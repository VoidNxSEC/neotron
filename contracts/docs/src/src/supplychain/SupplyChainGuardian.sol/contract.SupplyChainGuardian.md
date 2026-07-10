# SupplyChainGuardian
**Inherits:**
[ComplianceGuardrail](/src/ComplianceGuardrail.sol/abstract.ComplianceGuardrail.md)

**Title:**
SupplyChainGuardian

End-to-End Software Supply Chain Security — Orchestrator Contract

Unifies Neotron's compliance framework with IP Guard's license verification.
Complete attestation pipeline for every Nix package:
1. SBOMRegistry     — attests the Software Bill of Materials
2. BuildAttestation  — attests SLSA build provenance (Level 0-3)
3. LicenseRegistry   — mints a license NFT (ERC-721) with SPDX + ZK
4. ComplianceGuardrail — enforces LGPD/GDPR/AI Act modifiers
5. AuditLogger       — stores on-chain audit trail with IPFS/Arweave
Single entry point: attestPackage()
→ SBOM attested
→ Build provenance recorded
→ License NFT minted
→ Compliance logged
→ Audit trail stored
Covers:
✅ Legal certificates (SPDX license compliance)
✅ Supply chain security (SLSA build provenance)
✅ Vulnerability tracking (CVE reports)
✅ Compliance enforcement (LGPD/GDPR/AI Act)
✅ Immutable audit trail (IPFS/Arweave)


## State Variables
### sbomRegistry

```solidity
SBOMRegistry public sbomRegistry
```


### buildAttestation

```solidity
BuildAttestation public buildAttestation
```


### licenseRegistry

```solidity
LicenseRegistry public licenseRegistry
```


### auditLogger

```solidity
AuditLogger public auditLogger
```


### attestations

```solidity
mapping(bytes32 => PackageAttestation) public attestations
```


### builderAttestations

```solidity
mapping(address => bytes32[]) public builderAttestations
```


### allAttestations

```solidity
bytes32[] public allAttestations
```


### totalAttestations

```solidity
uint256 public totalAttestations
```


## Functions
### constructor


```solidity
constructor() ;
```

### attestPackage

Complete attestation of a Nix package — SBOM + Build + License + Audit

Single transaction that covers the full supply chain attestation


```solidity
function attestPackage(
    bytes32 packageHash,
    string calldata packageName,
    string calldata packageVersion,
    string calldata spdxId,
    bytes32 sbomContentHash,
    string calldata sbomIpfsCid,
    BuildAttestation.SLSALevel slsaLevel,
    bytes32 sourceCommit,
    string calldata sourceRepo,
    bytes32 flakeInputHash,
    string calldata buildIpfsCid,
    uint256 validUntil,
    bool transferable,
    string calldata regulation,
    uint8 article,
    string calldata auditIpfsCid
) external returns (bytes32);
```
**Parameters**

|Name|Type|Description|
|----|----|-----------|
|`packageHash`|`bytes32`|Nix derivation hash|
|`packageName`|`string`|Human-readable package name|
|`packageVersion`|`string`|Version string|
|`spdxId`|`string`|SPDX license identifier|
|`sbomContentHash`|`bytes32`|sha256 of the full SBOM document|
|`sbomIpfsCid`|`string`|IPFS CID of SBOM document|
|`slsaLevel`|`BuildAttestation.SLSALevel`|SLSA provenance level|
|`sourceCommit`|`bytes32`|Git commit hash|
|`sourceRepo`|`string`|Git repository URL|
|`flakeInputHash`|`bytes32`|Hash of flake.lock|
|`buildIpfsCid`|`string`|IPFS CID of build attestation|
|`validUntil`|`uint256`|License validity period (0 = perpetual)|
|`transferable`|`bool`|Can license be sublicensed?|
|`regulation`|`string`|Compliance regulation (e.g., "LGPD", "GDPR")|
|`article`|`uint8`|Compliance article number|
|`auditIpfsCid`|`string`|IPFS CID for audit log|


### reportVulnerability

Report a CVE against an attested package


```solidity
function reportVulnerability(
    bytes32 packageHash,
    string calldata cveId,
    uint8 severity,
    string calldata affectedPackage,
    string calldata fixedVersion
) external;
```

### getAttestation


```solidity
function getAttestation(bytes32 packageHash) external view returns (PackageAttestation memory);
```

### getBuilderAttestations


```solidity
function getBuilderAttestations(address builder) external view returns (bytes32[] memory);
```

### getTotalAttestations


```solidity
function getTotalAttestations() external view returns (uint256);
```

### verifySupplyChain

Verify a package's full supply chain status


```solidity
function verifySupplyChain(bytes32 packageHash) external view returns (bool, bool, bool, bool);
```
**Returns**

|Name|Type|Description|
|----|----|-----------|
|`<none>`|`bool`|sbomExists, buildVerified, licenseValid, auditLogged|
|`<none>`|`bool`||
|`<none>`|`bool`||
|`<none>`|`bool`||


### hasConsent


```solidity
function hasConsent(address) internal view override returns (bool);
```

### hasDataAccess


```solidity
function hasDataAccess(address, address) internal view override returns (bool);
```

### withinRetentionPeriod


```solidity
function withinRetentionPeriod(address) internal view override returns (bool);
```

### hasHumanReview


```solidity
function hasHumanReview(bytes32) internal view override returns (bool);
```

### hasTransparencyInfo


```solidity
function hasTransparencyInfo(bytes32) internal view override returns (bool);
```

### hasHumanOversight


```solidity
function hasHumanOversight(bytes32) internal view override returns (bool);
```

## Events
### PackageAttested

```solidity
event PackageAttested(
    bytes32 indexed packageHash,
    bytes32 sbomId,
    bytes32 buildId,
    uint256 licenseTokenId,
    bytes32 auditLogId,
    address indexed attestedBy
);
```

### FullAttestationComplete

```solidity
event FullAttestationComplete(
    bytes32 indexed packageHash, string packageName, string spdxId, BuildAttestation.SLSALevel slsaLevel
);
```

## Errors
### NotRegisteredBuilder

```solidity
error NotRegisteredBuilder(address caller);
```

### AttestationAlreadyComplete

```solidity
error AttestationAlreadyComplete(bytes32 packageHash);
```

### AttestationNotFound

```solidity
error AttestationNotFound(bytes32 packageHash);
```

## Structs
### PackageAttestation

```solidity
struct PackageAttestation {
    bytes32 packageHash; // Nix derivation hash
    bytes32 sbomId; // SBOM entry ID
    bytes32 buildId; // Build provenance ID
    uint256 licenseTokenId; // License NFT token ID
    bytes32 auditLogId; // Audit log entry ID
    address attestedBy; // Who submitted the attestation
    uint256 timestamp; // Block timestamp
    bool complete; // All 4 steps completed?
}
```

### AttestPackageParams

```solidity
struct AttestPackageParams {
    bytes32 packageHash;
    string packageName;
    string packageVersion;
    string spdxId;
    bytes32 sbomContentHash;
    string sbomIpfsCid;
    BuildAttestation.SLSALevel slsaLevel;
    bytes32 sourceCommit;
    string sourceRepo;
    bytes32 flakeInputHash;
    string buildIpfsCid;
    uint256 validUntil;
    bool transferable;
    string regulation;
    uint8 article;
    string auditIpfsCid;
}
```

