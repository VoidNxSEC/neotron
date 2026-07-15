# IPriceOracle
**Title:**
IPriceOracle

Chainlink-compatible price feed interface

Matches Chainlink's AggregatorV3Interface for drop-in compatibility


## Functions
### latestRoundData


```solidity
function latestRoundData()
    external
    view
    returns (uint80 roundId, int256 answer, uint256 startedAt, uint256 updatedAt, uint80 answeredInRound);
```

### decimals


```solidity
function decimals() external view returns (uint8);
```

### description


```solidity
function description() external view returns (string memory);
```

