// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.20;

import {Test, console2} from "forge-std/Test.sol";
import {AgentRewardToken} from "../src/dao/AgentRewardToken.sol";
import {IntelAgentDAO} from "../src/dao/IntelAgentDAO.sol";
import {AuditLogger} from "../src/AuditLogger.sol";

contract IntelAgentDAOTest is Test {
    AgentRewardToken token;
    AuditLogger      logger;
    IntelAgentDAO    dao;

    address admin  = address(this);
    address alice  = makeAddr("alice");
    address bob    = makeAddr("bob");
    address carol  = makeAddr("carol");
    address newbie = makeAddr("newbie");

    function setUp() public {
        token  = new AgentRewardToken();
        logger = new AuditLogger();
        dao    = new IntelAgentDAO(address(token), address(logger));
        token.transferOwnership(address(dao));

        // Register initial agents — alice/bob/carol are Council (Tier 1)
        dao.registerAgent(alice, "alice-agent", IntelAgentDAO.AgentTier.Council);
        dao.registerAgent(bob,   "bob-agent",   IntelAgentDAO.AgentTier.Council);
        dao.registerAgent(carol, "carol-agent", IntelAgentDAO.AgentTier.Council);
    }

    // ── Registration ──────────────────────────────────────────────────────────

    function test_RegisterAgent() public view {
        IntelAgentDAO.AgentProfile memory p = dao.getAgent(alice);
        assertEq(p.wallet,  alice);
        assertEq(p.agentId, "alice-agent");
        assertTrue(p.active);
    }

    function test_RegisterAgent_Duplicate_Reverts() public {
        vm.expectRevert(abi.encodeWithSelector(IntelAgentDAO.AgentAlreadyRegistered.selector, alice));
        dao.registerAgent(alice, "alice-dup", IntelAgentDAO.AgentTier.Council);
    }

    function test_ActiveAgentCount() public view {
        assertEq(dao.activeAgentCount(), 3);
    }

    // ── Proposals ─────────────────────────────────────────────────────────────

    function test_Propose_MintReward() public returns (bytes32 pid) {
        bytes32 taskId = keccak256("task-001");
        vm.prank(alice);
        pid = dao.propose(
            IntelAgentDAO.ProposalType.MintReward,
            bob,
            taskId,
            1e18,
            "Reward bob for completing task-001 with quality score 0.95"
        );
        assertTrue(pid != bytes32(0));

        IntelAgentDAO.Proposal memory p = dao.getProposal(pid);
        assertEq(p.target,    bob);
        assertEq(p.taskId,    taskId);
        assertEq(p.rewardAmt, 1e18);
        assertEq(uint8(p.status), uint8(IntelAgentDAO.ProposalStatus.Active));
    }

    function test_Propose_RequiresDescription() public {
        vm.prank(alice);
        vm.expectRevert("Description required (AI Act Art.13)");
        dao.propose(IntelAgentDAO.ProposalType.MintReward, bob, bytes32(0), 1e18, "");
    }

    function test_Propose_NonAgent_Reverts() public {
        vm.prank(newbie);
        vm.expectRevert(abi.encodeWithSelector(IntelAgentDAO.NotRegisteredAgent.selector, newbie));
        dao.propose(IntelAgentDAO.ProposalType.MintReward, bob, bytes32(0), 1e18, "test");
    }

    function test_Propose_OperationalTier_Reverts() public {
        address opsAgent = makeAddr("ops");
        dao.registerAgent(opsAgent, "ops-agent", IntelAgentDAO.AgentTier.Operational);

        vm.prank(opsAgent);
        vm.expectRevert(
            abi.encodeWithSelector(
                IntelAgentDAO.TierViolation.selector,
                opsAgent,
                IntelAgentDAO.AgentTier.Operational,
                "council-action"
            )
        );
        dao.propose(IntelAgentDAO.ProposalType.MintReward, bob, bytes32(0), 1e18, "ops trying to propose");
    }

    function test_Vote_OperationalTier_Reverts() public {
        bytes32 pid = _proposeMintReward(alice, bob, 1e18);

        address opsAgent = makeAddr("ops2");
        dao.registerAgent(opsAgent, "ops-agent-2", IntelAgentDAO.AgentTier.Operational);

        vm.prank(opsAgent);
        vm.expectRevert(
            abi.encodeWithSelector(
                IntelAgentDAO.TierViolation.selector,
                opsAgent,
                IntelAgentDAO.AgentTier.Operational,
                "council-action"
            )
        );
        dao.vote(pid, true);
    }

    function test_ActiveAgentCount_OnlyCouncil() public {
        // alice, bob, carol = Council (3)
        assertEq(dao.activeAgentCount(), 3);

        // Add Operational agent — should NOT count for quorum
        address opsAgent = makeAddr("ops3");
        dao.registerAgent(opsAgent, "ops-3", IntelAgentDAO.AgentTier.Operational);
        assertEq(dao.activeAgentCount(), 3); // still 3
    }

    // ── Voting ────────────────────────────────────────────────────────────────

    function test_Vote_ForAndAgainst() public {
        bytes32 pid = _proposeMintReward(alice, bob, 1e18);

        vm.prank(alice); dao.vote(pid, true);
        vm.prank(bob);   dao.vote(pid, true);
        vm.prank(carol); dao.vote(pid, false);

        IntelAgentDAO.Proposal memory p = dao.getProposal(pid);
        assertEq(p.votesFor,     2);
        assertEq(p.votesAgainst, 1);
    }

    function test_Vote_DoubleVote_Reverts() public {
        bytes32 pid = _proposeMintReward(alice, bob, 1e18);

        vm.prank(alice); dao.vote(pid, true);

        vm.prank(alice);
        vm.expectRevert(abi.encodeWithSelector(IntelAgentDAO.AlreadyVoted.selector, pid, alice));
        dao.vote(pid, true);
    }

    function test_Vote_AfterDeadline_Reverts() public {
        bytes32 pid = _proposeMintReward(alice, bob, 1e18);
        vm.warp(block.timestamp + 2 days); // past voting window

        vm.prank(alice);
        vm.expectRevert(abi.encodeWithSelector(IntelAgentDAO.VotingClosed.selector, pid));
        dao.vote(pid, true);
    }

    // ── Execution ─────────────────────────────────────────────────────────────

    function test_Execute_MintReward() public {
        bytes32 pid = _proposeMintReward(alice, bob, 1e18);

        // All 3 agents vote for (100% > 50% quorum)
        vm.prank(alice); dao.vote(pid, true);
        vm.prank(bob);   dao.vote(pid, true);
        vm.prank(carol); dao.vote(pid, true);

        // Advance past voting window + timelock
        vm.warp(block.timestamp + 1 days + 2);
        vm.roll(block.number + 2);

        dao.execute(pid);

        assertEq(token.balanceOf(bob), 1e18);

        IntelAgentDAO.Proposal memory p = dao.getProposal(pid);
        assertTrue(p.executed);
        assertEq(uint8(p.status), uint8(IntelAgentDAO.ProposalStatus.Executed));
    }

    function test_Execute_QuorumNotMet_Reverts() public {
        bytes32 pid = _proposeMintReward(alice, bob, 1e18);

        // Only 1 of 3 votes for (33% < 50% quorum)
        vm.prank(alice); dao.vote(pid, true);

        vm.warp(block.timestamp + 1 days + 2);
        vm.roll(block.number + 2);

        vm.expectRevert(abi.encodeWithSelector(IntelAgentDAO.QuorumNotMet.selector, 1, 2));
        dao.execute(pid);
    }

    function test_Execute_TimelockActive_Reverts() public {
        bytes32 pid = _proposeMintReward(alice, bob, 1e18);

        vm.prank(alice); dao.vote(pid, true);
        vm.prank(bob);   dao.vote(pid, true);
        vm.prank(carol); dao.vote(pid, true);

        // Still within voting window — timelock not elapsed
        vm.expectRevert();
        dao.execute(pid);
    }

    function test_Execute_DoubleExecution_Reverts() public {
        bytes32 pid = _proposeMintReward(alice, bob, 1e18);
        vm.prank(alice); dao.vote(pid, true);
        vm.prank(bob);   dao.vote(pid, true);
        vm.prank(carol); dao.vote(pid, true);
        vm.warp(block.timestamp + 1 days + 2);
        vm.roll(block.number + 2);
        dao.execute(pid);

        vm.expectRevert(abi.encodeWithSelector(IntelAgentDAO.ProposalAlreadyExecuted.selector, pid));
        dao.execute(pid);
    }

    // ── Slash ─────────────────────────────────────────────────────────────────

    function test_Execute_SlashAgent() public {
        // First reward alice so she has tokens to slash
        dao.adminReward(alice, keccak256("task-0"), 5e18);
        assertEq(token.balanceOf(alice), 5e18);

        bytes32 pid;
        vm.prank(bob);
        pid = dao.propose(
            IntelAgentDAO.ProposalType.SlashAgent,
            alice,
            bytes32(0),
            2e18,
            "Alice submitted low-quality output on task-0"
        );
        vm.prank(alice); dao.vote(pid, false); // alice votes against her own slash
        vm.prank(bob);   dao.vote(pid, true);
        vm.prank(carol); dao.vote(pid, true);

        vm.warp(block.timestamp + 1 days + 2);
        vm.roll(block.number + 2);
        dao.execute(pid);

        // alice deactivated + 2e18 burned
        assertFalse(dao.getAgent(alice).active);
        assertEq(token.balanceOf(alice), 3e18);
    }

    // ── Token soulbound ───────────────────────────────────────────────────────

    function test_Token_Transfer_Reverts() public {
        dao.adminReward(alice, keccak256("task-x"), 1e18);
        vm.prank(alice);
        vm.expectRevert(AgentRewardToken.TransferNotAllowed.selector);
        token.transfer(bob, 1e18);
    }

    // ── Admin ─────────────────────────────────────────────────────────────────

    function test_AdminReward_DirectMint() public {
        dao.adminReward(alice, keccak256("task-direct"), 3e18);
        assertEq(token.balanceOf(alice), 3e18);
    }

    function test_RenounceAdmin() public {
        dao.renounceAdmin();
        assertEq(dao.admin(), address(0));

        vm.expectRevert(IntelAgentDAO.OnlyAdmin.selector);
        dao.adminReward(alice, bytes32(0), 1e18);
    }

    // ── Fuzz ──────────────────────────────────────────────────────────────────

    function testFuzz_RewardAmount(uint128 amount) public {
        vm.assume(amount > 0 && amount < 1e27);
        bytes32 taskId = keccak256(abi.encodePacked(amount));
        dao.adminReward(alice, taskId, uint256(amount));
        assertEq(token.balanceOf(alice), uint256(amount));
    }

    // ── Helpers ───────────────────────────────────────────────────────────────

    function _proposeMintReward(
        address proposer,
        address target,
        uint256 amount
    ) internal returns (bytes32) {
        bytes32 taskId = keccak256(abi.encodePacked(proposer, target, amount, block.timestamp));
        vm.prank(proposer);
        return dao.propose(
            IntelAgentDAO.ProposalType.MintReward,
            target,
            taskId,
            amount,
            "Reward agent for passing QualityGate"
        );
    }
}
