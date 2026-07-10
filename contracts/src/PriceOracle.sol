// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title IPriceOracle
 * @notice Chainlink-compatible price feed interface
 * @dev Matches Chainlink's AggregatorV3Interface for drop-in compatibility
 */
interface IPriceOracle {
    function latestRoundData()
        external
        view
        returns (
            uint80 roundId,
            int256 answer,
            uint256 startedAt,
            uint256 updatedAt,
            uint80 answeredInRound
        );

    function decimals() external view returns (uint8);
    function description() external view returns (string memory);
}

/**
 * @title PriceOracle
 * @author NEXUS Platform
 * @notice Owner-managed price oracle with staleness protection
 * @dev Can be replaced with Chainlink AggregatorV3 in production
 *
 * Features:
 * - Price updates restricted to authorized feeders
 * - Staleness check (configurable max age)
 * - Price deviation circuit breaker (max 50% change per update)
 * - Decimal normalization helpers
 */
contract PriceOracle is IPriceOracle {
    // ============ Storage ============

    address public owner;
    mapping(address => bool) public authorizedFeeders;

    uint8 private _decimals;
    string private _description;

    int256 public latestPrice;
    uint256 public lastUpdatedAt;
    uint80 public currentRound;

    /// @notice Maximum price age in seconds before considered stale
    uint256 public maxStaleness;

    /// @notice Maximum allowed price deviation per update (basis points, 5000 = 50%)
    uint256 public constant MAX_DEVIATION_BPS = 5000;

    // ============ Events ============

    event PriceUpdated(uint80 indexed roundId, int256 price, uint256 timestamp);
    event FeederAuthorized(address indexed feeder);
    event FeederRevoked(address indexed feeder);
    event MaxStalenessUpdated(uint256 oldValue, uint256 newValue);

    // ============ Errors ============

    error Unauthorized();
    error StalePrice(uint256 lastUpdate, uint256 maxAge);
    error InvalidPrice();
    error ExcessiveDeviation(int256 oldPrice, int256 newPrice, uint256 deviationBps);

    // ============ Modifiers ============

    modifier onlyOwner() {
        if (msg.sender != owner) revert Unauthorized();
        _;
    }

    modifier onlyFeeder() {
        if (!authorizedFeeders[msg.sender] && msg.sender != owner) revert Unauthorized();
        _;
    }

    // ============ Constructor ============

    /**
     * @param initialPrice Initial price (e.g., 2000e8 for $2000 with 8 decimals)
     * @param priceDecimals Number of decimals in price (typically 8 for Chainlink)
     * @param desc Price feed description (e.g., "ETH / USD")
     * @param maxAge Maximum allowed price age in seconds (e.g., 3600 for 1 hour)
     */
    constructor(
        int256 initialPrice,
        uint8 priceDecimals,
        string memory desc,
        uint256 maxAge
    ) {
        if (initialPrice <= 0) revert InvalidPrice();

        owner = msg.sender;
        authorizedFeeders[msg.sender] = true;
        _decimals = priceDecimals;
        _description = desc;
        maxStaleness = maxAge;

        latestPrice = initialPrice;
        lastUpdatedAt = block.timestamp;
        currentRound = 1;

        emit PriceUpdated(1, initialPrice, block.timestamp);
    }

    // ============ Price Feed Interface ============

    /// @inheritdoc IPriceOracle
    function latestRoundData()
        external
        view
        override
        returns (
            uint80 roundId,
            int256 answer,
            uint256 startedAt,
            uint256 updatedAt,
            uint80 answeredInRound
        )
    {
        return (currentRound, latestPrice, lastUpdatedAt, lastUpdatedAt, currentRound);
    }

    /// @inheritdoc IPriceOracle
    function decimals() external view override returns (uint8) {
        return _decimals;
    }

    /// @inheritdoc IPriceOracle
    function description() external view override returns (string memory) {
        return _description;
    }

    // ============ Price Update ============

    /**
     * @notice Update the price (restricted to authorized feeders)
     * @param newPrice New price value
     */
    function updatePrice(int256 newPrice) external onlyFeeder {
        if (newPrice <= 0) revert InvalidPrice();

        // Check price deviation circuit breaker
        if (latestPrice > 0) {
            uint256 deviation;
            if (newPrice > latestPrice) {
                deviation = uint256(newPrice - latestPrice) * 10000 / uint256(latestPrice);
            } else {
                deviation = uint256(latestPrice - newPrice) * 10000 / uint256(latestPrice);
            }

            if (deviation > MAX_DEVIATION_BPS) {
                revert ExcessiveDeviation(latestPrice, newPrice, deviation);
            }
        }

        currentRound++;
        latestPrice = newPrice;
        lastUpdatedAt = block.timestamp;

        emit PriceUpdated(currentRound, newPrice, block.timestamp);
    }

    // ============ Helpers ============

    /**
     * @notice Get current price with staleness check
     * @return price Current price
     * @dev Reverts if price is stale
     */
    function getPrice() external view returns (int256 price) {
        if (block.timestamp - lastUpdatedAt > maxStaleness) {
            revert StalePrice(lastUpdatedAt, maxStaleness);
        }
        return latestPrice;
    }

    /**
     * @notice Check if the price feed is fresh (not stale)
     * @return fresh True if price was updated within maxStaleness
     */
    function isFresh() external view returns (bool) {
        return block.timestamp - lastUpdatedAt <= maxStaleness;
    }

    /**
     * @notice Convert an ETH amount to USD using current price
     * @param ethAmount Amount in wei
     * @return usdValue USD value (with oracle decimals)
     */
    function ethToUsd(uint256 ethAmount) external view returns (uint256) {
        if (block.timestamp - lastUpdatedAt > maxStaleness) {
            revert StalePrice(lastUpdatedAt, maxStaleness);
        }
        // price has _decimals precision, ethAmount is in wei (18 decimals)
        // result: ethAmount * price / 1e18 → USD with _decimals precision
        return (ethAmount * uint256(latestPrice)) / 1e18;
    }

    // ============ Admin ============

    function authorizeFeed(address feeder) external onlyOwner {
        authorizedFeeders[feeder] = true;
        emit FeederAuthorized(feeder);
    }

    function revokeFeeder(address feeder) external onlyOwner {
        authorizedFeeders[feeder] = false;
        emit FeederRevoked(feeder);
    }

    function setMaxStaleness(uint256 newMaxAge) external onlyOwner {
        emit MaxStalenessUpdated(maxStaleness, newMaxAge);
        maxStaleness = newMaxAge;
    }
}
