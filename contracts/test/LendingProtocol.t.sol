// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {Test, console2} from "forge-std/Test.sol";
import {LendingProtocol} from "../src/LendingProtocol.sol";

/**
 * @title LendingProtocolTest
 * @notice Comprehensive test suite for DeFi lending with compliance
 */
contract LendingProtocolTest is Test {
    LendingProtocol public lending;

    address public lender1 = address(0x1);
    address public lender2 = address(0x2);
    address public borrower1 = address(0x3);
    address public borrower2 = address(0x4);
    address public liquidator = address(0x5);

    uint256 public constant INITIAL_BALANCE = 100 ether;

    function setUp() public {
        lending = new LendingProtocol();

        // Fund accounts
        vm.deal(lender1, INITIAL_BALANCE);
        vm.deal(lender2, INITIAL_BALANCE);
        vm.deal(borrower1, INITIAL_BALANCE);
        vm.deal(borrower2, INITIAL_BALANCE);
        vm.deal(liquidator, INITIAL_BALANCE);
    }

    // ============ Deposit Tests ============

    function test_Deposit() public {
        uint256 depositAmount = 10 ether;

        vm.prank(lender1);
        lending.deposit{value: depositAmount}();

        (uint256 totalDeposits,, uint256 liquidity,) = lending.getPoolStatus();

        assertEq(totalDeposits, depositAmount);
        assertEq(liquidity, depositAmount);
    }

    function test_MultipleDeposits() public {
        vm.prank(lender1);
        lending.deposit{value: 10 ether}();

        vm.prank(lender2);
        lending.deposit{value: 20 ether}();

        (uint256 totalDeposits,, uint256 liquidity,) = lending.getPoolStatus();

        assertEq(totalDeposits, 30 ether);
        assertEq(liquidity, 30 ether);
    }

    function test_CannotDepositZero() public {
        vm.prank(lender1);
        vm.expectRevert("Deposit amount must be > 0");
        lending.deposit{value: 0}();
    }

    // ============ Withdrawal Tests ============

    function test_Withdraw() public {
        // Deposit first
        vm.prank(lender1);
        lending.deposit{value: 10 ether}();

        // Withdraw
        vm.prank(lender1);
        lending.withdraw(5 ether);

        (uint256 totalDeposits,, uint256 liquidity,) = lending.getPoolStatus();

        assertEq(totalDeposits, 5 ether);
        assertEq(liquidity, 5 ether);
    }

    function test_CannotWithdrawMoreThanAvailable() public {
        vm.prank(lender1);
        lending.deposit{value: 10 ether}();

        vm.prank(lender1);
        vm.expectRevert(
            abi.encodeWithSelector(
                LendingProtocol.InsufficientLiquidity.selector,
                20 ether,
                10 ether
            )
        );
        lending.withdraw(20 ether);
    }

    // ============ Loan Application Tests (WITH COMPLIANCE) ============

    function test_ApplyForLoan_WithConsent() public {
        // Setup: Lender deposits
        vm.prank(lender1);
        lending.deposit{value: 10 ether}();

        // Borrower grants LGPD consent
        vm.prank(borrower1);
        lending.grantConsent(
            address(lending),
            365 days,
            "Loan application and credit scoring"
        );

        // Apply for loan (1 ETH with 1.5 ETH collateral)
        vm.prank(borrower1);
        bytes32 loanId = lending.applyForLoan{value: 1.5 ether}(1 ether);

        // Verify loan created
        LendingProtocol.Loan memory loan = lending.getLoan(loanId);

        assertEq(loan.borrower, borrower1);
        assertEq(loan.principal, 1 ether);
        assertEq(loan.collateral, 1.5 ether);
        assertTrue(loan.active);
        assertFalse(loan.liquidated);
    }

    function test_ApplyForLoan_WithoutConsent_Reverts() public {
        // Setup: Lender deposits
        vm.prank(lender1);
        lending.deposit{value: 10 ether}();

        // Try to apply WITHOUT consent → should revert
        vm.prank(borrower1);
        vm.expectRevert(
            abi.encodeWithSelector(
                LendingProtocol.LGPD_Article7_ConsentRequired.selector,
                borrower1
            )
        );
        lending.applyForLoan{value: 1.5 ether}(1 ether);
    }

    function test_ApplyForLoan_InsufficientCollateral() public {
        vm.prank(lender1);
        lending.deposit{value: 10 ether}();

        vm.prank(borrower1);
        lending.grantConsent(address(lending), 365 days, "Loan application");

        // Try to borrow 1 ETH with only 1 ETH collateral (need 1.5 ETH)
        vm.prank(borrower1);
        vm.expectRevert(
            abi.encodeWithSelector(
                LendingProtocol.InsufficientCollateral.selector,
                1 ether,
                1.5 ether
            )
        );
        lending.applyForLoan{value: 1 ether}(1 ether);
    }

    function test_ApplyForLoan_InsufficientLiquidity() public {
        // No deposits → no liquidity

        vm.prank(borrower1);
        lending.grantConsent(address(lending), 365 days, "Loan application");

        vm.prank(borrower1);
        vm.expectRevert(
            abi.encodeWithSelector(
                LendingProtocol.InsufficientLiquidity.selector,
                1 ether,
                0
            )
        );
        lending.applyForLoan{value: 1.5 ether}(1 ether);
    }

    function test_MultipleLoansSameBorrower() public {
        vm.prank(lender1);
        lending.deposit{value: 20 ether}();

        vm.prank(borrower1);
        lending.grantConsent(address(lending), 365 days, "Multiple loans");

        // First loan
        vm.prank(borrower1);
        bytes32 loan1 = lending.applyForLoan{value: 1.5 ether}(1 ether);

        // Second loan
        vm.prank(borrower1);
        bytes32 loan2 = lending.applyForLoan{value: 3 ether}(2 ether);

        // Verify both loans
        bytes32[] memory loans = lending.getBorrowerLoans(borrower1);
        assertEq(loans.length, 2);
        assertEq(loans[0], loan1);
        assertEq(loans[1], loan2);
    }

    // ============ Loan Repayment Tests ============

    function test_RepayLoan() public {
        // Setup loan
        vm.prank(lender1);
        lending.deposit{value: 10 ether}();

        vm.prank(borrower1);
        lending.grantConsent(address(lending), 365 days, "Loan");

        vm.prank(borrower1);
        bytes32 loanId = lending.applyForLoan{value: 1.5 ether}(1 ether);

        // Warp time forward (30 days)
        vm.warp(block.timestamp + 30 days);

        // Calculate repayment amount
        uint256 interest = lending.calculateInterest(loanId);
        uint256 totalOwed = 1 ether + interest;

        // Repay
        vm.prank(borrower1);
        lending.repayLoan{value: totalOwed}(loanId);

        // Verify loan repaid
        LendingProtocol.Loan memory loan = lending.getLoan(loanId);
        assertFalse(loan.active);
    }

    function test_CannotRepayOthersLoan() public {
        // Setup loan
        vm.prank(lender1);
        lending.deposit{value: 10 ether}();

        vm.prank(borrower1);
        lending.grantConsent(address(lending), 365 days, "Loan");

        vm.prank(borrower1);
        bytes32 loanId = lending.applyForLoan{value: 1.5 ether}(1 ether);

        // Try to repay as different user
        vm.prank(borrower2);
        vm.expectRevert(
            abi.encodeWithSelector(
                LendingProtocol.UnauthorizedRepayment.selector,
                loanId,
                borrower2
            )
        );
        lending.repayLoan{value: 1 ether}(loanId);
    }

    function test_RepayLoan_InsufficientPayment() public {
        vm.prank(lender1);
        lending.deposit{value: 10 ether}();

        vm.prank(borrower1);
        lending.grantConsent(address(lending), 365 days, "Loan");

        vm.prank(borrower1);
        bytes32 loanId = lending.applyForLoan{value: 1.5 ether}(1 ether);

        vm.warp(block.timestamp + 30 days);

        uint256 interest = lending.calculateInterest(loanId);
        uint256 totalOwed = 1 ether + interest;

        // Try to pay less than owed
        vm.prank(borrower1);
        vm.expectRevert(
            abi.encodeWithSelector(
                LendingProtocol.InsufficientBalance.selector,
                0.5 ether,
                totalOwed
            )
        );
        lending.repayLoan{value: 0.5 ether}(loanId);
    }

    // ============ Interest Calculation Tests ============

    function test_InterestCalculation_30Days() public {
        vm.prank(lender1);
        lending.deposit{value: 10 ether}();

        vm.prank(borrower1);
        lending.grantConsent(address(lending), 365 days, "Loan");

        vm.prank(borrower1);
        bytes32 loanId = lending.applyForLoan{value: 1.5 ether}(1 ether);

        // Warp 30 days
        vm.warp(block.timestamp + 30 days);

        uint256 interest = lending.calculateInterest(loanId);

        // Expected: 1 ETH * 5% * (30/365) = ~0.0041 ETH
        assertGt(interest, 0);
        assertLt(interest, 0.01 ether); // Should be small for 30 days
    }

    function test_InterestCalculation_1Year() public {
        vm.prank(lender1);
        lending.deposit{value: 10 ether}();

        vm.prank(borrower1);
        lending.grantConsent(address(lending), 365 days, "Loan");

        vm.prank(borrower1);
        bytes32 loanId = lending.applyForLoan{value: 1.5 ether}(1 ether);

        // Warp 1 year
        vm.warp(block.timestamp + 365 days);

        uint256 interest = lending.calculateInterest(loanId);

        // Expected: 1 ETH * 5% = 0.05 ETH
        assertApproxEqRel(interest, 0.05 ether, 0.01e18); // 1% tolerance
    }

    // ============ Liquidation Tests ============

    function test_CannotLiquidateHealthyLoan() public {
        vm.prank(lender1);
        lending.deposit{value: 10 ether}();

        vm.prank(borrower1);
        lending.grantConsent(address(lending), 365 days, "Loan");

        // Healthy loan: 1 ETH borrowed, 1.5 ETH collateral (150%)
        vm.prank(borrower1);
        bytes32 loanId = lending.applyForLoan{value: 1.5 ether}(1 ether);

        // Try to liquidate
        vm.prank(liquidator);
        vm.expectRevert(
            abi.encodeWithSelector(LendingProtocol.LoanNotLiquidatable.selector, loanId)
        );
        lending.liquidate(loanId);
    }

    function test_HealthFactor() public {
        vm.prank(lender1);
        lending.deposit{value: 10 ether}();

        vm.prank(borrower1);
        lending.grantConsent(address(lending), 365 days, "Loan");

        vm.prank(borrower1);
        bytes32 loanId = lending.applyForLoan{value: 1.5 ether}(1 ether);

        uint256 healthFactor = lending.getLoanHealthFactor(loanId);

        // Health factor should be 150% = 15000 basis points
        assertApproxEqRel(healthFactor, 15000, 0.01e18);
    }

    function test_IsLiquidatable() public {
        vm.prank(lender1);
        lending.deposit{value: 10 ether}();

        vm.prank(borrower1);
        lending.grantConsent(address(lending), 365 days, "Loan");

        vm.prank(borrower1);
        bytes32 loanId = lending.applyForLoan{value: 1.5 ether}(1 ether);

        // Initially healthy
        assertFalse(lending.isLiquidatable(loanId));

        // After 1 year of interest, might become liquidatable
        vm.warp(block.timestamp + 365 days);

        // Still healthy (1.5 ETH collateral > 1.05 ETH debt)
        assertFalse(lending.isLiquidatable(loanId));
    }

    // ============ Pool Status Tests ============

    function test_PoolStatus_EmptyPool() public {
        (
            uint256 totalDeposits,
            uint256 totalBorrowed,
            uint256 availableLiquidity,
            uint256 utilizationRate
        ) = lending.getPoolStatus();

        assertEq(totalDeposits, 0);
        assertEq(totalBorrowed, 0);
        assertEq(availableLiquidity, 0);
        assertEq(utilizationRate, 0);
    }

    function test_PoolStatus_WithDepositsAndLoans() public {
        vm.prank(lender1);
        lending.deposit{value: 10 ether}();

        vm.prank(borrower1);
        lending.grantConsent(address(lending), 365 days, "Loan");

        vm.prank(borrower1);
        lending.applyForLoan{value: 1.5 ether}(1 ether);

        (
            uint256 totalDeposits,
            uint256 totalBorrowed,
            uint256 availableLiquidity,
            uint256 utilizationRate
        ) = lending.getPoolStatus();

        assertEq(totalDeposits, 10 ether);
        assertEq(totalBorrowed, 1 ether);
        assertEq(availableLiquidity, 9 ether);
        assertEq(utilizationRate, 1000); // 10% = 1000 basis points
    }

    // ============ Gas Optimization Tests ============

    function test_GasCost_ApplyForLoan() public {
        vm.prank(lender1);
        lending.deposit{value: 10 ether}();

        vm.prank(borrower1);
        lending.grantConsent(address(lending), 365 days, "Loan");

        uint256 gasBefore = gasleft();
        vm.prank(borrower1);
        lending.applyForLoan{value: 1.5 ether}(1 ether);
        uint256 gasUsed = gasBefore - gasleft();

        console2.log("Gas used for applyForLoan:", gasUsed);

        // Should be reasonable (< 300k gas)
        assertLt(gasUsed, 300000, "Gas cost too high for loan application");
    }

    function test_GasCost_RepayLoan() public {
        vm.prank(lender1);
        lending.deposit{value: 10 ether}();

        vm.prank(borrower1);
        lending.grantConsent(address(lending), 365 days, "Loan");

        vm.prank(borrower1);
        bytes32 loanId = lending.applyForLoan{value: 1.5 ether}(1 ether);

        vm.warp(block.timestamp + 30 days);

        uint256 interest = lending.calculateInterest(loanId);
        uint256 totalOwed = 1 ether + interest;

        uint256 gasBefore = gasleft();
        vm.prank(borrower1);
        lending.repayLoan{value: totalOwed}(loanId);
        uint256 gasUsed = gasBefore - gasleft();

        console2.log("Gas used for repayLoan:", gasUsed);

        assertLt(gasUsed, 200000, "Gas cost too high for repayment");
    }

    // ============ Integration Tests ============

    function test_FullLendingCycle() public {
        // 1. Lender deposits
        vm.prank(lender1);
        lending.deposit{value: 10 ether}();

        // 2. Borrower grants consent
        vm.prank(borrower1);
        lending.grantConsent(address(lending), 365 days, "Full cycle test");

        // 3. Borrower applies for loan
        vm.prank(borrower1);
        bytes32 loanId = lending.applyForLoan{value: 1.5 ether}(1 ether);

        // 4. Time passes (30 days)
        vm.warp(block.timestamp + 30 days);

        // 5. Borrower repays
        uint256 interest = lending.calculateInterest(loanId);
        uint256 totalOwed = 1 ether + interest;

        vm.prank(borrower1);
        lending.repayLoan{value: totalOwed}(loanId);

        // 6. Lender withdraws
        vm.prank(lender1);
        lending.withdraw(5 ether);

        // Verify final state
        LendingProtocol.Loan memory loan = lending.getLoan(loanId);
        assertFalse(loan.active);

        (uint256 totalDeposits,,,) = lending.getPoolStatus();
        assertGt(totalDeposits, 5 ether); // Should have interest earned
    }
}
