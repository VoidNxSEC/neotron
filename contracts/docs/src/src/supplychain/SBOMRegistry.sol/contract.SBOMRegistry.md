# SBOMRegistry
**Title:**
SBOMRegistry

Software Bill of Materials — on-chain attestation registry

Stores SBOM hashes with CycloneDX/SPDX metadata, signed by build systems.
What goes on-chain:
- Package hash (Nix derivation hash)
- SBOM format (CycloneDX 1.5 / SPDX 2.3)
- SBOM content hash (sha256 of the SBOM document)
- Builder identity (who generated this attestation)
- Timestamp
What stays off-chain (IPFS/Arweave):
- Full SBOM document (JSON/XML)
- Vulnerability scan results
- License compliance report
Integration:
- SupplyChainGuardian calls this for every Nix build
- BuildAttestation links to SBOM entries
- LicenseRegistry verifies SPDX compliance


## State Variables
### sbomEntries

```solidity
mapping(bytes32 => SBOMEntry) public sbomEntries
```


### packageSBOMs

```solidity
mapping(bytes32 => bytes32[]) public packageSBOMs
```


### builderSBOMs

```solidity
mapping(address => bytes32[]) public builderSBOMs
```


### vulnerabilities

```solidity
mapping(bytes32 => VulnerabilityReport[]) public vulnerabilities
```


### allSBOMs

```solidity
bytes32[] public allSBOMs
```


### totalSBOMs

```solidity
uint256 public totalSBOMs
```


## Functions
### attestSBOM

Attest a new SBOM for a Nix package


```solidity
function attestSBOM(
    bytes32 sbomId,
    bytes32 packageHash,
    bytes32 sbomContentHash,
    SBOMFormat format,
    string calldata ipfsCid,
    string calldata arweaveTxId
) external returns (bytes32);
```
**Parameters**

|Name|Type|Description|
|----|----|-----------|
|`sbomId`|`bytes32`|Unique ID (keccak256(packageHash + sbomContentHash))|
|`packageHash`|`bytes32`|Nix derivation hash|
|`sbomContentHash`|`bytes32`|sha256 of the full SBOM document|
|`format`|`SBOMFormat`|SBOM standard format|
|`ipfsCid`|`string`|IPFS CID of the full SBOM document|
|`arweaveTxId`|`string`|Arweave TX ID (empty if not permanent)|


### revokeSBOM

Revoke an SBOM entry (e.g., security issue found)


```solidity
function revokeSBOM(bytes32 sbomId, string calldata reason) external;
```

### reportVulnerability

Report a vulnerability against an SBOM entry


```solidity
function reportVulnerability(
    bytes32 sbomId,
    string calldata cveId,
    uint8 severity,
    string calldata affectedPackage,
    string calldata fixedVersion
) external;
```

### getSBOM


```solidity
function getSBOM(bytes32 sbomId) external view returns (SBOMEntry memory);
```

### getPackageSBOMs


```solidity
function getPackageSBOMs(bytes32 packageHash) external view returns (bytes32[] memory);
```

### getBuilderSBOMs


```solidity
function getBuilderSBOMs(address builder) external view returns (bytes32[] memory);
```

### getVulnerabilities


```solidity
function getVulnerabilities(bytes32 sbomId) external view returns (VulnerabilityReport[] memory);
```

### getTotalSBOMs


```solidity
function getTotalSBOMs() external view returns (uint256);
```

## Events
### SBOMAttested

```solidity
event SBOMAttested(
    bytes32 indexed sbomId,
    bytes32 indexed packageHash,
    address indexed builder,
    SBOMFormat format,
    string ipfsCid,
    uint256 timestamp
);
```

### VulnerabilityReported

```solidity
event VulnerabilityReported(bytes32 indexed sbomId, string cveId, uint8 severity, string affectedPackage);
```

### SBOMRevoked

```solidity
event SBOMRevoked(bytes32 indexed sbomId, string reason);
```

## Errors
### SBOMAlreadyExists

```solidity
error SBOMAlreadyExists(bytes32 sbomId);
```

### SBOMNotFound

```solidity
error SBOMNotFound(bytes32 sbomId);
```

### AlreadyRevoked

```solidity
error AlreadyRevoked(bytes32 sbomId);
```

## Structs
### SBOMEntry

```solidity
struct SBOMEntry {
    bytes32 packageHash; // Nix derivation hash
    bytes32 sbomContentHash; // sha256 of full SBOM document
    SBOMFormat format; // SBOM standard used
    address builder; // Who generated this attestation
    string ipfsCid; // IPFS CID of full SBOM document
    string arweaveTxId; // Arweave TX (permanent storage)
    uint256 timestamp; // Block timestamp
    bool revoked; // Allow revocation for security updates
}
```

### VulnerabilityReport

```solidity
struct VulnerabilityReport {
    bytes32 sbomId; // Links to SBOM entry
    string cveId; // CVE-2024-XXXX
    uint8 severity; // 0-10 (CVSS)
    string affectedPackage; // Package name
    string fixedVersion; // Version with fix
    uint256 reportedAt;
    bool resolved;
}
```

## Enums
### SBOMFormat

```solidity
enum SBOMFormat {
    CycloneDX_1_5,
    SPDX_2_3,
    CycloneDX_1_4,
    SPDX_2_2
}
```

