// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {ComplianceGuardrail} from "./ComplianceGuardrail.sol";

/**
 * @title AuditLogger
 * @author NEXUS Platform
 * @notice On-chain audit logging with off-chain storage references (IPFS/Arweave)
 * @dev Stores compliance events on-chain with pointers to full logs on decentralized storage
 *
 * Design Philosophy:
 * - On-chain: Event emission + storage references (gas-efficient)
 * - Off-chain: Full audit logs on IPFS (mutable) or Arweave (permanent)
 * - Hybrid approach: Best of both worlds (immutability + cost efficiency)
 *
 * Storage Costs:
 * - On-chain only: ~640 gas per byte (~$10+ for 1KB at 50 gwei)
 * - IPFS: ~$5/month per 100GB (mutable, requires pinning)
 * - Arweave: ~$0.005/MB one-time (permanent, 200+ years)
 *
 * Integration with BASTION-SC:
 * This contract works alongside ComplianceGuardrail to provide
 * comprehensive audit trails for all compliance checks.
 */
contract AuditLogger is ComplianceGuardrail {
    // ============ Structs ============

    /**
     * @notice Audit log reference stored on-chain
     * @param logId Unique identifier for the log
     * @param ipfsCID Content identifier on IPFS
     * @param arweaveTxId Transaction ID on Arweave (empty if not permanent)
     * @param regulation Regulation being audited (LGPD, GDPR, AI_ACT)
     * @param article Article number
     * @param passed Whether compliance check passed
     * @param timestamp Block timestamp
     * @param permanent Whether stored permanently on Arweave
     */
    struct AuditLog {
        bytes32 logId;
        string ipfsCID;
        string arweaveTxId;
        string regulation;
        uint8 article;
        bool passed;
        uint256 timestamp;
        bool permanent;
    }

    // ============ Storage ============

    /// @notice Mapping: logId => AuditLog
    mapping(bytes32 => AuditLog) public auditLogs;

    /// @notice Mapping: user => logId[] (user's audit history)
    mapping(address => bytes32[]) public userAuditHistory;

    /// @notice Mapping: regulation => logId[] (logs per regulation)
    mapping(string => bytes32[]) public regulationLogs;

    /// @notice Total number of audit logs
    uint256 public totalLogs;

    /// @notice Total number of compliance violations
    uint256 public totalViolations;

    // ============ Events ============

    event AuditLogCreated(
        bytes32 indexed logId,
        address indexed user,
        string regulation,
        uint8 article,
        bool passed,
        string ipfsCID,
        string arweaveTxId,
        bool permanent,
        uint256 timestamp
    );

    event AuditLogUpdated(
        bytes32 indexed logId,
        string newIpfsCID,
        string newArweaveTxId,
        uint256 timestamp
    );

    // ============ Errors ============

    error LogAlreadyExists(bytes32 logId);
    error LogNotFound(bytes32 logId);
    error CannotUpdatePermanentLog(bytes32 logId);

    // ============ Functions ============

    /**
     * @notice Log compliance check on-chain with off-chain storage reference
     * @param logId Unique identifier for the log
     * @param user Address of the user
     * @param regulation Regulation being checked
     * @param article Article number
     * @param passed Whether check passed
     * @param ipfsCID Content identifier on IPFS
     * @param arweaveTxId Transaction ID on Arweave (empty if not permanent)
     * @param permanent Whether stored permanently
     */
    function logCompliance(
        bytes32 logId,
        address user,
        string calldata regulation,
        uint8 article,
        bool passed,
        string calldata ipfsCID,
        string calldata arweaveTxId,
        bool permanent
    ) external {
        // Check if log already exists
        if (auditLogs[logId].timestamp != 0) {
            revert LogAlreadyExists(logId);
        }

        // Create audit log
        AuditLog memory log = AuditLog({
            logId: logId,
            ipfsCID: ipfsCID,
            arweaveTxId: arweaveTxId,
            regulation: regulation,
            article: article,
            passed: passed,
            timestamp: block.timestamp,
            permanent: permanent
        });

        // Store on-chain
        auditLogs[logId] = log;
        userAuditHistory[user].push(logId);
        regulationLogs[regulation].push(logId);

        // Update counters
        totalLogs++;
        if (!passed) {
            totalViolations++;
        }

        // Emit event
        emit AuditLogCreated(
            logId,
            user,
            regulation,
            article,
            passed,
            ipfsCID,
            arweaveTxId,
            permanent,
            block.timestamp
        );

        // Also emit base compliance event
        if (passed) {
            emit CompliancePass(user, regulation, article, block.timestamp);
        } else {
            emit ComplianceViolation(
                user,
                regulation,
                article,
                "See off-chain log for details",
                block.timestamp
            );
        }
    }

    /**
     * @notice Update IPFS/Arweave references for an audit log
     * @dev Can only update non-permanent logs (IPFS can be updated, Arweave cannot)
     * @param logId ID of the log to update
     * @param newIpfsCID New IPFS CID
     * @param newArweaveTxId New Arweave TX ID (if upgrading to permanent)
     */
    function updateLogReferences(
        bytes32 logId,
        string calldata newIpfsCID,
        string calldata newArweaveTxId
    ) external {
        AuditLog storage log = auditLogs[logId];

        if (log.timestamp == 0) {
            revert LogNotFound(logId);
        }

        // Cannot update if already permanent on Arweave
        if (log.permanent && bytes(log.arweaveTxId).length > 0) {
            revert CannotUpdatePermanentLog(logId);
        }

        // Update references
        log.ipfsCID = newIpfsCID;

        // If adding Arweave reference, mark as permanent
        if (bytes(newArweaveTxId).length > 0) {
            log.arweaveTxId = newArweaveTxId;
            log.permanent = true;
        }

        emit AuditLogUpdated(logId, newIpfsCID, newArweaveTxId, block.timestamp);
    }

    /**
     * @notice Get audit log by ID
     * @param logId ID of the log
     * @return AuditLog struct
     */
    function getAuditLog(bytes32 logId) external view returns (AuditLog memory) {
        if (auditLogs[logId].timestamp == 0) {
            revert LogNotFound(logId);
        }
        return auditLogs[logId];
    }

    /**
     * @notice Get user's audit history
     * @param user Address of the user
     * @return Array of log IDs
     */
    function getUserAuditHistory(address user) external view returns (bytes32[] memory) {
        return userAuditHistory[user];
    }

    /**
     * @notice Get logs for a specific regulation
     * @param regulation Regulation name (LGPD, GDPR, AI_ACT)
     * @return Array of log IDs
     */
    function getRegulationLogs(string calldata regulation) external view returns (bytes32[] memory) {
        return regulationLogs[regulation];
    }

    /**
     * @notice Get compliance statistics
     * @return totalLogs Total number of logs
     * @return totalViolations Total number of violations
     * @return complianceRate Compliance rate (passed / total) in basis points
     */
    function getComplianceStats() external view returns (
        uint256,
        uint256,
        uint256
    ) {
        uint256 complianceRate = totalLogs > 0
            ? ((totalLogs - totalViolations) * 10000) / totalLogs
            : 10000;

        return (totalLogs, totalViolations, complianceRate);
    }

    // ============ Placeholder Implementations ============

    /// @notice Not implemented (use LGPDConsent contract)
    function hasConsent(address) internal pure override returns (bool) {
        return true;
    }

    /// @notice Not implemented (use LGPDConsent contract)
    function hasDataAccess(address, address) internal pure override returns (bool) {
        return true;
    }

    /// @notice Not implemented (use LGPDConsent contract)
    function withinRetentionPeriod(address) internal pure override returns (bool) {
        return true;
    }

    /// @notice Not implemented (use GDPR contract)
    function hasHumanReview(bytes32) internal pure override returns (bool) {
        return true;
    }

    /// @notice Not implemented (use AI Act contract)
    function hasTransparencyInfo(bytes32) internal pure override returns (bool) {
        return true;
    }

    /// @notice Not implemented (use AI Act contract)
    function hasHumanOversight(bytes32) internal pure override returns (bool) {
        return true;
    }
}
