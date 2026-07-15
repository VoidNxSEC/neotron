// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title SBOMRegistry
 * @notice Software Bill of Materials — on-chain attestation registry
 * @dev Stores SBOM hashes with CycloneDX/SPDX metadata, signed by build systems.
 *
 * What goes on-chain:
 *   - Package hash (Nix derivation hash)
 *   - SBOM format (CycloneDX 1.5 / SPDX 2.3)
 *   - SBOM content hash (sha256 of the SBOM document)
 *   - Builder identity (who generated this attestation)
 *   - Timestamp
 *
 * What stays off-chain (IPFS/Arweave):
 *   - Full SBOM document (JSON/XML)
 *   - Vulnerability scan results
 *   - License compliance report
 *
 * Integration:
 *   - SupplyChainGuardian calls this for every Nix build
 *   - BuildAttestation links to SBOM entries
 *   - LicenseRegistry verifies SPDX compliance
 */

contract SBOMRegistry {
    // ── Types ──────────────────────────────────────────────────────────────

    enum SBOMFormat {
        CycloneDX_1_5,
        SPDX_2_3,
        CycloneDX_1_4,
        SPDX_2_2
    }

    struct SBOMEntry {
        bytes32 packageHash; // Nix derivation hash
        bytes32 sbomContentHash; // sha256 of full SBOM document
        SBOMFormat format; // SBOM standard used
        address builder; // Who generated this attestation
        string ipfsCid; // IPFS CID of full SBOM document
        string arweaveTxId; // Arweave TX (permanent storage)
        uint256 timestamp; // Block timestamp
        bool revoked; // Allow revocation for security updates
    }

    struct VulnerabilityReport {
        bytes32 sbomId; // Links to SBOM entry
        string cveId; // CVE-2024-XXXX
        uint8 severity; // 0-10 (CVSS)
        string affectedPackage; // Package name
        string fixedVersion; // Version with fix
        uint256 reportedAt;
        bool resolved;
    }

    // ── Storage ────────────────────────────────────────────────────────────

    mapping(bytes32 => SBOMEntry) public sbomEntries; // sbomId → entry
    mapping(bytes32 => bytes32[]) public packageSBOMs; // packageHash → sbomIds
    mapping(address => bytes32[]) public builderSBOMs; // builder → sbomIds
    mapping(bytes32 => VulnerabilityReport[]) public vulnerabilities; // sbomId → vulns

    bytes32[] public allSBOMs;
    uint256 public totalSBOMs;

    // ── Events ─────────────────────────────────────────────────────────────

    event SBOMAttested(
        bytes32 indexed sbomId,
        bytes32 indexed packageHash,
        address indexed builder,
        SBOMFormat format,
        string ipfsCid,
        uint256 timestamp
    );

    event VulnerabilityReported(
        bytes32 indexed sbomId,
        string cveId,
        uint8 severity,
        string affectedPackage
    );

    event SBOMRevoked(bytes32 indexed sbomId, string reason);

    // ── Errors ─────────────────────────────────────────────────────────────

    error SBOMAlreadyExists(bytes32 sbomId);
    error SBOMNotFound(bytes32 sbomId);
    error AlreadyRevoked(bytes32 sbomId);

    // ── SBOM Attestation ───────────────────────────────────────────────────

    /**
     * @notice Attest a new SBOM for a Nix package
     * @param sbomId Unique ID (keccak256(packageHash + sbomContentHash))
     * @param packageHash Nix derivation hash
     * @param sbomContentHash sha256 of the full SBOM document
     * @param format SBOM standard format
     * @param ipfsCid IPFS CID of the full SBOM document
     * @param arweaveTxId Arweave TX ID (empty if not permanent)
     */
    function attestSBOM(
        bytes32 sbomId,
        bytes32 packageHash,
        bytes32 sbomContentHash,
        SBOMFormat format,
        string calldata ipfsCid,
        string calldata arweaveTxId
    ) external returns (bytes32) {
        if (sbomEntries[sbomId].timestamp != 0) {
            revert SBOMAlreadyExists(sbomId);
        }

        sbomEntries[sbomId] = SBOMEntry({
            packageHash: packageHash,
            sbomContentHash: sbomContentHash,
            format: format,
            builder: msg.sender,
            ipfsCid: ipfsCid,
            arweaveTxId: arweaveTxId,
            timestamp: block.timestamp,
            revoked: false
        });

        packageSBOMs[packageHash].push(sbomId);
        builderSBOMs[msg.sender].push(sbomId);
        allSBOMs.push(sbomId);
        totalSBOMs++;

        emit SBOMAttested(
            sbomId,
            packageHash,
            msg.sender,
            format,
            ipfsCid,
            block.timestamp
        );

        return sbomId;
    }

    /**
     * @notice Revoke an SBOM entry (e.g., security issue found)
     */
    function revokeSBOM(bytes32 sbomId, string calldata reason) external {
        SBOMEntry storage entry = sbomEntries[sbomId];
        if (entry.timestamp == 0) revert SBOMNotFound(sbomId);
        if (entry.revoked) revert AlreadyRevoked(sbomId);

        require(msg.sender == entry.builder, "Only builder can revoke");

        entry.revoked = true;
        emit SBOMRevoked(sbomId, reason);
    }

    // ── Vulnerabilities ────────────────────────────────────────────────────

    /**
     * @notice Report a vulnerability against an SBOM entry
     */
    function reportVulnerability(
        bytes32 sbomId,
        string calldata cveId,
        uint8 severity,
        string calldata affectedPackage,
        string calldata fixedVersion
    ) external {
        if (sbomEntries[sbomId].timestamp == 0) revert SBOMNotFound(sbomId);

        vulnerabilities[sbomId].push(
            VulnerabilityReport({
                sbomId: sbomId,
                cveId: cveId,
                severity: severity,
                affectedPackage: affectedPackage,
                fixedVersion: fixedVersion,
                reportedAt: block.timestamp,
                resolved: false
            })
        );

        emit VulnerabilityReported(sbomId, cveId, severity, affectedPackage);
    }

    // ── Queries ────────────────────────────────────────────────────────────

    function getSBOM(bytes32 sbomId) external view returns (SBOMEntry memory) {
        if (sbomEntries[sbomId].timestamp == 0) revert SBOMNotFound(sbomId);
        return sbomEntries[sbomId];
    }

    function getPackageSBOMs(
        bytes32 packageHash
    ) external view returns (bytes32[] memory) {
        return packageSBOMs[packageHash];
    }

    function getBuilderSBOMs(
        address builder
    ) external view returns (bytes32[] memory) {
        return builderSBOMs[builder];
    }

    function getVulnerabilities(
        bytes32 sbomId
    ) external view returns (VulnerabilityReport[] memory) {
        return vulnerabilities[sbomId];
    }

    function getTotalSBOMs() external view returns (uint256) {
        return totalSBOMs;
    }
}
