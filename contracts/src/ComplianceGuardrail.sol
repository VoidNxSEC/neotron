// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title ComplianceGuardrail
 * @author NEXUS Platform
 * @notice Base contract for BASTION-SC compliance enforcement
 * @dev Abstract contract providing compliance modifiers and event logging
 *
 * BASTION-SC Philosophy:
 * Just as BASTION makes compliance violations impossible at the Linux kernel level (syscalls),
 * BASTION-SC makes them impossible at the smart contract level (function execution).
 *
 * Defense-in-Depth Compliance:
 * - Layer 1: SENTINEL (Application - Python validation)
 * - Layer 2: BASTION (Kernel - seccomp-BPF syscall filtering)
 * - Layer 3: BASTION-SC (Smart Contract - on-chain enforcement) ← This layer
 * - Layer 4: Audit Trail (PostgreSQL + IPFS/Arweave)
 */
abstract contract ComplianceGuardrail {
    // ============ Events ============

    /**
     * @notice Emitted when a compliance check fails
     * @param user Address of the user who triggered the violation
     * @param regulation The regulation that was violated (e.g., "LGPD", "GDPR")
     * @param article The specific article violated (e.g., 7, 15, 22)
     * @param violation Description of the violation
     * @param timestamp Block timestamp of the violation
     */
    event ComplianceViolation(
        address indexed user,
        string regulation,
        uint8 article,
        string violation,
        uint256 timestamp
    );

    /**
     * @notice Emitted when a compliance check passes
     * @param user Address of the user who passed the check
     * @param regulation The regulation that was checked
     * @param article The specific article checked
     * @param timestamp Block timestamp of the check
     */
    event CompliancePass(
        address indexed user,
        string regulation,
        uint8 article,
        uint256 timestamp
    );

    /**
     * @notice Emitted when an audit log is stored off-chain
     * @param logId Unique identifier for the audit log
     * @param ipfsCID Content identifier on IPFS
     * @param arweaveTxId Transaction ID on Arweave (if permanent storage)
     * @param regulation The regulation being audited
     * @param timestamp Block timestamp
     */
    event AuditLogStored(
        bytes32 indexed logId,
        string ipfsCID,
        string arweaveTxId,
        string regulation,
        uint256 timestamp
    );

    // ============ Errors ============

    /// @notice Thrown when LGPD Article 7 is violated (no consent)
    error LGPD_Article7_ConsentRequired(address dataSubject);

    /// @notice Thrown when LGPD Article 16 is violated (unauthorized data access)
    error LGPD_Article16_UnauthorizedAccess(address dataSubject);

    /// @notice Thrown when LGPD Article 46 is violated (retention policy)
    error LGPD_Article46_RetentionViolation(address dataSubject);

    /// @notice Thrown when GDPR Article 15 is violated (right to access)
    error GDPR_Article15_AccessDenied(address dataSubject);

    /// @notice Thrown when GDPR Article 17 is violated (right to erasure)
    error GDPR_Article17_ErasureRequired(address dataSubject);

    /// @notice Thrown when GDPR Article 22 is violated (automated decision-making)
    error GDPR_Article22_HumanOversightRequired(bytes32 decisionId);

    /// @notice Thrown when AI Act Article 5 is violated (prohibited practices)
    error AIAct_Article5_ProhibitedPractice(string practice);

    /// @notice Thrown when AI Act Article 13 is violated (transparency)
    error AIAct_Article13_TransparencyRequired(bytes32 outputId);

    /// @notice Thrown when AI Act Article 14 is violated (human oversight)
    error AIAct_Article14_OversightRequired(bytes32 decisionId);

    // ============ Modifiers ============

    /**
     * @notice LGPD Article 7 - Consent requirement for data processing
     * @dev Reverts if the data subject has not granted consent
     * @param dataSubject Address of the person whose data is being processed
     */
    modifier lgpdArticle7Consent(address dataSubject) {
        if (!hasConsent(dataSubject)) {
            emit ComplianceViolation(
                dataSubject,
                "LGPD",
                7,
                "Consent required for data processing",
                block.timestamp
            );
            revert LGPD_Article7_ConsentRequired(dataSubject);
        }

        emit CompliancePass(dataSubject, "LGPD", 7, block.timestamp);
        _;
    }

    /**
     * @notice LGPD Article 16 - Right to data portability and access
     * @dev Reverts if the requester is not authorized to access data
     * @param dataSubject Address of the person whose data is being accessed
     */
    modifier lgpdArticle16Access(address dataSubject) {
        if (!hasDataAccess(dataSubject, msg.sender)) {
            emit ComplianceViolation(
                dataSubject,
                "LGPD",
                16,
                "Unauthorized data access attempt",
                block.timestamp
            );
            revert LGPD_Article16_UnauthorizedAccess(dataSubject);
        }

        emit CompliancePass(msg.sender, "LGPD", 16, block.timestamp);
        _;
    }

    /**
     * @notice LGPD Article 46 - Data retention limits
     * @dev Reverts if data retention period has expired
     * @param dataSubject Address of the person whose data is subject to retention
     */
    modifier lgpdArticle46Retention(address dataSubject) {
        if (!withinRetentionPeriod(dataSubject)) {
            emit ComplianceViolation(
                dataSubject,
                "LGPD",
                46,
                "Data retention period expired - deletion required",
                block.timestamp
            );
            revert LGPD_Article46_RetentionViolation(dataSubject);
        }

        emit CompliancePass(dataSubject, "LGPD", 46, block.timestamp);
        _;
    }

    /**
     * @notice GDPR Article 22 - Automated decision-making with human oversight
     * @dev Reverts if human review is not present for automated decisions
     * @param decisionId Unique identifier for the decision being made
     */
    modifier gdprArticle22HumanOversight(bytes32 decisionId) {
        if (!hasHumanReview(decisionId)) {
            emit ComplianceViolation(
                msg.sender,
                "GDPR",
                22,
                "Human oversight required for automated decisions",
                block.timestamp
            );
            revert GDPR_Article22_HumanOversightRequired(decisionId);
        }

        emit CompliancePass(msg.sender, "GDPR", 22, block.timestamp);
        _;
    }

    /**
     * @notice AI Act Article 13 - Transparency requirements
     * @dev Reverts if AI output lacks required transparency information
     * @param outputId Unique identifier for the AI output
     */
    modifier aiActArticle13Transparency(bytes32 outputId) {
        if (!hasTransparencyInfo(outputId)) {
            emit ComplianceViolation(
                msg.sender,
                "AI_ACT",
                13,
                "AI output must include transparency information",
                block.timestamp
            );
            revert AIAct_Article13_TransparencyRequired(outputId);
        }

        emit CompliancePass(msg.sender, "AI_ACT", 13, block.timestamp);
        _;
    }

    /**
     * @notice AI Act Article 14 - Human oversight for high-risk AI
     * @dev Reverts if high-risk AI decision lacks human oversight
     * @param decisionId Unique identifier for the AI decision
     */
    modifier aiActArticle14Oversight(bytes32 decisionId) {
        if (!hasHumanOversight(decisionId)) {
            emit ComplianceViolation(
                msg.sender,
                "AI_ACT",
                14,
                "Human oversight required for high-risk AI systems",
                block.timestamp
            );
            revert AIAct_Article14_OversightRequired(decisionId);
        }

        emit CompliancePass(msg.sender, "AI_ACT", 14, block.timestamp);
        _;
    }

    // ============ Virtual Functions (Must be implemented by derived contracts) ============

    /**
     * @notice Check if a data subject has granted consent for data processing
     * @param dataSubject Address of the data subject
     * @return bool True if consent is granted and valid
     */
    function hasConsent(address dataSubject) internal view virtual returns (bool);

    /**
     * @notice Check if an address is authorized to access another's data
     * @param dataSubject Address of the data subject
     * @param accessor Address requesting access
     * @return bool True if access is authorized
     */
    function hasDataAccess(
        address dataSubject,
        address accessor
    ) internal view virtual returns (bool);

    /**
     * @notice Check if data is within its retention period
     * @param dataSubject Address of the data subject
     * @return bool True if within retention period
     */
    function withinRetentionPeriod(address dataSubject) internal view virtual returns (bool);

    /**
     * @notice Check if a decision has undergone human review
     * @param decisionId Unique identifier for the decision
     * @return bool True if human review is present
     */
    function hasHumanReview(bytes32 decisionId) internal view virtual returns (bool);

    /**
     * @notice Check if AI output has transparency information
     * @param outputId Unique identifier for the AI output
     * @return bool True if transparency info is present
     */
    function hasTransparencyInfo(bytes32 outputId) internal view virtual returns (bool);

    /**
     * @notice Check if a decision has human oversight
     * @param decisionId Unique identifier for the decision
     * @return bool True if human oversight is present
     */
    function hasHumanOversight(bytes32 decisionId) internal view virtual returns (bool);

    // ============ Audit Logging ============

    /**
     * @notice Store audit log off-chain (IPFS/Arweave)
     * @param logId Unique identifier for the audit log
     * @param ipfsCID Content identifier on IPFS
     * @param arweaveTxId Transaction ID on Arweave (empty if not permanent)
     * @param regulation The regulation being audited
     */
    function storeAuditLog(
        bytes32 logId,
        string memory ipfsCID,
        string memory arweaveTxId,
        string memory regulation
    ) internal {
        emit AuditLogStored(logId, ipfsCID, arweaveTxId, regulation, block.timestamp);
    }
}
