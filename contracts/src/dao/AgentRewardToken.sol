// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 VoidNXLabs
pragma solidity ^0.8.20;

import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";

/// @title AgentRewardToken
/// @notice Soulbound ERC-20 reward token for IntelAgent swarm members.
///
/// Minted by IntelAgentDAO when an agent passes a QualityGate.
/// Soulbound: cannot be transferred between wallets after minting.
/// Only the DAO contract (owner) can mint.
///
/// Token economics:
///   - 1 ART per task that passes QualityGate (score >= threshold)
///   - Burned automatically on agent slash (reputation penalty)
///   - Accrued balance = on-chain reputation signal
contract AgentRewardToken is ERC20, Ownable {
    // ── Events ────────────────────────────────────────────────────────────────

    event AgentRewarded(address indexed agent, bytes32 indexed taskId, uint256 amount);
    event AgentSlashed(address indexed agent, bytes32 indexed proposalId, uint256 amount);

    // ── Errors ────────────────────────────────────────────────────────────────

    error TransferNotAllowed();
    error InsufficientBalanceToSlash(address agent, uint256 balance, uint256 requested);

    // ── Constructor ───────────────────────────────────────────────────────────

    constructor() ERC20("AgentRewardToken", "ART") Ownable(msg.sender) {}

    // ── Minting (DAO only) ────────────────────────────────────────────────────

    /// @notice Mint reward tokens to an agent for passing a QualityGate.
    /// @param agent  Agent's wallet address
    /// @param taskId Task identifier (for audit trail)
    /// @param amount Number of tokens to mint (in wei, 18 decimals)
    function reward(address agent, bytes32 taskId, uint256 amount) external onlyOwner {
        _mint(agent, amount);
        emit AgentRewarded(agent, taskId, amount);
    }

    /// @notice Burn tokens from a slashed agent.
    /// @param agent      Agent's wallet address
    /// @param proposalId DAO proposal that approved the slash
    /// @param amount     Amount to burn
    function slash(address agent, bytes32 proposalId, uint256 amount) external onlyOwner {
        uint256 bal = balanceOf(agent);
        if (bal < amount) revert InsufficientBalanceToSlash(agent, bal, amount);
        _burn(agent, amount);
        emit AgentSlashed(agent, proposalId, amount);
    }

    // ── Soulbound: block all transfers ────────────────────────────────────────

    /// @dev Override to block peer-to-peer transfers.
    ///      Mint (from == 0) and burn (to == 0) are still allowed.
    function _update(address from, address to, uint256 value) internal override {
        if (from != address(0) && to != address(0)) {
            revert TransferNotAllowed();
        }
        super._update(from, to, value);
    }
}
