# PriceOracle
**Inherits:**
[IPriceOracle](/src/PriceOracle.sol/interface.IPriceOracle.md)

**Title:**
PriceOracle

**Author:**
NEXUS Platform

Owner-managed price oracle with staleness protection

Can be replaced with Chainlink AggregatorV3 in production
Features:
- Price updates restricted to authorized feeders
- Staleness check (configurable max age)
- Price deviation circuit breaker (max 50% change per update)
- Decimal normalization helpers


## State Variables
### owner

```solidity
address public owner
```


### authorizedFeeders

```solidity
mapping(address => bool) public authorizedFeeders
```


### _decimals

```solidity
uint8 private _decimals
```


### _description

```solidity
string private _description
```


### latestPrice

```solidity
int256 public latestPrice
```


### lastUpdatedAt

```solidity
uint256 public lastUpdatedAt
```


### currentRound

```solidity
uint80 public currentRound
```


### maxStaleness
Maximum price age in seconds before considered stale


```solidity
uint256 public maxStaleness
```


### MAX_DEVIATION_BPS
Maximum allowed price deviation per update (basis points, 5000 = 50%)


```solidity
uint256 public constant MAX_DEVIATION_BPS = 5000
```


## Functions
### onlyOwner


```solidity
modifier onlyOwner() ;
```

### onlyFeeder


```solidity
modifier onlyFeeder() ;
```

### constructor


```solidity
constructor(int256 initialPrice, uint8 priceDecimals, string memory desc, uint256 maxAge) ;
```
**Parameters**

|Name|Type|Description|
|----|----|-----------|
|`initialPrice`|`int256`|Initial price (e.g., 2000e8 for $2000 with 8 decimals)|
|`priceDecimals`|`uint8`|Number of decimals in price (typically 8 for Chainlink)|
|`desc`|`string`|Price feed description (e.g., "ETH / USD")|
|`maxAge`|`uint256`|Maximum allowed price age in seconds (e.g., 3600 for 1 hour)|


### latestRoundData


```solidity
function latestRoundData()
    external
    view
    override
    returns (uint80 roundId, int256 answer, uint256 startedAt, uint256 updatedAt, uint80 answeredInRound);
```

### decimals


```solidity
function decimals() external view override returns (uint8);
```

### description


```solidity
function description() external view override returns (string memory);
```

### updatePrice

Update the price (restricted to authorized feeders)


```solidity
function updatePrice(int256 newPrice) external onlyFeeder;
```
**Parameters**

|Name|Type|Description|
|----|----|-----------|
|`newPrice`|`int256`|New price value|


### getPrice

Get current price with staleness check

Reverts if price is stale


```solidity
function getPrice() external view returns (int256 price);
```
**Returns**

|Name|Type|Description|
|----|----|-----------|
|`price`|`int256`|Current price|


### isFresh

Check if the price feed is fresh (not stale)


```solidity
function isFresh() external view returns (bool);
```
**Returns**

|Name|Type|Description|
|----|----|-----------|
|`<none>`|`bool`|fresh True if price was updated within maxStaleness|


### ethToUsd

Convert an ETH amount to USD using current price


```solidity
function ethToUsd(uint256 ethAmount) external view returns (uint256);
```
**Parameters**

|Name|Type|Description|
|----|----|-----------|
|`ethAmount`|`uint256`|Amount in wei|

**Returns**

|Name|Type|Description|
|----|----|-----------|
|`<none>`|`uint256`|usdValue USD value (with oracle decimals)|


### authorizeFeed


```solidity
function authorizeFeed(address feeder) external onlyOwner;
```

### revokeFeeder


```solidity
function revokeFeeder(address feeder) external onlyOwner;
```

### setMaxStaleness


```solidity
function setMaxStaleness(uint256 newMaxAge) external onlyOwner;
```

## Events
### PriceUpdated

```solidity
event PriceUpdated(uint80 indexed roundId, int256 price, uint256 timestamp);
```

### FeederAuthorized

```solidity
event FeederAuthorized(address indexed feeder);
```

### FeederRevoked

```solidity
event FeederRevoked(address indexed feeder);
```

### MaxStalenessUpdated

```solidity
event MaxStalenessUpdated(uint256 oldValue, uint256 newValue);
```

## Errors
### Unauthorized

```solidity
error Unauthorized();
```

### StalePrice

```solidity
error StalePrice(uint256 lastUpdate, uint256 maxAge);
```

### InvalidPrice

```solidity
error InvalidPrice();
```

### ExcessiveDeviation

```solidity
error ExcessiveDeviation(int256 oldPrice, int256 newPrice, uint256 deviationBps);
```

