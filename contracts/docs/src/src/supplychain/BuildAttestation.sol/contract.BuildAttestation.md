# BuildAttestation
**Title:**
BuildAttestation

SLSA Build Provenance — on-chain attestation of build integrity

Implements SLSA v1.0 provenance model for Nix-based builds.
SLSA Levels tracked:
Level 0: No attestation
Level 1: Build is scripted (provenance exists)
Level 2: Build service generates provenance (parameterized, no user access)
Level 3: Build is hermetic + isolated (Nix provides this natively)
Nix provides SLSA Level 3 by default:
- Hermetic: fixed-input derivations
- Isolated: sandbox builds
- Reproducible: bit-for-bit identical outputs
Attestation payload (off-chain, IPFS):
- Builder ID (Nix daemon / GitHub Actions runner)
- Build invocation (command line, parameters)
- Source provenance (git commit, repo URL)
- Build dependencies (Nix flake inputs, pinned hashes)
- Output artifacts (derivation paths, hashes)


## State Variables
### provenances

```solidity
mapping(bytes32 => BuildProvenance) public provenances
```


### packageBuilds

```solidity
mapping(bytes32 => bytes32[]) public packageBuilds
```


### builders

```solidity
mapping(address => Builder) public builders
```


### builderBuilds

```solidity
mapping(address => bytes32[]) public builderBuilds
```


### allBuilds

```solidity
bytes32[] public allBuilds
```


### totalBuilds

```solidity
uint256 public totalBuilds
```


## Functions
### registerBuilder

Register a builder identity (Nix daemon, CI runner, etc.)


```solidity
function registerBuilder(string calldata name, string calldata publicKey) external;
```

### attestBuild

Attest a build with SLSA provenance


```solidity
function attestBuild(
    bytes32 buildId,
    bytes32 packageHash,
    SLSALevel slsaLevel,
    bytes32 sourceCommit,
    string calldata sourceRepo,
    bytes32 flakeInputHash,
    string calldata ipfsCid
) external returns (bytes32);
```
**Parameters**

|Name|Type|Description|
|----|----|-----------|
|`buildId`|`bytes32`|keccak256(msg.sender + packageHash + block.timestamp)|
|`packageHash`|`bytes32`|Nix derivation hash|
|`slsaLevel`|`SLSALevel`|SLSA level (0-3)|
|`sourceCommit`|`bytes32`|Git commit hash|
|`sourceRepo`|`string`|Git repository URL|
|`flakeInputHash`|`bytes32`|Hash of flake.lock|
|`ipfsCid`|`string`|IPFS CID of full attestation|


### verifyBuild

Verify a build attestation (called by SupplyChainGuardian)


```solidity
function verifyBuild(bytes32 buildId) external returns (bool);
```

### getBuild


```solidity
function getBuild(bytes32 buildId) external view returns (BuildProvenance memory);
```

### getPackageBuilds


```solidity
function getPackageBuilds(bytes32 packageHash) external view returns (bytes32[] memory);
```

### getBuilderBuilds


```solidity
function getBuilderBuilds(address builder) external view returns (bytes32[] memory);
```

### getBuilder


```solidity
function getBuilder(address builder) external view returns (Builder memory);
```

### getTotalBuilds


```solidity
function getTotalBuilds() external view returns (uint256);
```

## Events
### BuildAttested

```solidity
event BuildAttested(
    bytes32 indexed buildId,
    bytes32 indexed packageHash,
    address indexed builder,
    SLSALevel slsaLevel,
    bytes32 sourceCommit,
    string ipfsCid
);
```

### BuilderRegistered

```solidity
event BuilderRegistered(address indexed builder, string name, string publicKey);
```

### BuildVerified

```solidity
event BuildVerified(bytes32 indexed buildId, address indexed verifier);
```

## Errors
### BuildAlreadyExists

```solidity
error BuildAlreadyExists(bytes32 buildId);
```

### BuildNotFound

```solidity
error BuildNotFound(bytes32 buildId);
```

### BuilderNotRegistered

```solidity
error BuilderNotRegistered(address builder);
```

### BuilderAlreadyRegistered

```solidity
error BuilderAlreadyRegistered(address builder);
```

## Structs
### BuildProvenance

```solidity
struct BuildProvenance {
    bytes32 buildId; // keccak256(builder + packageHash + timestamp)
    bytes32 packageHash; // Nix derivation hash
    address builder; // Builder identity (Nix daemon key / CI runner)
    SLSALevel slsaLevel; // SLSA provenance level
    bytes32 sourceCommit; // Git commit hash
    string sourceRepo; // Git repository URL
    bytes32 flakeInputHash; // Hash of flake.lock (all inputs pinned)
    string ipfsCid; // IPFS CID of full attestation document
    uint256 timestamp;
    bool verified; // Has this attestation been verified?
}
```

### Builder

```solidity
struct Builder {
    address builderAddress;
    string name; // e.g., "GitHub Actions", "Nix daemon"
    string publicKey; // Ed25519 public key (hex)
    uint256 totalBuilds; // Total builds attested
    bool active;
}
```

## Enums
### SLSALevel

```solidity
enum SLSALevel {
    Level0,
    Level1,
    Level2,
    Level3
}
```

