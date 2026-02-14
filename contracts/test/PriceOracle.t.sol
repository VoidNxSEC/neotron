// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {Test, console2} from "forge-std/Test.sol";
import {PriceOracle, IPriceOracle} from "../src/PriceOracle.sol";

contract PriceOracleTest is Test {
    PriceOracle public oracle;

    address public owner = address(this);
    address public feeder = address(0x1);
    address public user = address(0x2);

    int256 public constant INITIAL_PRICE = 2000e8; // $2000 with 8 decimals
    uint256 public constant MAX_STALENESS = 3600; // 1 hour

    function setUp() public {
        oracle = new PriceOracle(INITIAL_PRICE, 8, "ETH / USD", MAX_STALENESS);
        oracle.authorizeFeed(feeder);
    }

    // ============ Constructor Tests ============

    function test_InitialState() public view {
        assertEq(oracle.latestPrice(), INITIAL_PRICE);
        assertEq(oracle.decimals(), 8);
        assertEq(oracle.currentRound(), 1);
        assertEq(oracle.maxStaleness(), MAX_STALENESS);
        assertEq(oracle.owner(), owner);
    }

    function test_Description() public view {
        assertEq(oracle.description(), "ETH / USD");
    }

    function test_RevertInvalidInitialPrice() public {
        vm.expectRevert(PriceOracle.InvalidPrice.selector);
        new PriceOracle(0, 8, "ETH / USD", 3600);
    }

    function test_RevertNegativeInitialPrice() public {
        vm.expectRevert(PriceOracle.InvalidPrice.selector);
        new PriceOracle(-1, 8, "ETH / USD", 3600);
    }

    // ============ Price Update Tests ============

    function test_UpdatePrice() public {
        int256 newPrice = 2100e8;
        vm.prank(feeder);
        oracle.updatePrice(newPrice);

        assertEq(oracle.latestPrice(), newPrice);
        assertEq(oracle.currentRound(), 2);
    }

    function test_OwnerCanUpdatePrice() public {
        oracle.updatePrice(2050e8);
        assertEq(oracle.latestPrice(), 2050e8);
    }

    function test_RevertUnauthorizedUpdate() public {
        vm.prank(user);
        vm.expectRevert(PriceOracle.Unauthorized.selector);
        oracle.updatePrice(2100e8);
    }

    function test_RevertZeroPrice() public {
        vm.expectRevert(PriceOracle.InvalidPrice.selector);
        oracle.updatePrice(0);
    }

    function test_RevertNegativePrice() public {
        vm.expectRevert(PriceOracle.InvalidPrice.selector);
        oracle.updatePrice(-100);
    }

    function test_RevertExcessiveDeviation() public {
        // Try to change price by more than 50%
        int256 newPrice = 3100e8; // 55% increase
        vm.expectRevert(
            abi.encodeWithSelector(PriceOracle.ExcessiveDeviation.selector, INITIAL_PRICE, newPrice, 5500)
        );
        oracle.updatePrice(newPrice);
    }

    function test_AllowMaxDeviation() public {
        // 50% increase should be allowed
        int256 newPrice = 3000e8;
        oracle.updatePrice(newPrice);
        assertEq(oracle.latestPrice(), newPrice);
    }

    function test_MultipleUpdates() public {
        oracle.updatePrice(2100e8);
        assertEq(oracle.currentRound(), 2);

        oracle.updatePrice(2200e8);
        assertEq(oracle.currentRound(), 3);

        oracle.updatePrice(2150e8);
        assertEq(oracle.currentRound(), 4);
        assertEq(oracle.latestPrice(), 2150e8);
    }

    // ============ LatestRoundData Tests ============

    function test_LatestRoundData() public view {
        (
            uint80 roundId,
            int256 answer,
            uint256 startedAt,
            uint256 updatedAt,
            uint80 answeredInRound
        ) = oracle.latestRoundData();

        assertEq(roundId, 1);
        assertEq(answer, INITIAL_PRICE);
        assertGt(startedAt, 0);
        assertEq(updatedAt, startedAt);
        assertEq(answeredInRound, 1);
    }

    // ============ Staleness Tests ============

    function test_GetPriceFresh() public view {
        int256 price = oracle.getPrice();
        assertEq(price, INITIAL_PRICE);
    }

    function test_IsFresh() public view {
        assertTrue(oracle.isFresh());
    }

    function test_RevertStalePrice() public {
        // Advance time past staleness threshold
        vm.warp(block.timestamp + MAX_STALENESS + 1);

        vm.expectRevert(
            abi.encodeWithSelector(PriceOracle.StalePrice.selector, oracle.lastUpdatedAt(), MAX_STALENESS)
        );
        oracle.getPrice();
    }

    function test_IsNotFreshAfterStaleness() public {
        vm.warp(block.timestamp + MAX_STALENESS + 1);
        assertFalse(oracle.isFresh());
    }

    function test_FreshAfterUpdate() public {
        vm.warp(block.timestamp + MAX_STALENESS + 1);
        assertFalse(oracle.isFresh());

        oracle.updatePrice(2050e8);
        assertTrue(oracle.isFresh());
    }

    // ============ ETH to USD Conversion ============

    function test_EthToUsd() public view {
        // 1 ETH = 1e18 wei, price = 2000e8
        // Expected: 1e18 * 2000e8 / 1e18 = 2000e8
        uint256 usdValue = oracle.ethToUsd(1 ether);
        assertEq(usdValue, 2000e8);
    }

    function test_EthToUsdHalfEther() public view {
        uint256 usdValue = oracle.ethToUsd(0.5 ether);
        assertEq(usdValue, 1000e8);
    }

    function test_EthToUsdStaleReverts() public {
        vm.warp(block.timestamp + MAX_STALENESS + 1);
        vm.expectRevert();
        oracle.ethToUsd(1 ether);
    }

    // ============ Feeder Management Tests ============

    function test_AuthorizeFeeder() public {
        address newFeeder = address(0x99);
        oracle.authorizeFeed(newFeeder);
        assertTrue(oracle.authorizedFeeders(newFeeder));
    }

    function test_RevokeFeeder() public {
        oracle.revokeFeeder(feeder);
        assertFalse(oracle.authorizedFeeders(feeder));

        vm.prank(feeder);
        vm.expectRevert(PriceOracle.Unauthorized.selector);
        oracle.updatePrice(2100e8);
    }

    function test_OnlyOwnerCanAuthorize() public {
        vm.prank(user);
        vm.expectRevert(PriceOracle.Unauthorized.selector);
        oracle.authorizeFeed(address(0x99));
    }

    // ============ Admin Tests ============

    function test_SetMaxStaleness() public {
        oracle.setMaxStaleness(7200);
        assertEq(oracle.maxStaleness(), 7200);
    }

    // ============ Fuzz Tests ============

    function testFuzz_UpdatePriceWithinDeviation(uint256 delta) public {
        // Bound delta to valid range (0-50% of current price)
        delta = bound(delta, 0, uint256(INITIAL_PRICE) / 2);
        int256 newPrice = INITIAL_PRICE + int256(delta);

        oracle.updatePrice(newPrice);
        assertEq(oracle.latestPrice(), newPrice);
    }

    function testFuzz_EthToUsd(uint256 ethAmount) public view {
        ethAmount = bound(ethAmount, 0, 1000 ether);
        uint256 usd = oracle.ethToUsd(ethAmount);
        uint256 expected = (ethAmount * uint256(INITIAL_PRICE)) / 1e18;
        assertEq(usd, expected);
    }
}
