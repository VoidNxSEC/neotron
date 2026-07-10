// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title EmergencyStop
 * @author NEXUS Platform
 * @notice Circuit breaker with timelock for emergency pause/unpause
 * @dev Provides pause functionality with governance controls
 *
 * Features:
 * - Instant pause by any guardian
 * - Unpause requires timelock (default 24h)
 * - Multiple guardians supported
 * - Pause reason tracking for audit trail
 */
abstract contract EmergencyStop {
    // ============ Storage ============

    bool public paused;
    uint256 public pausedAt;
    string public pauseReason;
    address public guardian;

    mapping(address => bool) public isGuardian;
    uint256 public guardianCount;

    /// @notice Timelock delay for unpause (seconds)
    uint256 public unpauseDelay;

    /// @notice Timestamp when unpause was requested
    uint256 public unpauseRequestedAt;

    /// @notice Address that requested unpause
    address public unpauseRequester;

    // ============ Events ============

    event Paused(address indexed by, string reason, uint256 timestamp);
    event UnpauseRequested(address indexed by, uint256 executeAfter);
    event Unpaused(address indexed by, uint256 timestamp);
    event GuardianAdded(address indexed guardian);
    event GuardianRemoved(address indexed guardian);
    event UnpauseDelayUpdated(uint256 oldDelay, uint256 newDelay);

    // ============ Errors ============

    error ContractPaused();
    error ContractNotPaused();
    error NotGuardian();
    error UnpauseTimelockActive(uint256 availableAt);
    error UnpauseNotRequested();
    error CannotRemoveLastGuardian();

    // ============ Modifiers ============

    modifier whenNotPaused() {
        if (paused) revert ContractPaused();
        _;
    }

    modifier whenPaused() {
        if (!paused) revert ContractNotPaused();
        _;
    }

    modifier onlyGuardian() {
        if (!isGuardian[msg.sender]) revert NotGuardian();
        _;
    }

    // ============ Constructor ============

    /**
     * @param initialGuardian First guardian address
     * @param timelockDelay Timelock delay for unpause in seconds
     */
    constructor(address initialGuardian, uint256 timelockDelay) {
        guardian = initialGuardian;
        isGuardian[initialGuardian] = true;
        guardianCount = 1;
        unpauseDelay = timelockDelay;
    }

    // ============ Emergency Controls ============

    /**
     * @notice Pause the contract immediately (any guardian can call)
     * @param reason Human-readable reason for the pause
     */
    function pause(string calldata reason) external onlyGuardian whenNotPaused {
        paused = true;
        pausedAt = block.timestamp;
        pauseReason = reason;

        // Reset any pending unpause
        unpauseRequestedAt = 0;
        unpauseRequester = address(0);

        emit Paused(msg.sender, reason, block.timestamp);
    }

    /**
     * @notice Request unpause (starts timelock)
     * @dev Only guardians can request. Must wait unpauseDelay before executing.
     */
    function requestUnpause() external onlyGuardian whenPaused {
        unpauseRequestedAt = block.timestamp;
        unpauseRequester = msg.sender;

        emit UnpauseRequested(msg.sender, block.timestamp + unpauseDelay);
    }

    /**
     * @notice Execute unpause after timelock expires
     * @dev Any guardian can execute once timelock has passed
     */
    function executeUnpause() external onlyGuardian whenPaused {
        if (unpauseRequestedAt == 0) revert UnpauseNotRequested();

        uint256 availableAt = unpauseRequestedAt + unpauseDelay;
        if (block.timestamp < availableAt) {
            revert UnpauseTimelockActive(availableAt);
        }

        paused = false;
        pausedAt = 0;
        pauseReason = "";
        unpauseRequestedAt = 0;
        unpauseRequester = address(0);

        emit Unpaused(msg.sender, block.timestamp);
    }

    // ============ Guardian Management ============

    function addGuardian(address newGuardian) external onlyGuardian {
        if (!isGuardian[newGuardian]) {
            isGuardian[newGuardian] = true;
            guardianCount++;
            emit GuardianAdded(newGuardian);
        }
    }

    function removeGuardian(address oldGuardian) external onlyGuardian {
        if (guardianCount <= 1) revert CannotRemoveLastGuardian();
        if (isGuardian[oldGuardian]) {
            isGuardian[oldGuardian] = false;
            guardianCount--;
            emit GuardianRemoved(oldGuardian);
        }
    }

    function setUnpauseDelay(uint256 newDelay) external onlyGuardian {
        emit UnpauseDelayUpdated(unpauseDelay, newDelay);
        unpauseDelay = newDelay;
    }
}
