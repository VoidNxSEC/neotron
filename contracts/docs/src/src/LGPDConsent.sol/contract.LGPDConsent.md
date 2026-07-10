# LGPDConsent
**Inherits:**
[ComplianceGuardrail](/src/ComplianceGuardrail.sol/abstract.ComplianceGuardrail.md)

**Title:**
LGPDConsent

**Author:**
NEXUS Platform

Implements LGPD consent management on-chain

Handles consent granting, revocation, and verification for LGPD compliance
LGPD Articles Implemented:
- Article 7: Consent required for data processing
- Article 16: Right to data portability and access control
- Article 46: Data retention limits
Integration with BASTION Kernel Layer:
This smart contract provides on-chain consent management that mirrors
the kernel-level enforcement in neutron/compliance/auditors/lgpd_kernel.py


## State Variables
### consents
Mapping: dataSubject => processor => ConsentRecord


```solidity
mapping(address => mapping(address => ConsentRecord)) public consents
```


### accessAuthorizations
Mapping: dataSubject => accessor => AccessRecord


```solidity
mapping(address => mapping(address => AccessRecord)) public accessAuthorizations
```


### retentionPolicies
Mapping: dataSubject => RetentionPolicy


```solidity
mapping(address => RetentionPolicy) public retentionPolicies
```


### DEFAULT_RETENTION_PERIOD
Default retention period (365 days)


```solidity
uint256 public constant DEFAULT_RETENTION_PERIOD = 365 days
```


### MAX_RETENTION_PERIOD
Maximum retention period (10 years)


```solidity
uint256 public constant MAX_RETENTION_PERIOD = 10 * 365 days
```


## Functions
### grantConsent

Grant consent for data processing


```solidity
function grantConsent(address processor, uint256 duration, string calldata purpose) external;
```
**Parameters**

|Name|Type|Description|
|----|----|-----------|
|`processor`|`address`|Address of the entity that will process data|
|`duration`|`uint256`|Duration of consent in seconds|
|`purpose`|`string`|Description of the processing purpose|


### revokeConsent

Revoke consent for data processing


```solidity
function revokeConsent(address processor) external;
```
**Parameters**

|Name|Type|Description|
|----|----|-----------|
|`processor`|`address`|Address of the processor whose consent to revoke|


### checkConsent

Check if valid consent exists


```solidity
function checkConsent(address dataSubject, address processor) external view returns (bool);
```
**Parameters**

|Name|Type|Description|
|----|----|-----------|
|`dataSubject`|`address`|Address of the data subject|
|`processor`|`address`|Address of the processor|

**Returns**

|Name|Type|Description|
|----|----|-----------|
|`<none>`|`bool`|bool True if valid consent exists|


### hasConsent

Internal function to check consent (used by modifiers)


```solidity
function hasConsent(address dataSubject) internal view override returns (bool);
```
**Parameters**

|Name|Type|Description|
|----|----|-----------|
|`dataSubject`|`address`|Address of the data subject|

**Returns**

|Name|Type|Description|
|----|----|-----------|
|`<none>`|`bool`|bool True if consent is valid|


### hasConsent

Internal helper to check consent for a specific processor


```solidity
function hasConsent(address dataSubject, address processor) internal view returns (bool);
```
**Parameters**

|Name|Type|Description|
|----|----|-----------|
|`dataSubject`|`address`|Address of the data subject|
|`processor`|`address`|Address of the processor|

**Returns**

|Name|Type|Description|
|----|----|-----------|
|`<none>`|`bool`|bool True if consent is valid|


### grantDataAccess

Grant data access to another address


```solidity
function grantDataAccess(address accessor, uint256 duration, string calldata scope) external;
```
**Parameters**

|Name|Type|Description|
|----|----|-----------|
|`accessor`|`address`|Address to grant access to|
|`duration`|`uint256`|Duration of access in seconds|
|`scope`|`string`|Description of access scope|


### revokeDataAccess

Revoke data access from an address


```solidity
function revokeDataAccess(address accessor) external;
```
**Parameters**

|Name|Type|Description|
|----|----|-----------|
|`accessor`|`address`|Address to revoke access from|


### hasDataAccess

Check if data access is authorized


```solidity
function hasDataAccess(address dataSubject, address accessor) internal view override returns (bool);
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


### setRetentionPolicy

Set data retention policy for caller's data


```solidity
function setRetentionPolicy(uint256 retentionPeriod, string calldata purpose) external;
```
**Parameters**

|Name|Type|Description|
|----|----|-----------|
|`retentionPeriod`|`uint256`|Duration in seconds to retain data|
|`purpose`|`string`|Purpose for data retention|


### withinRetentionPeriod

Check if data is within retention period


```solidity
function withinRetentionPeriod(address dataSubject) internal view override returns (bool);
```
**Parameters**

|Name|Type|Description|
|----|----|-----------|
|`dataSubject`|`address`|Address of the data subject|

**Returns**

|Name|Type|Description|
|----|----|-----------|
|`<none>`|`bool`|bool True if within retention period|


### isRetentionExpired

Check if retention period has expired for data subject


```solidity
function isRetentionExpired(address dataSubject) external view returns (bool);
```
**Parameters**

|Name|Type|Description|
|----|----|-----------|
|`dataSubject`|`address`|Address of the data subject|

**Returns**

|Name|Type|Description|
|----|----|-----------|
|`<none>`|`bool`|bool True if retention period has expired|


### hasHumanReview

Not implemented in this contract (for GDPR)


```solidity
function hasHumanReview(bytes32) internal pure override returns (bool);
```

### hasTransparencyInfo

Not implemented in this contract (for AI Act)


```solidity
function hasTransparencyInfo(bytes32) internal pure override returns (bool);
```

### hasHumanOversight

Not implemented in this contract (for AI Act)


```solidity
function hasHumanOversight(bytes32) internal pure override returns (bool);
```

## Events
### ConsentGranted

```solidity
event ConsentGranted(
    address indexed dataSubject, address indexed processor, string purpose, uint256 expiresAt, uint256 timestamp
);
```

### ConsentRevoked

```solidity
event ConsentRevoked(address indexed dataSubject, address indexed processor, uint256 timestamp);
```

### ConsentExpired

```solidity
event ConsentExpired(address indexed dataSubject, address indexed processor, uint256 timestamp);
```

### AccessGranted

```solidity
event AccessGranted(
    address indexed dataSubject, address indexed accessor, string scope, uint256 expiresAt, uint256 timestamp
);
```

### AccessRevoked

```solidity
event AccessRevoked(address indexed dataSubject, address indexed accessor, uint256 timestamp);
```

### RetentionPolicySet

```solidity
event RetentionPolicySet(address indexed dataSubject, uint256 retentionPeriod, string purpose, uint256 timestamp);
```

## Errors
### ConsentAlreadyGranted

```solidity
error ConsentAlreadyGranted(address dataSubject, address processor);
```

### ConsentNotFound

```solidity
error ConsentNotFound(address dataSubject, address processor);
```

### ConsentAlreadyRevoked

```solidity
error ConsentAlreadyRevoked(address dataSubject, address processor);
```

### InvalidDuration

```solidity
error InvalidDuration(uint256 duration);
```

### InvalidRetentionPeriod

```solidity
error InvalidRetentionPeriod(uint256 period);
```

## Structs
### ConsentRecord
Consent record structure


```solidity
struct ConsentRecord {
    bool granted;
    uint256 grantedAt;
    uint256 expiresAt;
    string purpose;
    bool revoked;
    uint256 revokedAt;
}
```

**Properties**

|Name|Type|Description|
|----|----|-----------|
|`granted`|`bool`|Whether consent has been granted|
|`grantedAt`|`uint256`|Timestamp when consent was granted|
|`expiresAt`|`uint256`|Timestamp when consent expires|
|`purpose`|`string`|Description of data processing purpose|
|`revoked`|`bool`|Whether consent has been revoked|
|`revokedAt`|`uint256`|Timestamp when consent was revoked|

### AccessRecord
Data access authorization record


```solidity
struct AccessRecord {
    bool authorized;
    uint256 grantedAt;
    uint256 expiresAt;
    string scope;
}
```

**Properties**

|Name|Type|Description|
|----|----|-----------|
|`authorized`|`bool`|Whether access is authorized|
|`grantedAt`|`uint256`|Timestamp when access was granted|
|`expiresAt`|`uint256`|Timestamp when access expires|
|`scope`|`string`|Description of access scope|

### RetentionPolicy
Data retention policy


```solidity
struct RetentionPolicy {
    uint256 retentionPeriod;
    uint256 dataCreatedAt;
    string purpose;
}
```

**Properties**

|Name|Type|Description|
|----|----|-----------|
|`retentionPeriod`|`uint256`|Duration in seconds for data retention|
|`dataCreatedAt`|`uint256`|Timestamp when data was created|
|`purpose`|`string`|Purpose for data retention|

