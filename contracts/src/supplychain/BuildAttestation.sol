// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title BuildAttestation
 * @notice SLSA Build Provenance — on-chain attestation of build integrity
 * @dev Implements SLSA v1.0 provenance model for Nix-based builds.
 *
 * SLSA Levels tracked:
 *   Level 0: No attestation
 *   Level 1: Build is scripted (provenance exists)
 *   Level 2: Build service generates provenance (parameterized, no user access)
 *   Level 3: Build is hermetic + isolated (Nix provides this natively)
 *
 * Nix provides SLSA Level 3 by default:
 *   - Hermetic: fixed-input derivations
 *   - Isolated: sandbox builds
 *   - Reproducible: bit-for-bit identical outputs
 *
 * Attestation payload (off-chain, IPFS):
 *   - Builder ID (Nix daemon / GitHub Actions runner)
 *   - Build invocation (command line, parameters)
 *   - Source provenance (git commit, repo URL)
 *   - Build dependencies (Nix flake inputs, pinned hashes)
 *   - Output artifacts (derivation paths, hashes)
 */

contract BuildAttestation {
    // ── Types ──────────────────────────────────────────────────────────────

    enum SLSALevel {
        Level0,
        Level1,
        Level2,
        Level3
    }

    struct BuildProvenance {
        bytes32 buildId;            // keccak256(builder + packageHash + timestamp)
        bytes32 packageHash;        // Nix derivation hash
        address builder;            // Builder identity (Nix daemon key / CI runner)
        SLSALevel slsaLevel;        // SLSA provenance level
        bytes32 sourceCommit;       // Git commit hash
        string sourceRepo;          // Git repository URL
        bytes32 flakeInputHash;     // Hash of flake.lock (all inputs pinned)
        string ipfsCid;             // IPFS CID of full attestation document
        uint256 timestamp;
        bool verified;              // Has this attestation been verified?
    }

    struct Builder {
        address builderAddress;
        string name;                // e.g., "GitHub Actions", "Nix daemon"
        string publicKey;           // Ed25519 public key (hex)
        uint256 totalBuilds;        // Total builds attested
        bool active;
    }

    // ── Storage ────────────────────────────────────────────────────────────

    mapping(bytes32 => BuildProvenance) public provenances;
    mapping(bytes32 => bytes32[]) public packageBuilds;     // packageHash → buildIds
    mapping(address => Builder) public builders;            // builder address → metadata
    mapping(address => bytes32[]) public builderBuilds;     // builder → buildIds

    bytes32[] public allBuilds;
    uint256 public totalBuilds;

    // ── Events ─────────────────────────────────────────────────────────────

    event BuildAttested(
        bytes32 indexed buildId,
        bytes32 indexed packageHash,
        address indexed builder,
        SLSALevel slsaLevel,
        bytes32 sourceCommit,
        string ipfsCid
    );

    event BuilderRegistered(address indexed builder, string name, string publicKey);
    event BuildVerified(bytes32 indexed buildId, address indexed verifier);

    // ── Errors ─────────────────────────────────────────────────────────────

    error BuildAlreadyExists(bytes32 buildId);
    error BuildNotFound(bytes32 buildId);
    error BuilderNotRegistered(address builder);
    error BuilderAlreadyRegistered(address builder);

    // ── Builder Registration ───────────────────────────────────────────────

    /**
     * @notice Register a builder identity (Nix daemon, CI runner, etc.)
     */
    function registerBuilder(
        string calldata name,
        string calldata publicKey
    ) external {
        if (builders[msg.sender].active) revert BuilderAlreadyRegistered(msg.sender);

        builders[msg.sender] = Builder({
            builderAddress: msg.sender,
            name: name,
            publicKey: publicKey,
            totalBuilds: 0,
            active: true
        });

        emit BuilderRegistered(msg.sender, name, publicKey);
    }

    // ── Build Attestation ──────────────────────────────────────────────────

    /**
     * @notice Attest a build with SLSA provenance
     * @param buildId keccak256(msg.sender + packageHash + block.timestamp)
     * @param packageHash Nix derivation hash
     * @param slsaLevel SLSA level (0-3)
     * @param sourceCommit Git commit hash
     * @param sourceRepo Git repository URL
     * @param flakeInputHash Hash of flake.lock
     * @param ipfsCid IPFS CID of full attestation
     */
    function attestBuild(
        bytes32 buildId,
        bytes32 packageHash,
        SLSALevel slsaLevel,
        bytes32 sourceCommit,
        string calldata sourceRepo,
        bytes32 flakeInputHash,
        string calldata ipfsCid
    ) external returns (bytes32) {
        if (!builders[msg.sender].active) revert BuilderNotRegistered(msg.sender);
        if (provenances[buildId].timestamp != 0) revert BuildAlreadyExists(buildId);

        provenances[buildId] = BuildProvenance({
            buildId: buildId,
            packageHash: packageHash,
            builder: msg.sender,
            slsaLevel: slsaLevel,
            sourceCommit: sourceCommit,
            sourceRepo: sourceRepo,
            flakeInputHash: flakeInputHash,
            ipfsCid: ipfsCid,
            timestamp: block.timestamp,
            verified: false
        });

        packageBuilds[packageHash].push(buildId);
        builderBuilds[msg.sender].push(buildId);
        builders[msg.sender].totalBuilds++;
        allBuilds.push(buildId);
        totalBuilds++;

        emit BuildAttested(buildId, packageHash, msg.sender, slsaLevel, sourceCommit, ipfsCid);

        return buildId;
    }

    /**
     * @notice Verify a build attestation (called by SupplyChainGuardian)
     */
    function verifyBuild(bytes32 buildId) external returns (bool) {
        BuildProvenance storage p = provenances[buildId];
        if (p.timestamp == 0) revert BuildNotFound(buildId);

        p.verified = true;
        emit BuildVerified(buildId, msg.sender);
        return true;
    }

    // ── Queries ────────────────────────────────────────────────────────────

    function getBuild(bytes32 buildId) external view returns (BuildProvenance memory) {
        if (provenances[buildId].timestamp == 0) revert BuildNotFound(buildId);
        return provenances[buildId];
    }

    function getPackageBuilds(bytes32 packageHash) external view returns (bytes32[] memory) {
        return packageBuilds[packageHash];
    }

    function getBuilderBuilds(address builder) external view returns (bytes32[] memory) {
        return builderBuilds[builder];
    }

    function getBuilder(address builder) external view returns (Builder memory) {
        if (!builders[builder].active) revert BuilderNotRegistered(builder);
        return builders[builder];
    }

    function getTotalBuilds() external view returns (uint256) {
        return totalBuilds;
    }
}
