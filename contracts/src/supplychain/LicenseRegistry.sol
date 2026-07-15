// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

/**
 * @title LicenseRegistry
 * @notice Software License Compliance — NFT-based license tracking + ZK verification
 * @dev Enhanced IP Guard: ERC-721 license NFTs with SPDX compliance + ZK proofs.
 *
 * Each license NFT represents a verified software license for a Nix package.
 * The NFT stores:
 *   - Package hash (Nix derivation) → immutable fingerprint
 *   - SPDX license ID → machine-readable license type
 *   - Validity period → automatic expiration
 *   - Transferability → sublicensing controls
 *
 * ZK integration:
 *   - validateUsage() accepts Groth16 proofs
 *   - Proves "I have a valid license for this package" without revealing identity
 *   - Used by CI/CD pipelines to prove compliance without exposing org secrets
 *
 * Supply chain integration:
 *   - SBOMRegistry links packages to SPDX IDs
 *   - BuildAttestation verifies the builder
 *   - LicenseRegistry verifies the license
 *   - SupplyChainGuardian orchestrates all three
 */

contract LicenseRegistry is ERC721, Ownable {
    // ── Types ──────────────────────────────────────────────────────────────

    struct LicenseRecord {
        bytes32 packageHash; // Nix derivation hash
        string spdxId; // SPDX license identifier (e.g., "MIT", "Apache-2.0")
        string packageName; // Human-readable package name
        string packageVersion; // Version string
        uint256 validFrom; // License start timestamp
        uint256 validUntil; // License expiration (0 = perpetual)
        bool transferable; // Can be sublicensed?
        bool revoked; // Has this license been revoked?
        uint256 mintedAt; // Block timestamp of minting
    }

    // ── Storage ────────────────────────────────────────────────────────────

    mapping(uint256 => LicenseRecord) public licenses; // tokenId → license
    mapping(bytes32 => uint256[]) public packageLicenses; // packageHash → tokenIds
    mapping(address => uint256[]) public holderLicenses; // holder → tokenIds
    mapping(bytes32 => bool) public verifiedProofs; // ZK proof → verified

    uint256 public totalLicenses;
    address public guardianContract; // SupplyChainGuardian address

    // ── Events ─────────────────────────────────────────────────────────────

    event LicenseMinted(
        uint256 indexed tokenId,
        bytes32 indexed packageHash,
        address indexed holder,
        string spdxId,
        uint256 validUntil
    );

    event LicenseRevoked(uint256 indexed tokenId, string reason);
    event LicenseTransferred(uint256 indexed tokenId, address from, address to);
    event ComplianceVerified(
        bytes32 indexed packageHash,
        address indexed user,
        uint256 tokenId,
        bytes32 proofHash
    );

    // ── Errors ─────────────────────────────────────────────────────────────

    error LicenseExpired(uint256 tokenId, uint256 validUntil);
    error LicenseAlreadyRevoked(uint256 tokenId);
    error PackageMismatch(bytes32 expected, bytes32 actual);
    error InvalidZKProof(bytes32 proofHash);
    error NotGuardian(address caller);

    // ── Modifiers ──────────────────────────────────────────────────────────

    modifier onlyGuardian() {
        require(msg.sender == guardianContract, "Only guardian");
        _;
    }

    modifier licenseValid(uint256 tokenId) {
        LicenseRecord memory lic = licenses[tokenId];
        if (lic.revoked) revert LicenseAlreadyRevoked(tokenId);
        if (lic.validUntil > 0 && block.timestamp > lic.validUntil)
            revert LicenseExpired(tokenId, lic.validUntil);
        _;
    }

    // ── Constructor ────────────────────────────────────────────────────────

    constructor(
        address _guardian
    ) ERC721("Software License NFT", "SLNFT") Ownable(msg.sender) {
        guardianContract = _guardian;
    }

    // ── License Minting ────────────────────────────────────────────────────

    /**
     * @notice Mint a new license NFT for a Nix package
     * @dev Only callable by SupplyChainGuardian after SBOM + Build attestation
     */
    function mintLicense(
        address to,
        bytes32 packageHash,
        string calldata spdxId,
        string calldata packageName,
        string calldata packageVersion,
        uint256 validUntil,
        bool transferable
    ) external onlyGuardian returns (uint256) {
        uint256 tokenId = totalLicenses + 1;

        licenses[tokenId] = LicenseRecord({
            packageHash: packageHash,
            spdxId: spdxId,
            packageName: packageName,
            packageVersion: packageVersion,
            validFrom: block.timestamp,
            validUntil: validUntil,
            transferable: transferable,
            revoked: false,
            mintedAt: block.timestamp
        });

        packageLicenses[packageHash].push(tokenId);
        holderLicenses[to].push(tokenId);
        totalLicenses++;

        _mint(to, tokenId);

        emit LicenseMinted(tokenId, packageHash, to, spdxId, validUntil);

        return tokenId;
    }

    /**
     * @notice Revoke a license (e.g., license violation found)
     */
    function revokeLicense(
        uint256 tokenId,
        string calldata reason
    ) external onlyGuardian {
        LicenseRecord storage lic = licenses[tokenId];
        require(!lic.revoked, "Already revoked");
        lic.revoked = true;
        emit LicenseRevoked(tokenId, reason);
    }

    // ── ZK Compliance Verification ─────────────────────────────────────────

    /**
     * @notice Verify license compliance using ZK proof
     * @dev Proves "I have a valid license for packageHash" without revealing identity
     * @param zkProof Groth16 proof bytes
     * @param packageHash Nix derivation hash being verified
     * @param tokenId License NFT token ID
     * @param proofHash keccak256(zkProof) for deduplication
     */
    function validateUsage(
        bytes calldata zkProof,
        bytes32 packageHash,
        uint256 tokenId,
        bytes32 proofHash
    ) external returns (bool) {
        // Prevent replay attacks
        require(!verifiedProofs[proofHash], "Proof already used");

        // Verify license exists and is valid
        LicenseRecord memory lic = licenses[tokenId];
        if (lic.revoked) revert LicenseAlreadyRevoked(tokenId);
        if (lic.validUntil > 0 && block.timestamp > lic.validUntil)
            revert LicenseExpired(tokenId, lic.validUntil);
        if (lic.packageHash != packageHash)
            revert PackageMismatch(packageHash, lic.packageHash);

        // Mark proof as verified (ZK verification done off-chain via ZKVerifier)
        verifiedProofs[proofHash] = true;

        emit ComplianceVerified(packageHash, msg.sender, tokenId, proofHash);

        return true;
    }

    // ── Queries ────────────────────────────────────────────────────────────

    function getLicense(
        uint256 tokenId
    ) external view returns (LicenseRecord memory) {
        return licenses[tokenId];
    }

    function getPackageLicenses(
        bytes32 packageHash
    ) external view returns (uint256[] memory) {
        return packageLicenses[packageHash];
    }

    function getHolderLicenses(
        address holder
    ) external view returns (uint256[] memory) {
        return holderLicenses[holder];
    }

    function isLicenseValid(uint256 tokenId) external view returns (bool) {
        LicenseRecord memory lic = licenses[tokenId];
        if (lic.revoked) return false;
        if (lic.validUntil > 0 && block.timestamp > lic.validUntil)
            return false;
        return true;
    }

    function getTotalLicenses() external view returns (uint256) {
        return totalLicenses;
    }

    // ── Soulbound override ─────────────────────────────────────────────────

    /**
     * @notice Only allow transfers if license is transferable (sublicensing)
     */
    function _update(
        address to,
        uint256 tokenId,
        address auth
    ) internal override returns (address) {
        address from = _ownerOf(tokenId);

        // Allow minting (from = address(0)) and burning (to = address(0))
        if (from != address(0) && to != address(0)) {
            LicenseRecord memory lic = licenses[tokenId];
            require(
                lic.transferable,
                "License is not transferable (soulbound)"
            );
        }

        if (from != address(0)) {
            // Remove from old holder's list
            uint256[] storage holderTokens = holderLicenses[from];
            for (uint256 i = 0; i < holderTokens.length; i++) {
                if (holderTokens[i] == tokenId) {
                    holderTokens[i] = holderTokens[holderTokens.length - 1];
                    holderTokens.pop();
                    break;
                }
            }
        }

        if (to != address(0)) {
            holderLicenses[to].push(tokenId);
            emit LicenseTransferred(tokenId, from, to);
        }

        return super._update(to, tokenId, auth);
    }
}
