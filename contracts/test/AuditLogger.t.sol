// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {Test, console2} from "forge-std/Test.sol";
import {AuditLogger} from "../src/AuditLogger.sol";

/**
 * @title AuditLoggerTest
 * @notice Comprehensive test suite for on-chain audit logging with off-chain storage
 */
contract AuditLoggerTest is Test {
    AuditLogger public auditLogger;

    address public user1 = address(0x1);
    address public user2 = address(0x2);

    bytes32 public logId1 = keccak256("log_001");
    bytes32 public logId2 = keccak256("log_002");

    string public ipfsCID1 = "QmYwAPJzv5CZsnA625s3Xf2nemtYgPpHdWEz79ojWnPbdG";
    string public arweaveTxId1 = "8wgRDqvN3qP9nZQ7xKfP8YqN5xKfP8YqN5xKfP8YqN5";

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

    function setUp() public {
        auditLogger = new AuditLogger();
    }

    // ============ Audit Log Creation Tests ============

    function test_LogCompliance_LGPD_ConsentGranted() public {
        vm.expectEmit(true, true, false, true);
        emit AuditLogCreated(
            logId1,
            user1,
            "LGPD",
            7,
            true,
            ipfsCID1,
            "",
            false,
            block.timestamp
        );

        auditLogger.logCompliance(
            logId1,
            user1,
            "LGPD",
            7,
            true,
            ipfsCID1,
            "",
            false
        );

        AuditLogger.AuditLog memory log = auditLogger.getAuditLog(logId1);

        assertEq(log.logId, logId1);
        assertEq(log.regulation, "LGPD");
        assertEq(log.article, 7);
        assertTrue(log.passed);
        assertEq(log.ipfsCID, ipfsCID1);
        assertFalse(log.permanent);
    }

    function test_LogCompliance_WithArweave_Permanent() public {
        auditLogger.logCompliance(
            logId1,
            user1,
            "LGPD",
            7,
            true,
            ipfsCID1,
            arweaveTxId1,
            true
        );

        AuditLogger.AuditLog memory log = auditLogger.getAuditLog(logId1);

        assertEq(log.arweaveTxId, arweaveTxId1);
        assertTrue(log.permanent);
    }

    function test_LogCompliance_Violation() public {
        auditLogger.logCompliance(
            logId1,
            user1,
            "LGPD",
            7,
            false,  // Failed compliance check
            ipfsCID1,
            "",
            false
        );

        AuditLogger.AuditLog memory log = auditLogger.getAuditLog(logId1);

        assertFalse(log.passed);

        // Check violation counter
        (, uint256 violations,) = auditLogger.getComplianceStats();
        assertEq(violations, 1);
    }

    function test_CannotLogSameIdTwice() public {
        // Log once
        auditLogger.logCompliance(
            logId1,
            user1,
            "LGPD",
            7,
            true,
            ipfsCID1,
            "",
            false
        );

        // Try to log again with same ID
        vm.expectRevert(
            abi.encodeWithSelector(AuditLogger.LogAlreadyExists.selector, logId1)
        );

        auditLogger.logCompliance(
            logId1,
            user1,
            "LGPD",
            7,
            true,
            "different_cid",
            "",
            false
        );
    }

    function test_LogMultipleUsers() public {
        // User 1 logs
        auditLogger.logCompliance(
            logId1,
            user1,
            "LGPD",
            7,
            true,
            ipfsCID1,
            "",
            false
        );

        // User 2 logs
        auditLogger.logCompliance(
            logId2,
            user2,
            "GDPR",
            22,
            true,
            "another_cid",
            "",
            false
        );

        // Check both logs exist
        assertEq(auditLogger.getAuditLog(logId1).regulation, "LGPD");
        assertEq(auditLogger.getAuditLog(logId2).regulation, "GDPR");

        // Check total logs
        (uint256 total,,) = auditLogger.getComplianceStats();
        assertEq(total, 2);
    }

    // ============ Audit Log Update Tests ============

    function test_UpdateLogReferences_IPFS() public {
        // Create log
        auditLogger.logCompliance(
            logId1,
            user1,
            "LGPD",
            7,
            true,
            ipfsCID1,
            "",
            false
        );

        // Update IPFS CID
        string memory newCID = "QmNewCIDExample123456789";

        vm.expectEmit(true, false, false, true);
        emit AuditLogUpdated(logId1, newCID, "", block.timestamp);

        auditLogger.updateLogReferences(logId1, newCID, "");

        AuditLogger.AuditLog memory log = auditLogger.getAuditLog(logId1);
        assertEq(log.ipfsCID, newCID);
    }

    function test_UpdateLogReferences_AddArweave() public {
        // Create log without Arweave
        auditLogger.logCompliance(
            logId1,
            user1,
            "LGPD",
            7,
            true,
            ipfsCID1,
            "",
            false
        );

        // Add Arweave reference (upgrade to permanent)
        auditLogger.updateLogReferences(logId1, ipfsCID1, arweaveTxId1);

        AuditLogger.AuditLog memory log = auditLogger.getAuditLog(logId1);

        assertEq(log.arweaveTxId, arweaveTxId1);
        assertTrue(log.permanent);
    }

    function test_CannotUpdatePermanentLog() public {
        // Create permanent log
        auditLogger.logCompliance(
            logId1,
            user1,
            "LGPD",
            7,
            true,
            ipfsCID1,
            arweaveTxId1,
            true
        );

        // Try to update
        vm.expectRevert(
            abi.encodeWithSelector(AuditLogger.CannotUpdatePermanentLog.selector, logId1)
        );

        auditLogger.updateLogReferences(logId1, "new_cid", "");
    }

    function test_CannotUpdateNonexistentLog() public {
        bytes32 fakeLogId = keccak256("nonexistent");

        vm.expectRevert(
            abi.encodeWithSelector(AuditLogger.LogNotFound.selector, fakeLogId)
        );

        auditLogger.updateLogReferences(fakeLogId, "some_cid", "");
    }

    // ============ User History Tests ============

    function test_GetUserAuditHistory_SingleLog() public {
        auditLogger.logCompliance(
            logId1,
            user1,
            "LGPD",
            7,
            true,
            ipfsCID1,
            "",
            false
        );

        bytes32[] memory history = auditLogger.getUserAuditHistory(user1);

        assertEq(history.length, 1);
        assertEq(history[0], logId1);
    }

    function test_GetUserAuditHistory_MultipleLogs() public {
        // User 1 creates 3 logs
        for (uint i = 0; i < 3; i++) {
            bytes32 logId = keccak256(abi.encodePacked("log_", i));
            auditLogger.logCompliance(
                logId,
                user1,
                "LGPD",
                7,
                true,
                ipfsCID1,
                "",
                false
            );
        }

        bytes32[] memory history = auditLogger.getUserAuditHistory(user1);

        assertEq(history.length, 3);
    }

    function test_GetUserAuditHistory_EmptyForNewUser() public {
        bytes32[] memory history = auditLogger.getUserAuditHistory(user2);

        assertEq(history.length, 0);
    }

    // ============ Regulation Logs Tests ============

    function test_GetRegulationLogs_LGPD() public {
        // Create LGPD logs
        for (uint i = 0; i < 2; i++) {
            bytes32 logId = keccak256(abi.encodePacked("lgpd_log_", i));
            auditLogger.logCompliance(
                logId,
                user1,
                "LGPD",
                7,
                true,
                ipfsCID1,
                "",
                false
            );
        }

        // Create GDPR log
        auditLogger.logCompliance(
            logId2,
            user1,
            "GDPR",
            22,
            true,
            ipfsCID1,
            "",
            false
        );

        bytes32[] memory lgpdLogs = auditLogger.getRegulationLogs("LGPD");
        bytes32[] memory gdprLogs = auditLogger.getRegulationLogs("GDPR");

        assertEq(lgpdLogs.length, 2);
        assertEq(gdprLogs.length, 1);
    }

    // ============ Compliance Statistics Tests ============

    function test_GetComplianceStats_AllPassed() public {
        // Create 10 passing logs
        for (uint i = 0; i < 10; i++) {
            bytes32 logId = keccak256(abi.encodePacked("log_", i));
            auditLogger.logCompliance(
                logId,
                user1,
                "LGPD",
                7,
                true,
                ipfsCID1,
                "",
                false
            );
        }

        (uint256 total, uint256 violations, uint256 rate) = auditLogger.getComplianceStats();

        assertEq(total, 10);
        assertEq(violations, 0);
        assertEq(rate, 10000);  // 100% in basis points
    }

    function test_GetComplianceStats_SomeViolations() public {
        // 7 passed, 3 violations
        for (uint i = 0; i < 10; i++) {
            bytes32 logId = keccak256(abi.encodePacked("log_", i));
            bool passed = i < 7;

            auditLogger.logCompliance(
                logId,
                user1,
                "LGPD",
                7,
                passed,
                ipfsCID1,
                "",
                false
            );
        }

        (uint256 total, uint256 violations, uint256 rate) = auditLogger.getComplianceStats();

        assertEq(total, 10);
        assertEq(violations, 3);
        assertEq(rate, 7000);  // 70% in basis points
    }

    function test_GetComplianceStats_EmptyState() public {
        (uint256 total, uint256 violations, uint256 rate) = auditLogger.getComplianceStats();

        assertEq(total, 0);
        assertEq(violations, 0);
        assertEq(rate, 10000);  // 100% (no logs = perfect compliance)
    }

    // ============ Gas Optimization Tests ============

    function test_GasCost_LogCompliance() public {
        uint256 gasBefore = gasleft();

        auditLogger.logCompliance(
            logId1,
            user1,
            "LGPD",
            7,
            true,
            ipfsCID1,
            "",
            false
        );

        uint256 gasUsed = gasBefore - gasleft();

        console2.log("Gas used for logCompliance:", gasUsed);

        // Audit logging with IPFS/Arweave integration requires more gas
        // Includes event emission, storage writes, and string handling
        // Expected: ~296k gas for immutable audit trail
        assertLt(gasUsed, 300000, "Gas cost too high for logging");
    }

    function test_GasCost_GetAuditLog() public {
        // Setup: Create log
        auditLogger.logCompliance(
            logId1,
            user1,
            "LGPD",
            7,
            true,
            ipfsCID1,
            "",
            false
        );

        uint256 gasBefore = gasleft();
        auditLogger.getAuditLog(logId1);
        uint256 gasUsed = gasBefore - gasleft();

        console2.log("Gas used for getAuditLog:", gasUsed);

        // Read should be cheap
        assertLt(gasUsed, 10000, "Gas cost too high for reading");
    }

    // ============ Integration Tests ============

    function test_FullAuditWorkflow() public {
        // 1. User grants consent
        auditLogger.logCompliance(
            logId1,
            user1,
            "LGPD",
            7,
            true,
            ipfsCID1,
            "",
            false
        );

        // 2. User accesses data
        bytes32 accessLogId = keccak256("access_log");
        auditLogger.logCompliance(
            accessLogId,
            user1,
            "LGPD",
            16,
            true,
            "access_cid",
            "",
            false
        );

        // 3. Upgrade to permanent storage
        auditLogger.updateLogReferences(logId1, ipfsCID1, arweaveTxId1);

        // Verify workflow
        bytes32[] memory history = auditLogger.getUserAuditHistory(user1);
        assertEq(history.length, 2);

        AuditLogger.AuditLog memory consentLog = auditLogger.getAuditLog(logId1);
        assertTrue(consentLog.permanent);
        assertEq(consentLog.arweaveTxId, arweaveTxId1);
    }

    function test_MultiRegulationCompliance() public {
        // LGPD Article 7
        auditLogger.logCompliance(
            keccak256("lgpd_7"),
            user1,
            "LGPD",
            7,
            true,
            "cid1",
            "",
            false
        );

        // GDPR Article 22
        auditLogger.logCompliance(
            keccak256("gdpr_22"),
            user1,
            "GDPR",
            22,
            true,
            "cid2",
            "",
            false
        );

        // AI Act Article 13
        auditLogger.logCompliance(
            keccak256("ai_act_13"),
            user1,
            "AI_ACT",
            13,
            true,
            "cid3",
            "",
            false
        );

        // Verify all regulations tracked
        assertEq(auditLogger.getRegulationLogs("LGPD").length, 1);
        assertEq(auditLogger.getRegulationLogs("GDPR").length, 1);
        assertEq(auditLogger.getRegulationLogs("AI_ACT").length, 1);

        (uint256 total,,) = auditLogger.getComplianceStats();
        assertEq(total, 3);
    }

    // ============ Fuzz Tests ============

    function testFuzz_LogComplianceWithRandomInputs(
        address user,
        uint8 article,
        bool passed
    ) public {
        vm.assume(user != address(0));
        vm.assume(article > 0 && article < 100);

        bytes32 logId = keccak256(abi.encodePacked(user, article, passed));

        auditLogger.logCompliance(
            logId,
            user,
            "LGPD",
            article,
            passed,
            "random_cid",
            "",
            false
        );

        AuditLogger.AuditLog memory log = auditLogger.getAuditLog(logId);

        assertEq(log.article, article);
        assertEq(log.passed, passed);
    }
}
