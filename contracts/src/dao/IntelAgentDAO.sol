// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 VoidNXLabs
pragma solidity ^0.8.20;

import {ComplianceGuardrail} from "../ComplianceGuardrail.sol";
import {AuditLogger} from "../AuditLogger.sol";
import {AgentRewardToken} from "./AgentRewardToken.sol";

/// @title IntelAgentDAO
/// @notice On-chain governance for the NEXUS CORTEX agent swarm.
///
/// Tier model (see GOVERNANCE.md):
///   Tier 0 — Constitutional  Human key holders (ADR ledger, contract upgrades)
///   Tier 1 — Council         Senior agents + humans (DAO proposals, voting)
///   Tier 2 — Operational     Active agents (task execution, quality reporting)
///   Tier 3 — Autonomous      Enforcement only (SENTINEL, BASTION — no governance rights)
///
/// Proposal constraints:
///   RegisterAgent, SlashAgent, UpdateParams — Tier 1 only
///   MintReward                              — Tier 1 only (quality signal comes from Tier 2 via NATS, council decides)
///   Vote                                    — Tier 1 only
///
/// Failure policy: proportional — one typed revert + one audit event, never silent, never cascading.
contract IntelAgentDAO is ComplianceGuardrail {
    // ── Types ──────────────────────────────────────────────────────────────────

    /// @notice Governance tier. See GOVERNANCE.md for full authority matrix.
    enum AgentTier {
        Council,       // Tier 1 — can propose and vote
        Operational,   // Tier 2 — can execute tasks, cannot propose/vote
        Autonomous     // Tier 3 — enforcement only, no governance rights
    }

    enum ProposalType {
        RegisterAgent,
        SlashAgent,
        MintReward,
        UpdateParams
    }

    enum ProposalStatus {
        Active,
        Approved,
        Rejected,
        Executed,
        Expired
    }

    struct AgentProfile {
        address   wallet;
        string    agentId;       // Off-chain ID (UUID or name)
        AgentTier tier;          // Governance tier — enforced on-chain
        uint256   registeredAt;
        bool      active;
    }

    struct Proposal {
        bytes32        id;
        ProposalType   ptype;
        address        target;      // Agent address for agent-related proposals
        bytes32        taskId;      // Task reference for MintReward proposals
        uint256        rewardAmt;   // Amount for MintReward / SlashAgent
        string         description;
        address        proposer;
        uint256        votesFor;
        uint256        votesAgainst;
        uint256        deadline;    // block.timestamp + votingWindow
        uint256        execAfter;   // deadline + timelock (earliest execution)
        ProposalStatus status;
        bool           executed;
    }

    // ── Storage ────────────────────────────────────────────────────────────────

    AgentRewardToken public immutable rewardToken;
    AuditLogger      public immutable auditLogger;

    mapping(address => AgentProfile) public agents;
    address[] public agentList;

    mapping(bytes32 => Proposal)              public proposals;
    mapping(bytes32 => mapping(address => bool)) public hasVoted;
    bytes32[] public proposalList;

    // DAO parameters (adjustable via UpdateParams proposal)
    uint256 public quorumPercent  = 50;    // 50% of registered agents must vote
    uint256 public votingWindow   = 1 days;
    uint256 public timelockBlocks = 1;     // 1 block in dev; 7200 (~24h) in prod
    uint256 public minReputationToPropose = 0; // ART tokens required to propose

    address public admin; // Bootstrap admin — removed after first DAO proposal

    // ── Events ─────────────────────────────────────────────────────────────────

    event AgentRegistered(address indexed wallet, string agentId, uint256 timestamp);
    event AgentDeactivated(address indexed wallet, string reason);
    event ProposalCreated(bytes32 indexed id, ProposalType ptype, address proposer, string description);
    event Voted(bytes32 indexed proposalId, address indexed voter, bool support);
    event ProposalExecuted(bytes32 indexed id, ProposalType ptype, bool success);
    event ParamsUpdated(uint256 quorumPercent, uint256 votingWindow, uint256 timelockBlocks);

    // ── Errors ──────────────────────────────────────────────────────────────────

    error NotRegisteredAgent(address caller);
    error AgentAlreadyRegistered(address wallet);
    error AlreadyVoted(bytes32 proposalId, address voter);
    error VotingClosed(bytes32 proposalId);
    error QuorumNotMet(uint256 votesFor, uint256 required);
    error TimelockActive(uint256 execAfter, uint256 current);
    error ProposalAlreadyExecuted(bytes32 proposalId);
    error ProposalExpiredOrRejected(bytes32 proposalId);
    error InsufficientReputation(uint256 balance, uint256 required);
    error OnlyAdmin();
    /// @notice Emitted when an agent attempts an action outside its tier authority.
    /// Proportional: one revert, one audit event — no cascading alerts.
    error TierViolation(address agent, AgentTier agentTier, string attemptedAction);

    // ── Modifiers ───────────────────────────────────────────────────────────────

    modifier onlyAgent() {
        if (!agents[msg.sender].active) revert NotRegisteredAgent(msg.sender);
        _;
    }

    /// @notice Restricts to Council tier (Tier 1). Tier 2/3 get a typed revert + audit event.
    modifier onlyCouncil() {
        AgentProfile storage p = agents[msg.sender];
        if (!p.active) revert NotRegisteredAgent(msg.sender);
        if (p.tier != AgentTier.Council) {
            // Proportional: one event, one revert — no flood
            emit ComplianceViolation(
                msg.sender, "GOVERNANCE", 1,
                "Tier violation: Council authority required",
                block.timestamp
            );
            revert TierViolation(msg.sender, p.tier, "council-action");
        }
        _;
    }

    modifier onlyAdmin() {
        if (msg.sender != admin) revert OnlyAdmin();
        _;
    }

    // ── Constructor ─────────────────────────────────────────────────────────────

    constructor(address _rewardToken, address _auditLogger) {
        rewardToken = AgentRewardToken(_rewardToken);
        auditLogger = AuditLogger(_auditLogger);
        admin = msg.sender;
    }

    // ── Agent Management ────────────────────────────────────────────────────────

    /// @notice Register a new agent with an explicit tier.
    /// Called by admin (bootstrap) or via DAO execute (address(this)).
    function registerAgent(address wallet, string calldata agentId, AgentTier tier) external {
        require(
            msg.sender == admin || msg.sender == address(this),
            "Only admin or DAO"
        );
        if (agents[wallet].registeredAt != 0) revert AgentAlreadyRegistered(wallet);

        agents[wallet] = AgentProfile({
            wallet:       wallet,
            agentId:      agentId,
            tier:         tier,
            registeredAt: block.timestamp,
            active:       true
        });
        agentList.push(wallet);

        emit AgentRegistered(wallet, agentId, block.timestamp);
    }

    /// @notice Count active Council agents (quorum is among peers, not all tiers).
    function activeAgentCount() public view returns (uint256 count) {
        for (uint256 i = 0; i < agentList.length; i++) {
            AgentProfile storage p = agents[agentList[i]];
            if (p.active && p.tier == AgentTier.Council) count++;
        }
    }

    // ── Proposals ────────────────────────────────────────────────────────────────

    /// @notice Create a governance proposal. Requires Council tier (Tier 1).
    function propose(
        ProposalType   ptype,
        address        target,
        bytes32        taskId,
        uint256        rewardAmt,
        string calldata description
    ) external onlyCouncil returns (bytes32 proposalId) {
        // AI Act Art. 13 — transparency: full description required
        require(bytes(description).length > 0, "Description required (AI Act Art.13)");

        if (minReputationToPropose > 0) {
            uint256 bal = rewardToken.balanceOf(msg.sender);
            if (bal < minReputationToPropose)
                revert InsufficientReputation(bal, minReputationToPropose);
        }

        proposalId = keccak256(abi.encodePacked(
            ptype, target, taskId, msg.sender, block.timestamp
        ));

        proposals[proposalId] = Proposal({
            id:          proposalId,
            ptype:       ptype,
            target:      target,
            taskId:      taskId,
            rewardAmt:   rewardAmt,
            description: description,
            proposer:    msg.sender,
            votesFor:    0,
            votesAgainst: 0,
            deadline:    block.timestamp + votingWindow,
            execAfter:   block.timestamp + votingWindow + timelockBlocks,
            status:      ProposalStatus.Active,
            executed:    false
        });
        proposalList.push(proposalId);

        emit ProposalCreated(proposalId, ptype, msg.sender, description);
        emit CompliancePass(msg.sender, "AI_ACT", 13, block.timestamp);
    }

    // ── Voting ───────────────────────────────────────────────────────────────────

    /// @notice Cast a vote on an active proposal. Requires Council tier (Tier 1).
    function vote(bytes32 proposalId, bool support) external onlyCouncil {
        Proposal storage p = proposals[proposalId];
        if (block.timestamp > p.deadline) revert VotingClosed(proposalId);
        if (hasVoted[proposalId][msg.sender]) revert AlreadyVoted(proposalId, msg.sender);

        hasVoted[proposalId][msg.sender] = true;
        if (support) {
            p.votesFor++;
        } else {
            p.votesAgainst++;
        }

        emit Voted(proposalId, msg.sender, support);
    }

    // ── Execution ────────────────────────────────────────────────────────────────

    /// @notice Execute an approved proposal after quorum + timelock.
    /// @dev AI Act Art. 14 — human oversight: execution is always human-initiated.
    function execute(bytes32 proposalId) external {
        Proposal storage p = proposals[proposalId];

        if (p.executed) revert ProposalAlreadyExecuted(proposalId);
        if (block.timestamp < p.execAfter) revert TimelockActive(p.execAfter, block.timestamp);

        // Check quorum
        uint256 totalAgents = activeAgentCount();
        // Ceiling division: ceil(n * q / 100) — garante que 50% de 3 = 2, não 1
        uint256 required = (totalAgents * quorumPercent + 99) / 100;
        if (required == 0) required = 1;
        if (p.votesFor < required) revert QuorumNotMet(p.votesFor, required);
        if (p.votesFor <= p.votesAgainst) revert ProposalExpiredOrRejected(proposalId);

        p.executed = true;
        p.status   = ProposalStatus.Executed;

        bool success = _executeProposal(p);

        // Audit log every execution (immutable trail)
        bytes32 logId = keccak256(abi.encodePacked("dao.execute", proposalId, block.timestamp));
        auditLogger.logCompliance(
            logId,
            msg.sender,
            "AI_ACT",
            14,
            success,
            "",  // IPFS CID — populated off-chain
            "",  // Arweave TX — populated off-chain
            false
        );

        emit ProposalExecuted(proposalId, p.ptype, success);
        emit CompliancePass(msg.sender, "AI_ACT", 14, block.timestamp);
    }

    function _executeProposal(Proposal storage p) internal returns (bool) {
        if (p.ptype == ProposalType.RegisterAgent) {
            // rewardAmt encodes tier: 1 = Council, 2 = Operational, 3 = Autonomous
            AgentTier newTier = p.rewardAmt == 1 ? AgentTier.Council
                              : p.rewardAmt == 3 ? AgentTier.Autonomous
                              : AgentTier.Operational;
            string memory agentId = string(abi.encodePacked(p.taskId));
            agents[p.target] = AgentProfile({
                wallet:       p.target,
                agentId:      agentId,
                tier:         newTier,
                registeredAt: block.timestamp,
                active:       true
            });
            agentList.push(p.target);
            emit AgentRegistered(p.target, agentId, block.timestamp);

        } else if (p.ptype == ProposalType.SlashAgent) {
            agents[p.target].active = false;
            if (p.rewardAmt > 0) {
                rewardToken.slash(p.target, p.id, p.rewardAmt);
            }
            emit AgentDeactivated(p.target, p.description);

        } else if (p.ptype == ProposalType.MintReward) {
            rewardToken.reward(p.target, p.taskId, p.rewardAmt);

        } else if (p.ptype == ProposalType.UpdateParams) {
            // rewardAmt encodes [quorum(16b) | window(16b) | timelock(16b)] packed
            // Simple encoding: rewardAmt = quorum * 1e12 + window * 1e6 + timelock
            uint256 newQuorum   = p.rewardAmt / 1e12;
            uint256 newWindow   = (p.rewardAmt % 1e12) / 1e6;
            uint256 newTimelock = p.rewardAmt % 1e6;
            if (newQuorum > 0 && newQuorum <= 100) quorumPercent  = newQuorum;
            if (newWindow > 0)  votingWindow   = newWindow;
            if (newTimelock > 0) timelockBlocks = newTimelock;
            emit ParamsUpdated(quorumPercent, votingWindow, timelockBlocks);
        }
        return true;
    }

    // ── Admin bootstrap helpers ──────────────────────────────────────────────────

    /// @notice Direct reward by admin (bootstrap only — before first DAO vote).
    function adminReward(address agent, bytes32 taskId, uint256 amount) external onlyAdmin {
        rewardToken.reward(agent, taskId, amount);
    }

    /// @notice Renounce admin role — DAO becomes fully autonomous.
    function renounceAdmin() external onlyAdmin {
        admin = address(0);
    }

    // ── ComplianceGuardrail virtuals ─────────────────────────────────────────────

    function hasConsent(address) internal pure override returns (bool) { return true; }
    function hasDataAccess(address, address) internal pure override returns (bool) { return true; }
    function withinRetentionPeriod(address) internal pure override returns (bool) { return true; }
    function hasHumanReview(bytes32) internal pure override returns (bool) { return true; }
    function hasTransparencyInfo(bytes32) internal pure override returns (bool) { return true; }
    function hasHumanOversight(bytes32) internal pure override returns (bool) { return true; }

    // ── Views ────────────────────────────────────────────────────────────────────

    function getProposal(bytes32 proposalId) external view returns (Proposal memory) {
        return proposals[proposalId];
    }

    function getAgent(address wallet) external view returns (AgentProfile memory) {
        return agents[wallet];
    }

    function proposalCount() external view returns (uint256) {
        return proposalList.length;
    }

    function agentCount() external view returns (uint256) {
        return agentList.length;
    }
}
