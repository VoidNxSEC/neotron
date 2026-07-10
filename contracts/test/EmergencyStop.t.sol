// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {Test, console2} from "forge-std/Test.sol";
import {EmergencyStop} from "../src/EmergencyStop.sol";

/// @dev Concrete implementation for testing the abstract contract
contract MockProtocol is EmergencyStop {
    uint256 public value;

    constructor(address guardian, uint256 timelockDelay)
        EmergencyStop(guardian, timelockDelay)
    {}

    function protectedAction(uint256 newValue) external whenNotPaused {
        value = newValue;
    }

    function pausedOnlyAction() external whenPaused returns (bool) {
        return true;
    }
}

contract EmergencyStopTest is Test {
    MockProtocol public protocol;

    address public guardian1 = address(0x1);
    address public guardian2 = address(0x2);
    address public user = address(0x3);

    uint256 public constant TIMELOCK_DELAY = 1 days;

    function setUp() public {
        vm.prank(guardian1);
        protocol = new MockProtocol(guardian1, TIMELOCK_DELAY);
    }

    // ============ Initial State ============

    function test_InitialState() public view {
        assertFalse(protocol.paused());
        assertTrue(protocol.isGuardian(guardian1));
        assertEq(protocol.guardianCount(), 1);
        assertEq(protocol.unpauseDelay(), TIMELOCK_DELAY);
    }

    // ============ Pause Tests ============

    function test_Pause() public {
        vm.prank(guardian1);
        protocol.pause("Security incident");

        assertTrue(protocol.paused());
        assertEq(protocol.pauseReason(), "Security incident");
        assertGt(protocol.pausedAt(), 0);
    }

    function test_PauseBlocksProtectedActions() public {
        vm.prank(guardian1);
        protocol.pause("Test");

        vm.expectRevert(EmergencyStop.ContractPaused.selector);
        protocol.protectedAction(42);
    }

    function test_PausedOnlyActionWhenPaused() public {
        vm.prank(guardian1);
        protocol.pause("Test");

        vm.prank(guardian1);
        assertTrue(protocol.pausedOnlyAction());
    }

    function test_PausedOnlyActionWhenNotPaused() public {
        vm.expectRevert(EmergencyStop.ContractNotPaused.selector);
        protocol.pausedOnlyAction();
    }

    function test_RevertPauseNotGuardian() public {
        vm.prank(user);
        vm.expectRevert(EmergencyStop.NotGuardian.selector);
        protocol.pause("Unauthorized");
    }

    function test_RevertPauseWhenAlreadyPaused() public {
        vm.prank(guardian1);
        protocol.pause("First");

        vm.prank(guardian1);
        vm.expectRevert(EmergencyStop.ContractPaused.selector);
        protocol.pause("Second");
    }

    event Paused(address indexed by, string reason, uint256 timestamp);

    function test_PauseEmitsEvent() public {
        vm.prank(guardian1);
        vm.expectEmit(true, false, false, true);
        emit Paused(guardian1, "Security incident", block.timestamp);
        protocol.pause("Security incident");
    }

    // ============ Unpause Tests ============

    function test_UnpauseFlow() public {
        // Pause
        vm.prank(guardian1);
        protocol.pause("Test");
        assertTrue(protocol.paused());

        // Request unpause
        vm.prank(guardian1);
        protocol.requestUnpause();
        assertGt(protocol.unpauseRequestedAt(), 0);

        // Wait for timelock
        vm.warp(block.timestamp + TIMELOCK_DELAY);

        // Execute unpause
        vm.prank(guardian1);
        protocol.executeUnpause();

        assertFalse(protocol.paused());
        assertEq(protocol.pausedAt(), 0);
        assertEq(protocol.unpauseRequestedAt(), 0);
    }

    function test_RevertUnpauseBeforeTimelock() public {
        vm.prank(guardian1);
        protocol.pause("Test");

        vm.prank(guardian1);
        protocol.requestUnpause();

        // Try to execute before timelock expires
        vm.prank(guardian1);
        vm.expectRevert(
            abi.encodeWithSelector(
                EmergencyStop.UnpauseTimelockActive.selector,
                block.timestamp + TIMELOCK_DELAY
            )
        );
        protocol.executeUnpause();
    }

    function test_RevertUnpauseWithoutRequest() public {
        vm.prank(guardian1);
        protocol.pause("Test");

        vm.prank(guardian1);
        vm.expectRevert(EmergencyStop.UnpauseNotRequested.selector);
        protocol.executeUnpause();
    }

    function test_RevertRequestUnpauseNotPaused() public {
        vm.prank(guardian1);
        vm.expectRevert(EmergencyStop.ContractNotPaused.selector);
        protocol.requestUnpause();
    }

    function test_PauseResetsUnpauseRequest() public {
        // Pause and request unpause
        vm.startPrank(guardian1);
        protocol.pause("First");
        protocol.requestUnpause();
        assertGt(protocol.unpauseRequestedAt(), 0);

        // Wait and unpause
        vm.warp(block.timestamp + TIMELOCK_DELAY);
        protocol.executeUnpause();

        // Pause again - should reset unpause state
        protocol.pause("Second");
        assertEq(protocol.unpauseRequestedAt(), 0);
        vm.stopPrank();
    }

    function test_ProtectedActionWorksAfterUnpause() public {
        // Pause
        vm.prank(guardian1);
        protocol.pause("Test");

        // Full unpause flow
        vm.prank(guardian1);
        protocol.requestUnpause();
        vm.warp(block.timestamp + TIMELOCK_DELAY);
        vm.prank(guardian1);
        protocol.executeUnpause();

        // Should work now
        protocol.protectedAction(42);
        assertEq(protocol.value(), 42);
    }

    // ============ Guardian Management ============

    function test_AddGuardian() public {
        vm.prank(guardian1);
        protocol.addGuardian(guardian2);

        assertTrue(protocol.isGuardian(guardian2));
        assertEq(protocol.guardianCount(), 2);
    }

    function test_SecondGuardianCanPause() public {
        vm.prank(guardian1);
        protocol.addGuardian(guardian2);

        vm.prank(guardian2);
        protocol.pause("Guardian 2 pause");

        assertTrue(protocol.paused());
    }

    function test_RemoveGuardian() public {
        vm.prank(guardian1);
        protocol.addGuardian(guardian2);

        vm.prank(guardian1);
        protocol.removeGuardian(guardian2);

        assertFalse(protocol.isGuardian(guardian2));
        assertEq(protocol.guardianCount(), 1);
    }

    function test_RevertRemoveLastGuardian() public {
        vm.prank(guardian1);
        vm.expectRevert(EmergencyStop.CannotRemoveLastGuardian.selector);
        protocol.removeGuardian(guardian1);
    }

    function test_RevertAddGuardianNotGuardian() public {
        vm.prank(user);
        vm.expectRevert(EmergencyStop.NotGuardian.selector);
        protocol.addGuardian(address(0x99));
    }

    // ============ Timelock Config ============

    function test_SetUnpauseDelay() public {
        vm.prank(guardian1);
        protocol.setUnpauseDelay(2 days);
        assertEq(protocol.unpauseDelay(), 2 days);
    }

    // ============ Fuzz Tests ============

    function testFuzz_UnpauseAfterDelay(uint256 delay) public {
        delay = bound(delay, 0, 365 days);

        vm.prank(guardian1);
        protocol.setUnpauseDelay(delay);

        vm.prank(guardian1);
        protocol.pause("Fuzz test");

        vm.prank(guardian1);
        protocol.requestUnpause();

        vm.warp(block.timestamp + delay);

        vm.prank(guardian1);
        protocol.executeUnpause();

        assertFalse(protocol.paused());
    }
}
