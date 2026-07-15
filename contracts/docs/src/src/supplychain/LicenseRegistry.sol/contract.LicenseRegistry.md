# LicenseRegistry
**Inherits:**
ERC721, Ownable

**Title:**
LicenseRegistry

Software License Compliance — NFT-based license tracking + ZK verification

Enhanced IP Guard: ERC-721 license NFTs with SPDX compliance + ZK proofs.
Each license NFT represents a verified software license for a Nix package.
The NFT stores:
- Package hash (Nix derivation) → immutable fingerprint
- SPDX license ID → machine-readable license type
- Validity period → automatic expiration
- Transferability → sublicensing controls
ZK integration:
- validateUsage() accepts Groth16 proofs
- Proves "I have a valid license for this package" without revealing identity
- Used by CI/CD pipelines to prove compliance without exposing org secrets
Supply chain integration:
- SBOMRegistry links packages to SPDX IDs
- BuildAttestation verifies the builder
- LicenseRegistry verifies the license
- SupplyChainGuardian orchestrates all three


## State Variables
### licenses

```solidity
mapping(uint256 => LicenseRecord) public licenses
```


### packageLicenses

```solidity
mapping(bytes32 => uint256[]) public packageLicenses
```


### holderLicenses

```solidity
mapping(address => uint256[]) public holderLicenses
```


### verifiedProofs

```solidity
mapping(bytes32 => bool) public verifiedProofs
```


### totalLicenses

```solidity
uint256 public totalLicenses
```


### guardianContract

```solidity
address public guardianContract
```


## Functions
### onlyGuardian


```solidity
modifier onlyGuardian() ;
```

### licenseValid


```solidity
modifier licenseValid(uint256 tokenId) ;
```

### constructor


```solidity
constructor(address _guardian) ERC721("Software License NFT", "SLNFT") Ownable(msg.sender);
```

### mintLicense

Mint a new license NFT for a Nix package

Only callable by SupplyChainGuardian after SBOM + Build attestation


```solidity
function mintLicense(
    address to,
    bytes32 packageHash,
    string calldata spdxId,
    string calldata packageName,
    string calldata packageVersion,
    uint256 validUntil,
    bool transferable
) external onlyGuardian returns (uint256);
```

### revokeLicense

Revoke a license (e.g., license violation found)


```solidity
function revokeLicense(uint256 tokenId, string calldata reason) external onlyGuardian;
```

### validateUsage

Verify license compliance using ZK proof

Proves "I have a valid license for packageHash" without revealing identity


```solidity
function validateUsage(bytes calldata zkProof, bytes32 packageHash, uint256 tokenId, bytes32 proofHash)
    external
    returns (bool);
```
**Parameters**

|Name|Type|Description|
|----|----|-----------|
|`zkProof`|`bytes`|Groth16 proof bytes|
|`packageHash`|`bytes32`|Nix derivation hash being verified|
|`tokenId`|`uint256`|License NFT token ID|
|`proofHash`|`bytes32`|keccak256(zkProof) for deduplication|


### getLicense


```solidity
function getLicense(uint256 tokenId) external view returns (LicenseRecord memory);
```

### getPackageLicenses


```solidity
function getPackageLicenses(bytes32 packageHash) external view returns (uint256[] memory);
```

### getHolderLicenses


```solidity
function getHolderLicenses(address holder) external view returns (uint256[] memory);
```

### isLicenseValid


```solidity
function isLicenseValid(uint256 tokenId) external view returns (bool);
```

### getTotalLicenses


```solidity
function getTotalLicenses() external view returns (uint256);
```

### _update

Only allow transfers if license is transferable (sublicensing)


```solidity
function _update(address to, uint256 tokenId, address auth) internal override returns (address);
```

## Events
### LicenseMinted

```solidity
event LicenseMinted(
    uint256 indexed tokenId, bytes32 indexed packageHash, address indexed holder, string spdxId, uint256 validUntil
);
```

### LicenseRevoked

```solidity
event LicenseRevoked(uint256 indexed tokenId, string reason);
```

### LicenseTransferred

```solidity
event LicenseTransferred(uint256 indexed tokenId, address from, address to);
```

### ComplianceVerified

```solidity
event ComplianceVerified(bytes32 indexed packageHash, address indexed user, uint256 tokenId, bytes32 proofHash);
```

## Errors
### LicenseExpired

```solidity
error LicenseExpired(uint256 tokenId, uint256 validUntil);
```

### LicenseAlreadyRevoked

```solidity
error LicenseAlreadyRevoked(uint256 tokenId);
```

### PackageMismatch

```solidity
error PackageMismatch(bytes32 expected, bytes32 actual);
```

### InvalidZKProof

```solidity
error InvalidZKProof(bytes32 proofHash);
```

### NotGuardian

```solidity
error NotGuardian(address caller);
```

## Structs
### LicenseRecord

```solidity
struct LicenseRecord {
    bytes32 packageHash; // Nix derivation hash
    string spdxId; // SPDX license identifier (e.g., "MIT", "Apache-2.0")
    string packageName; // Human-readable package name
    string packageVersion; // Version string
    uint256 validFrom; // License start timestamp
    uint256 validUntil; // License expiration (0 = perpetual)
    bool transferable; // Can be sublicensed?
    bool revoked; // Has this license been revoked?
    uint256 mintedAt; // Block timestamp of minting
}
```

