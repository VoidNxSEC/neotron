// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {ComplianceGuardrail} from "./ComplianceGuardrail.sol";

/**
 * @title LGPDConsent
 * @author NEXUS Platform
 * @notice Implements LGPD consent management on-chain
 * @dev Handles consent granting, revocation, and verification for LGPD compliance
 *
 * LGPD Articles Implemented:
 * - Article 7: Consent required for data processing
 * - Article 16: Right to data portability and access control
 * - Article 46: Data retention limits
 *
 * Integration with BASTION Kernel Layer:
 * This smart contract provides on-chain consent management that mirrors
 * the kernel-level enforcement in neutron/compliance/auditors/lgpd_kernel.py
 */
contract LGPDConsent is ComplianceGuardrail {
    // ============ Structs ============

    /**
     * @notice Consent record structure
     * @param granted Whether consent has been granted
     * @param grantedAt Timestamp when consent was granted
     * @param expiresAt Timestamp when consent expires
     * @param purpose Description of data processing purpose
     * @param revoked Whether consent has been revoked
     * @param revokedAt Timestamp when consent was revoked
     */
    struct ConsentRecord {
        bool granted;
        uint256 grantedAt;
        uint256 expiresAt;
        string purpose;
        bool revoked;
        uint256 revokedAt;
    }

    /**
     * @notice Data access authorization record
     * @param authorized Whether access is authorized
     * @param grantedAt Timestamp when access was granted
     * @param expiresAt Timestamp when access expires
     * @param scope Description of access scope
     */
    struct AccessRecord {
        bool authorized;
        uint256 grantedAt;
        uint256 expiresAt;
        string scope;
    }

    /**
     * @notice Data retention policy
     * @param retentionPeriod Duration in seconds for data retention
     * @param dataCreatedAt Timestamp when data was created
     * @param purpose Purpose for data retention
     */
    struct RetentionPolicy {
        uint256 retentionPeriod;
        uint256 dataCreatedAt;
        string purpose;
    }

    // ============ Storage ============

    /// @notice Mapping: dataSubject => processor => ConsentRecord
    mapping(address => mapping(address => ConsentRecord)) public consents;

    /// @notice Mapping: dataSubject => accessor => AccessRecord
    mapping(address => mapping(address => AccessRecord)) public accessAuthorizations;

    /// @notice Mapping: dataSubject => RetentionPolicy
    mapping(address => RetentionPolicy) public retentionPolicies;

    /// @notice Default retention period (365 days)
    uint256 public constant DEFAULT_RETENTION_PERIOD = 365 days;

    /// @notice Maximum retention period (10 years)
    uint256 public constant MAX_RETENTION_PERIOD = 10 * 365 days;

    // ============ Events ============

    event ConsentGranted(
        address indexed dataSubject,
        address indexed processor,
        string purpose,
        uint256 expiresAt,
        uint256 timestamp
    );

    event ConsentRevoked(
        address indexed dataSubject,
        address indexed processor,
        uint256 timestamp
    );

    event ConsentExpired(
        address indexed dataSubject,
        address indexed processor,
        uint256 timestamp
    );

    event AccessGranted(
        address indexed dataSubject,
        address indexed accessor,
        string scope,
        uint256 expiresAt,
        uint256 timestamp
    );

    event AccessRevoked(
        address indexed dataSubject,
        address indexed accessor,
        uint256 timestamp
    );

    event RetentionPolicySet(
        address indexed dataSubject,
        uint256 retentionPeriod,
        string purpose,
        uint256 timestamp
    );

    // ============ Errors ============

    error ConsentAlreadyGranted(address dataSubject, address processor);
    error ConsentNotFound(address dataSubject, address processor);
    error ConsentAlreadyRevoked(address dataSubject, address processor);
    error InvalidDuration(uint256 duration);
    error InvalidRetentionPeriod(uint256 period);

    // ============ Consent Management Functions ============

    /**
     * @notice Grant consent for data processing
     * @param processor Address of the entity that will process data
     * @param duration Duration of consent in seconds
     * @param purpose Description of the processing purpose
     */
    function grantConsent(
        address processor,
        uint256 duration,
        string calldata purpose
    ) external {
        if (duration == 0 || duration > MAX_RETENTION_PERIOD) {
            revert InvalidDuration(duration);
        }

        ConsentRecord storage record = consents[msg.sender][processor];

        if (record.granted && !record.revoked && block.timestamp < record.expiresAt) {
            revert ConsentAlreadyGranted(msg.sender, processor);
        }

        uint256 expiresAt = block.timestamp + duration;

        record.granted = true;
        record.grantedAt = block.timestamp;
        record.expiresAt = expiresAt;
        record.purpose = purpose;
        record.revoked = false;
        record.revokedAt = 0;

        emit ConsentGranted(msg.sender, processor, purpose, expiresAt, block.timestamp);
    }

    /**
     * @notice Revoke consent for data processing
     * @param processor Address of the processor whose consent to revoke
     */
    function revokeConsent(address processor) external {
        ConsentRecord storage record = consents[msg.sender][processor];

        if (!record.granted) {
            revert ConsentNotFound(msg.sender, processor);
        }

        if (record.revoked) {
            revert ConsentAlreadyRevoked(msg.sender, processor);
        }

        record.revoked = true;
        record.revokedAt = block.timestamp;

        emit ConsentRevoked(msg.sender, processor, block.timestamp);
    }

    /**
     * @notice Check if valid consent exists
     * @param dataSubject Address of the data subject
     * @param processor Address of the processor
     * @return bool True if valid consent exists
     */
    function checkConsent(
        address dataSubject,
        address processor
    ) external view returns (bool) {
        return hasConsent(dataSubject, processor);
    }

    /**
     * @notice Internal function to check consent (used by modifiers)
     * @param dataSubject Address of the data subject
     * @return bool True if consent is valid
     */
    function hasConsent(address dataSubject) internal view override returns (bool) {
        return hasConsent(dataSubject, address(this));
    }

    /**
     * @notice Internal helper to check consent for a specific processor
     * @param dataSubject Address of the data subject
     * @param processor Address of the processor
     * @return bool True if consent is valid
     */
    function hasConsent(address dataSubject, address processor) internal view returns (bool) {
        ConsentRecord memory record = consents[dataSubject][processor];

        return record.granted && !record.revoked && block.timestamp < record.expiresAt;
    }

    // ============ Data Access Management (LGPD Article 16) ============

    /**
     * @notice Grant data access to another address
     * @param accessor Address to grant access to
     * @param duration Duration of access in seconds
     * @param scope Description of access scope
     */
    function grantDataAccess(
        address accessor,
        uint256 duration,
        string calldata scope
    ) external {
        if (duration == 0 || duration > MAX_RETENTION_PERIOD) {
            revert InvalidDuration(duration);
        }

        uint256 expiresAt = block.timestamp + duration;

        accessAuthorizations[msg.sender][accessor] = AccessRecord({
            authorized: true,
            grantedAt: block.timestamp,
            expiresAt: expiresAt,
            scope: scope
        });

        emit AccessGranted(msg.sender, accessor, scope, expiresAt, block.timestamp);
    }

    /**
     * @notice Revoke data access from an address
     * @param accessor Address to revoke access from
     */
    function revokeDataAccess(address accessor) external {
        delete accessAuthorizations[msg.sender][accessor];

        emit AccessRevoked(msg.sender, accessor, block.timestamp);
    }

    /**
     * @notice Check if data access is authorized
     * @param dataSubject Address of the data subject
     * @param accessor Address requesting access
     * @return bool True if access is authorized
     */
    function hasDataAccess(
        address dataSubject,
        address accessor
    ) internal view override returns (bool) {
        // Data subject always has access to their own data
        if (dataSubject == accessor) {
            return true;
        }

        AccessRecord memory record = accessAuthorizations[dataSubject][accessor];

        return record.authorized && block.timestamp < record.expiresAt;
    }

    // ============ Data Retention Management (LGPD Article 46) ============

    /**
     * @notice Set data retention policy for caller's data
     * @param retentionPeriod Duration in seconds to retain data
     * @param purpose Purpose for data retention
     */
    function setRetentionPolicy(uint256 retentionPeriod, string calldata purpose) external {
        if (retentionPeriod == 0 || retentionPeriod > MAX_RETENTION_PERIOD) {
            revert InvalidRetentionPeriod(retentionPeriod);
        }

        retentionPolicies[msg.sender] = RetentionPolicy({
            retentionPeriod: retentionPeriod,
            dataCreatedAt: block.timestamp,
            purpose: purpose
        });

        emit RetentionPolicySet(msg.sender, retentionPeriod, purpose, block.timestamp);
    }

    /**
     * @notice Check if data is within retention period
     * @param dataSubject Address of the data subject
     * @return bool True if within retention period
     */
    function withinRetentionPeriod(address dataSubject) internal view override returns (bool) {
        RetentionPolicy memory policy = retentionPolicies[dataSubject];

        // If no policy is set, use default retention period
        if (policy.dataCreatedAt == 0) {
            return true; // No data created yet, always valid
        }

        uint256 retentionPeriod =
            policy.retentionPeriod > 0 ? policy.retentionPeriod : DEFAULT_RETENTION_PERIOD;

        return block.timestamp < (policy.dataCreatedAt + retentionPeriod);
    }

    /**
     * @notice Check if retention period has expired for data subject
     * @param dataSubject Address of the data subject
     * @return bool True if retention period has expired
     */
    function isRetentionExpired(address dataSubject) external view returns (bool) {
        return !withinRetentionPeriod(dataSubject);
    }

    // ============ Placeholder Implementations (for other compliance checks) ============

    /// @notice Not implemented in this contract (for GDPR)
    function hasHumanReview(bytes32) internal pure override returns (bool) {
        return true; // Override in GDPR-specific contract
    }

    /// @notice Not implemented in this contract (for AI Act)
    function hasTransparencyInfo(bytes32) internal pure override returns (bool) {
        return true; // Override in AI Act-specific contract
    }

    /// @notice Not implemented in this contract (for AI Act)
    function hasHumanOversight(bytes32) internal pure override returns (bool) {
        return true; // Override in AI Act-specific contract
    }
}
