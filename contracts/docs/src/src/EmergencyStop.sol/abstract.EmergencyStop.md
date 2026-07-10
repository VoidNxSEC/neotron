# EmergencyStop
**Title:**
EmergencyStop

**Author:**
NEXUS Platform

Circuit breaker with timelock for emergency pause/unpause

Provides pause functionality with governance controls
Features:
- Instant pause by any guardian
- Unpause requires timelock (default 24h)
- Multiple guardians supported
- Pause reason tracking for audit trail


## State Variables
### paused

```solidity
bool public paused
```


### pausedAt

```solidity
uint256 public pausedAt
```


### pauseReason

```solidity
string public pauseReason
```


### guardian

```solidity
address public guardian
```


### isGuardian

```solidity
mapping(address => bool) public isGuardian
```


### guardianCount

```solidity
uint256 public guardianCount
```


### unpauseDelay
Timelock delay for unpause (seconds)


```solidity
uint256 public unpauseDelay
```


### unpauseRequestedAt
Timestamp when unpause was requested


```solidity
uint256 public unpauseRequestedAt
```


### unpauseRequester
Address that requested unpause


```solidity
address public unpauseRequester
```


## Functions
### whenNotPaused


```solidity
modifier whenNotPaused() ;
```

### whenPaused


```solidity
modifier whenPaused() ;
```

### onlyGuardian


```solidity
modifier onlyGuardian() ;
```

### constructor


```solidity
constructor(address initialGuardian, uint256 timelockDelay) ;
```
**Parameters**

|Name|Type|Description|
|----|----|-----------|
|`initialGuardian`|`address`|First guardian address|
|`timelockDelay`|`uint256`|Timelock delay for unpause in seconds|


### pause

Pause the contract immediately (any guardian can call)


```solidity
function pause(string calldata reason) external onlyGuardian whenNotPaused;
```
**Parameters**

|Name|Type|Description|
|----|----|-----------|
|`reason`|`string`|Human-readable reason for the pause|


### requestUnpause

Request unpause (starts timelock)

Only guardians can request. Must wait unpauseDelay before executing.


```solidity
function requestUnpause() external onlyGuardian whenPaused;
```

### executeUnpause

Execute unpause after timelock expires

Any guardian can execute once timelock has passed


```solidity
function executeUnpause() external onlyGuardian whenPaused;
```

### addGuardian


```solidity
function addGuardian(address newGuardian) external onlyGuardian;
```

### removeGuardian


```solidity
function removeGuardian(address oldGuardian) external onlyGuardian;
```

### setUnpauseDelay


```solidity
function setUnpauseDelay(uint256 newDelay) external onlyGuardian;
```

## Events
### Paused

```solidity
event Paused(address indexed by, string reason, uint256 timestamp);
```

### UnpauseRequested

```solidity
event UnpauseRequested(address indexed by, uint256 executeAfter);
```

### Unpaused

```solidity
event Unpaused(address indexed by, uint256 timestamp);
```

### GuardianAdded

```solidity
event GuardianAdded(address indexed guardian);
```

### GuardianRemoved

```solidity
event GuardianRemoved(address indexed guardian);
```

### UnpauseDelayUpdated

```solidity
event UnpauseDelayUpdated(uint256 oldDelay, uint256 newDelay);
```

## Errors
### ContractPaused

```solidity
error ContractPaused();
```

### ContractNotPaused

```solidity
error ContractNotPaused();
```

### NotGuardian

```solidity
error NotGuardian();
```

### UnpauseTimelockActive

```solidity
error UnpauseTimelockActive(uint256 availableAt);
```

### UnpauseNotRequested

```solidity
error UnpauseNotRequested();
```

### CannotRemoveLastGuardian

```solidity
error CannotRemoveLastGuardian();
```

