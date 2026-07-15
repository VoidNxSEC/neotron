# ComplianceGuardrail
**Title:**
ComplianceGuardrail

**Author:**
NEXUS Platform

Base contract for BASTION-SC compliance enforcement

Abstract contract providing compliance modifiers and event logging
BASTION-SC Philosophy:
Just as BASTION makes compliance violations impossible at the Linux kernel level (syscalls),
BASTION-SC makes them impossible at the smart contract level (function execution).
Defense-in-Depth Compliance:
- Layer 1: SENTINEL (Application - Python validation)
- Layer 2: BASTION (Kernel - seccomp-BPF syscall filtering)
- Layer 3: BASTION-SC (Smart Contract - on-chain enforcement) ← This layer
- Layer 4: Audit Trail (PostgreSQL + IPFS/Arweave)


## Functions
### lgpdArticle7Consent

LGPD Article 7 - Consent requirement for data processing

Reverts if the data subject has not granted consent


```solidity
modifier lgpdArticle7Consent(address dataSubject) ;
```
**Parameters**

|Name|Type|Description|
|----|----|-----------|
|`dataSubject`|`address`|Address of the person whose data is being processed|


### lgpdArticle16Access

LGPD Article 16 - Right to data portability and access

Reverts if the requester is not authorized to access data


```solidity
modifier lgpdArticle16Access(address dataSubject) ;
```
**Parameters**

|Name|Type|Description|
|----|----|-----------|
|`dataSubject`|`address`|Address of the person whose data is being accessed|


### lgpdArticle46Retention

LGPD Article 46 - Data retention limits

Reverts if data retention period has expired


```solidity
modifier lgpdArticle46Retention(address dataSubject) ;
```
**Parameters**

|Name|Type|Description|
|----|----|-----------|
|`dataSubject`|`address`|Address of the person whose data is subject to retention|


### gdprArticle22HumanOversight

GDPR Article 22 - Automated decision-making with human oversight

Reverts if human review is not present for automated decisions


```solidity
modifier gdprArticle22HumanOversight(bytes32 decisionId) ;
```
**Parameters**

|Name|Type|Description|
|----|----|-----------|
|`decisionId`|`bytes32`|Unique identifier for the decision being made|


### aiActArticle13Transparency

AI Act Article 13 - Transparency requirements

Reverts if AI output lacks required transparency information


```solidity
modifier aiActArticle13Transparency(bytes32 outputId) ;
```
**Parameters**

|Name|Type|Description|
|----|----|-----------|
|`outputId`|`bytes32`|Unique identifier for the AI output|


### aiActArticle14Oversight

AI Act Article 14 - Human oversight for high-risk AI

Reverts if high-risk AI decision lacks human oversight


```solidity
modifier aiActArticle14Oversight(bytes32 decisionId) ;
```
**Parameters**

|Name|Type|Description|
|----|----|-----------|
|`decisionId`|`bytes32`|Unique identifier for the AI decision|


### hasConsent

Check if a data subject has granted consent for data processing


```solidity
function hasConsent(address dataSubject) internal view virtual returns (bool);
```
**Parameters**

|Name|Type|Description|
|----|----|-----------|
|`dataSubject`|`address`|Address of the data subject|

**Returns**

|Name|Type|Description|
|----|----|-----------|
|`<none>`|`bool`|bool True if consent is granted and valid|


### hasDataAccess

Check if an address is authorized to access another's data


```solidity
function hasDataAccess(address dataSubject, address accessor) internal view virtual returns (bool);
```
**Parameters**

|Name|Type|Description|
|----|----|-----------|
|`dataSubject`|`address`|Address of the data subject|
|`accessor`|`address`|Address requesting access|

**Returns**

|Name|Type|Description|
|----|----|-----------|
|`<none>`|`bool`|bool True if access is authorized|


### withinRetentionPeriod

Check if data is within its retention period


```solidity
function withinRetentionPeriod(address dataSubject) internal view virtual returns (bool);
```
**Parameters**

|Name|Type|Description|
|----|----|-----------|
|`dataSubject`|`address`|Address of the data subject|

**Returns**

|Name|Type|Description|
|----|----|-----------|
|`<none>`|`bool`|bool True if within retention period|


### hasHumanReview

Check if a decision has undergone human review


```solidity
function hasHumanReview(bytes32 decisionId) internal view virtual returns (bool);
```
**Parameters**

|Name|Type|Description|
|----|----|-----------|
|`decisionId`|`bytes32`|Unique identifier for the decision|

**Returns**

|Name|Type|Description|
|----|----|-----------|
|`<none>`|`bool`|bool True if human review is present|


### hasTransparencyInfo

Check if AI output has transparency information


```solidity
function hasTransparencyInfo(bytes32 outputId) internal view virtual returns (bool);
```
**Parameters**

|Name|Type|Description|
|----|----|-----------|
|`outputId`|`bytes32`|Unique identifier for the AI output|

**Returns**

|Name|Type|Description|
|----|----|-----------|
|`<none>`|`bool`|bool True if transparency info is present|


### hasHumanOversight

Check if a decision has human oversight


```solidity
function hasHumanOversight(bytes32 decisionId) internal view virtual returns (bool);
```
**Parameters**

|Name|Type|Description|
|----|----|-----------|
|`decisionId`|`bytes32`|Unique identifier for the decision|

**Returns**

|Name|Type|Description|
|----|----|-----------|
|`<none>`|`bool`|bool True if human oversight is present|


### storeAuditLog

Store audit log off-chain (IPFS/Arweave)


```solidity
function storeAuditLog(bytes32 logId, string memory ipfsCID, string memory arweaveTxId, string memory regulation)
    internal;
```
**Parameters**

|Name|Type|Description|
|----|----|-----------|
|`logId`|`bytes32`|Unique identifier for the audit log|
|`ipfsCID`|`string`|Content identifier on IPFS|
|`arweaveTxId`|`string`|Transaction ID on Arweave (empty if not permanent)|
|`regulation`|`string`|The regulation being audited|


## Events
### ComplianceViolation
Emitted when a compliance check fails


```solidity
event ComplianceViolation(
    address indexed user, string regulation, uint8 article, string violation, uint256 timestamp
);
```

**Parameters**

|Name|Type|Description|
|----|----|-----------|
|`user`|`address`|Address of the user who triggered the violation|
|`regulation`|`string`|The regulation that was violated (e.g., "LGPD", "GDPR")|
|`article`|`uint8`|The specific article violated (e.g., 7, 15, 22)|
|`violation`|`string`|Description of the violation|
|`timestamp`|`uint256`|Block timestamp of the violation|

### CompliancePass
Emitted when a compliance check passes


```solidity
event CompliancePass(address indexed user, string regulation, uint8 article, uint256 timestamp);
```

**Parameters**

|Name|Type|Description|
|----|----|-----------|
|`user`|`address`|Address of the user who passed the check|
|`regulation`|`string`|The regulation that was checked|
|`article`|`uint8`|The specific article checked|
|`timestamp`|`uint256`|Block timestamp of the check|

### AuditLogStored
Emitted when an audit log is stored off-chain


```solidity
event AuditLogStored(
    bytes32 indexed logId, string ipfsCID, string arweaveTxId, string regulation, uint256 timestamp
);
```

**Parameters**

|Name|Type|Description|
|----|----|-----------|
|`logId`|`bytes32`|Unique identifier for the audit log|
|`ipfsCID`|`string`|Content identifier on IPFS|
|`arweaveTxId`|`string`|Transaction ID on Arweave (if permanent storage)|
|`regulation`|`string`|The regulation being audited|
|`timestamp`|`uint256`|Block timestamp|

## Errors
### LGPD_Article7_ConsentRequired
Thrown when LGPD Article 7 is violated (no consent)


```solidity
error LGPD_Article7_ConsentRequired(address dataSubject);
```

### LGPD_Article16_UnauthorizedAccess
Thrown when LGPD Article 16 is violated (unauthorized data access)


```solidity
error LGPD_Article16_UnauthorizedAccess(address dataSubject);
```

### LGPD_Article46_RetentionViolation
Thrown when LGPD Article 46 is violated (retention policy)


```solidity
error LGPD_Article46_RetentionViolation(address dataSubject);
```

### GDPR_Article15_AccessDenied
Thrown when GDPR Article 15 is violated (right to access)


```solidity
error GDPR_Article15_AccessDenied(address dataSubject);
```

### GDPR_Article17_ErasureRequired
Thrown when GDPR Article 17 is violated (right to erasure)


```solidity
error GDPR_Article17_ErasureRequired(address dataSubject);
```

### GDPR_Article22_HumanOversightRequired
Thrown when GDPR Article 22 is violated (automated decision-making)


```solidity
error GDPR_Article22_HumanOversightRequired(bytes32 decisionId);
```

### AIAct_Article5_ProhibitedPractice
Thrown when AI Act Article 5 is violated (prohibited practices)


```solidity
error AIAct_Article5_ProhibitedPractice(string practice);
```

### AIAct_Article13_TransparencyRequired
Thrown when AI Act Article 13 is violated (transparency)


```solidity
error AIAct_Article13_TransparencyRequired(bytes32 outputId);
```

### AIAct_Article14_OversightRequired
Thrown when AI Act Article 14 is violated (human oversight)


```solidity
error AIAct_Article14_OversightRequired(bytes32 decisionId);
```

