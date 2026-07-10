# AuditLogger
**Title:**
AuditLogger

**Author:**
NEXUS Platform

On-chain audit logging with off-chain storage references (IPFS/Arweave)

Stores compliance events on-chain with pointers to full logs on decentralized storage
Design Philosophy:
- On-chain: Event emission + storage references (gas-efficient)
- Off-chain: Full audit logs on IPFS (mutable) or Arweave (permanent)
- Hybrid approach: Best of both worlds (immutability + cost efficiency)
Storage Costs:
- On-chain only: ~640 gas per byte (~$10+ for 1KB at 50 gwei)
- IPFS: ~$5/month per 100GB (mutable, requires pinning)
- Arweave: ~$0.005/MB one-time (permanent, 200+ years)
Integration with BASTION-SC:
This contract works alongside ComplianceGuardrail to provide
comprehensive audit trails for all compliance checks.


## State Variables
### auditLogs
Mapping: logId => AuditLog


```solidity
mapping(bytes32 => AuditLog) public auditLogs
```


### userAuditHistory
Mapping: user => logId[] (user's audit history)


```solidity
mapping(address => bytes32[]) public userAuditHistory
```


### regulationLogs
Mapping: regulation => logId[] (logs per regulation)


```solidity
mapping(string => bytes32[]) public regulationLogs
```


### totalLogs
Total number of audit logs


```solidity
uint256 public totalLogs
```


### totalViolations
Total number of compliance violations


```solidity
uint256 public totalViolations
```


## Functions
### logCompliance

Log compliance check on-chain with off-chain storage reference


```solidity
function logCompliance(
    bytes32 logId,
    address user,
    string memory regulation,
    uint8 article,
    bool passed,
    string memory ipfsCID,
    string memory arweaveTxId,
    bool permanent
) public;
```
**Parameters**

|Name|Type|Description|
|----|----|-----------|
|`logId`|`bytes32`|Unique identifier for the log|
|`user`|`address`|Address of the user|
|`regulation`|`string`|Regulation being checked|
|`article`|`uint8`|Article number|
|`passed`|`bool`|Whether check passed|
|`ipfsCID`|`string`|Content identifier on IPFS|
|`arweaveTxId`|`string`|Transaction ID on Arweave (empty if not permanent)|
|`permanent`|`bool`|Whether stored permanently|


### updateLogReferences

Update IPFS/Arweave references for an audit log

Can only update non-permanent logs (IPFS can be updated, Arweave cannot)


```solidity
function updateLogReferences(bytes32 logId, string memory newIpfsCID, string memory newArweaveTxId) external;
```
**Parameters**

|Name|Type|Description|
|----|----|-----------|
|`logId`|`bytes32`|ID of the log to update|
|`newIpfsCID`|`string`|New IPFS CID|
|`newArweaveTxId`|`string`|New Arweave TX ID (if upgrading to permanent)|


### getAuditLog

Get audit log by ID


```solidity
function getAuditLog(bytes32 logId) external view returns (AuditLog memory);
```
**Parameters**

|Name|Type|Description|
|----|----|-----------|
|`logId`|`bytes32`|ID of the log|

**Returns**

|Name|Type|Description|
|----|----|-----------|
|`<none>`|`AuditLog`|AuditLog struct|


### getUserAuditHistory

Get user's audit history


```solidity
function getUserAuditHistory(address user) external view returns (bytes32[] memory);
```
**Parameters**

|Name|Type|Description|
|----|----|-----------|
|`user`|`address`|Address of the user|

**Returns**

|Name|Type|Description|
|----|----|-----------|
|`<none>`|`bytes32[]`|Array of log IDs|


### getRegulationLogs

Get logs for a specific regulation


```solidity
function getRegulationLogs(string calldata regulation) external view returns (bytes32[] memory);
```
**Parameters**

|Name|Type|Description|
|----|----|-----------|
|`regulation`|`string`|Regulation name (LGPD, GDPR, AI_ACT)|

**Returns**

|Name|Type|Description|
|----|----|-----------|
|`<none>`|`bytes32[]`|Array of log IDs|


### getComplianceStats

Get compliance statistics


```solidity
function getComplianceStats() external view returns (uint256, uint256, uint256);
```
**Returns**

|Name|Type|Description|
|----|----|-----------|
|`<none>`|`uint256`|totalLogs Total number of logs|
|`<none>`|`uint256`|totalViolations Total number of violations|
|`<none>`|`uint256`|complianceRate Compliance rate (passed / total) in basis points|


## Events
### AuditLogCreated

```solidity
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
```

### AuditLogUpdated

```solidity
event AuditLogUpdated(bytes32 indexed logId, string newIpfsCID, string newArweaveTxId, uint256 timestamp);
```

## Errors
### LogAlreadyExists

```solidity
error LogAlreadyExists(bytes32 logId);
```

### LogNotFound

```solidity
error LogNotFound(bytes32 logId);
```

### CannotUpdatePermanentLog

```solidity
error CannotUpdatePermanentLog(bytes32 logId);
```

## Structs
### AuditLog
Audit log reference stored on-chain


```solidity
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
```

**Properties**

|Name|Type|Description|
|----|----|-----------|
|`logId`|`bytes32`|Unique identifier for the log|
|`ipfsCID`|`string`|Content identifier on IPFS|
|`arweaveTxId`|`string`|Transaction ID on Arweave (empty if not permanent)|
|`regulation`|`string`|Regulation being audited (LGPD, GDPR, AI_ACT)|
|`article`|`uint8`|Article number|
|`passed`|`bool`|Whether compliance check passed|
|`timestamp`|`uint256`|Block timestamp|
|`permanent`|`bool`|Whether stored permanently on Arweave|

