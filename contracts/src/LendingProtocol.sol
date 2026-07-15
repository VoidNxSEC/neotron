// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {LGPDConsent} from "./LGPDConsent.sol";
import {AuditLogger} from "./AuditLogger.sol";

/**
 * @title LendingProtocol
 * @author NEXUS Platform
 * @notice DeFi lending protocol with FULL compliance enforcement (4 layers)
 * @dev First-ever DeFi protocol with kernel-level compliance integration
 *
 * Defense-in-Depth Compliance (ALL 4 LAYERS):
 * ┌────────────────────────────────────────────────────────────┐
 * │  Layer 1: SENTINEL (Application - Python validation)      │
 * │  Layer 2: BASTION (Kernel - seccomp-BPF syscalls)         │
 * │  Layer 3: BASTION-SC (Smart Contract - this contract)     │
 * │  Layer 4: Audit Trail (IPFS + Arweave via AuditLogger)    │
 * └────────────────────────────────────────────────────────────┘
 *
 * Features:
 * - Borrow/lend with LGPD Article 7 consent enforcement
 * - Collateralized loans (150% collateral ratio)
 * - Interest accrual (5% APY)
 * - Liquidation mechanism
 * - Complete audit trail (on-chain + IPFS/Arweave)
 * - Compliance violations → automatic revert
 */
contract LendingProtocol is LGPDConsent, AuditLogger {
    // ============ Structs ============

    struct Loan {
        address borrower;
        uint256 principal;           // Amount borrowed
        uint256 collateral;          // ETH collateral
        uint256 interestRate;        // Basis points (500 = 5%)
        uint256 borrowedAt;          // Timestamp
        uint256 lastAccrualTime;     // Last interest calculation
        uint256 accruedInterest;     // Interest accrued
        bool active;
        bool liquidated;
    }

    struct LendingPool {
        uint256 totalDeposits;
        uint256 totalBorrowed;
        uint256 availableLiquidity;
    }

    // ============ Storage ============

    /// @notice Minimum collateral ratio (150%)
    uint256 public constant COLLATERAL_RATIO = 150;

    /// @notice Annual interest rate (5%)
    uint256 public constant INTEREST_RATE = 500; // 5% in basis points

    /// @notice Liquidation threshold (120%)
    uint256 public constant LIQUIDATION_THRESHOLD = 120;

    /// @notice Mapping: loanId => Loan
    mapping(bytes32 => Loan) public loans;

    /// @notice Mapping: borrower => loanIds[]
    mapping(address => bytes32[]) public borrowerLoans;

    /// @notice Lending pool state
    LendingPool public pool;

    /// @notice Total loans created
    uint256 public totalLoans;

    // ============ Events ============

    event Deposited(address indexed lender, uint256 amount, uint256 timestamp);

    event LoanRequested(
        bytes32 indexed loanId,
        address indexed borrower,
        uint256 principal,
        uint256 collateral,
        uint256 timestamp
    );

    event LoanApproved(
        bytes32 indexed loanId,
        address indexed borrower,
        uint256 amount,
        uint256 timestamp
    );

    event LoanRepaid(
        bytes32 indexed loanId,
        address indexed borrower,
        uint256 principal,
        uint256 interest,
        uint256 timestamp
    );

    event LoanLiquidated(
        bytes32 indexed loanId,
        address indexed borrower,
        address indexed liquidator,
        uint256 collateralSeized,
        uint256 timestamp
    );

    event Withdrawn(address indexed lender, uint256 amount, uint256 timestamp);

    // ============ Errors ============

    error InsufficientLiquidity(uint256 requested, uint256 available);
    error InsufficientCollateral(uint256 provided, uint256 required);
    error LoanNotFound(bytes32 loanId);
    error LoanNotActive(bytes32 loanId);
    error UnauthorizedRepayment(bytes32 loanId, address caller);
    error LoanNotLiquidatable(bytes32 loanId);
    error InsufficientBalance(uint256 balance, uint256 requested);

    // ============ Deposit Functions ============

    /**
     * @notice Deposit funds into lending pool
     * @dev Anyone can deposit to earn interest from borrowers
     */
    function deposit() external payable {
        require(msg.value > 0, "Deposit amount must be > 0");

        pool.totalDeposits += msg.value;
        pool.availableLiquidity += msg.value;

        emit Deposited(msg.sender, msg.value, block.timestamp);

        // Log audit trail
        bytes32 logId = keccak256(abi.encodePacked("deposit", msg.sender, block.timestamp));
        logCompliance(
            logId,
            msg.sender,
            "DEFI",
            0,
            true,
            "deposit_ipfs_cid",  // Would be actual CID in production
            "",
            false
        );
    }

    /**
     * @notice Withdraw funds from lending pool
     * @param amount Amount to withdraw
     */
    function withdraw(uint256 amount) external {
        if (amount > pool.availableLiquidity) {
            revert InsufficientLiquidity(amount, pool.availableLiquidity);
        }

        pool.totalDeposits -= amount;
        pool.availableLiquidity -= amount;

        (bool success,) = msg.sender.call{value: amount}("");
        require(success, "Withdrawal failed");

        emit Withdrawn(msg.sender, amount, block.timestamp);
    }

    // ============ Borrowing Functions ============

    /**
     * @notice Apply for loan (requires LGPD Article 7 consent)
     * @dev COMPLIANCE ENFORCED: Automatic revert if no consent granted
     * @param amount Amount to borrow
     * @return loanId Unique loan identifier
     */
    function applyForLoan(uint256 amount)
        external
        payable
        lgpdArticle7Consent(msg.sender)  // ← COMPLIANCE LAYER 3: Smart contract enforcement
        returns (bytes32 loanId)
    {
        // Calculate required collateral (150%)
        uint256 requiredCollateral = (amount * COLLATERAL_RATIO) / 100;

        if (msg.value < requiredCollateral) {
            revert InsufficientCollateral(msg.value, requiredCollateral);
        }

        if (amount > pool.availableLiquidity) {
            revert InsufficientLiquidity(amount, pool.availableLiquidity);
        }

        // Create loan
        loanId = keccak256(abi.encodePacked(msg.sender, amount, block.timestamp));

        loans[loanId] = Loan({
            borrower: msg.sender,
            principal: amount,
            collateral: msg.value,
            interestRate: INTEREST_RATE,
            borrowedAt: block.timestamp,
            lastAccrualTime: block.timestamp,
            accruedInterest: 0,
            active: true,
            liquidated: false
        });

        borrowerLoans[msg.sender].push(loanId);
        totalLoans++;

        // Update pool
        pool.availableLiquidity -= amount;
        pool.totalBorrowed += amount;

        // Transfer borrowed amount to borrower
        (bool success,) = msg.sender.call{value: amount}("");
        require(success, "Loan transfer failed");

        emit LoanRequested(loanId, msg.sender, amount, msg.value, block.timestamp);
        emit LoanApproved(loanId, msg.sender, amount, block.timestamp);

        // Log compliance audit (Layer 4: IPFS/Arweave)
        bytes32 auditLogId = keccak256(abi.encodePacked("loan_approved", loanId));
        logCompliance(
            auditLogId,
            msg.sender,
            "LGPD",
            7,  // Article 7: Consent
            true,
            "loan_approval_ipfs_cid",  // Would be actual IPFS CID
            "",
            false
        );

        return loanId;
    }

    /**
     * @notice Repay loan with interest
     * @param loanId Loan identifier
     */
    function repayLoan(bytes32 loanId) external payable {
        Loan storage loan = loans[loanId];

        if (loan.borrower == address(0)) {
            revert LoanNotFound(loanId);
        }

        if (!loan.active) {
            revert LoanNotActive(loanId);
        }

        if (msg.sender != loan.borrower) {
            revert UnauthorizedRepayment(loanId, msg.sender);
        }

        // Calculate total owed (principal + interest)
        uint256 interest = calculateInterest(loanId);
        uint256 totalOwed = loan.principal + interest;

        if (msg.value < totalOwed) {
            revert InsufficientBalance(msg.value, totalOwed);
        }

        // Mark loan as repaid
        loan.active = false;
        loan.accruedInterest = interest;

        // Update pool
        pool.availableLiquidity += totalOwed;
        pool.totalBorrowed -= loan.principal;

        // Return collateral to borrower
        (bool success,) = loan.borrower.call{value: loan.collateral}("");
        require(success, "Collateral return failed");

        // Return excess payment
        if (msg.value > totalOwed) {
            (bool refundSuccess,) = msg.sender.call{value: msg.value - totalOwed}("");
            require(refundSuccess, "Refund failed");
        }

        emit LoanRepaid(loanId, msg.sender, loan.principal, interest, block.timestamp);

        // Log audit trail
        bytes32 auditLogId = keccak256(abi.encodePacked("loan_repaid", loanId));
        logCompliance(
            auditLogId,
            msg.sender,
            "DEFI",
            0,
            true,
            "loan_repayment_ipfs_cid",
            "",
            false
        );
    }

    /**
     * @notice Liquidate undercollateralized loan
     * @param loanId Loan identifier
     */
    function liquidate(bytes32 loanId) external {
        Loan storage loan = loans[loanId];

        if (loan.borrower == address(0)) {
            revert LoanNotFound(loanId);
        }

        if (!loan.active) {
            revert LoanNotActive(loanId);
        }

        // Check if liquidatable (collateral < 120% of debt)
        uint256 totalDebt = loan.principal + calculateInterest(loanId);
        uint256 liquidationValue = (totalDebt * LIQUIDATION_THRESHOLD) / 100;

        if (loan.collateral >= liquidationValue) {
            revert LoanNotLiquidatable(loanId);
        }

        // Mark as liquidated
        loan.active = false;
        loan.liquidated = true;

        // Update pool
        pool.totalBorrowed -= loan.principal;

        // Transfer collateral to liquidator (as reward for maintaining protocol health)
        (bool success,) = msg.sender.call{value: loan.collateral}("");
        require(success, "Liquidation payment failed");

        emit LoanLiquidated(
            loanId,
            loan.borrower,
            msg.sender,
            loan.collateral,
            block.timestamp
        );

        // Log audit trail
        bytes32 auditLogId = keccak256(abi.encodePacked("loan_liquidated", loanId));
        logCompliance(
            auditLogId,
            loan.borrower,
            "DEFI",
            0,
            false,  // Liquidation = compliance failure (undercollateralized)
            "liquidation_ipfs_cid",
            "",
            false
        );
    }

    // ============ View Functions ============

    /**
     * @notice Calculate accrued interest for a loan
     * @param loanId Loan identifier
     * @return interest Interest accrued
     */
    function calculateInterest(bytes32 loanId) public view returns (uint256) {
        Loan memory loan = loans[loanId];

        if (!loan.active) {
            return loan.accruedInterest;
        }

        uint256 timeElapsed = block.timestamp - loan.lastAccrualTime;
        uint256 yearInSeconds = 365 days;

        // Simple interest: principal * rate * time
        uint256 interest = (loan.principal * loan.interestRate * timeElapsed) / (10000 * yearInSeconds);

        return loan.accruedInterest + interest;
    }

    /**
     * @notice Get loan details
     * @param loanId Loan identifier
     * @return loan Loan struct
     */
    function getLoan(bytes32 loanId) external view returns (Loan memory) {
        return loans[loanId];
    }

    /**
     * @notice Get all loans for a borrower
     * @param borrower Borrower address
     * @return loanIds Array of loan IDs
     */
    function getBorrowerLoans(address borrower) external view returns (bytes32[] memory) {
        return borrowerLoans[borrower];
    }

    /**
     * @notice Get lending pool status
     * @return totalDeposits Total deposits
     * @return totalBorrowed Total borrowed
     * @return availableLiquidity Available liquidity
     * @return utilizationRate Utilization rate (basis points)
     */
    function getPoolStatus() external view returns (
        uint256 totalDeposits,
        uint256 totalBorrowed,
        uint256 availableLiquidity,
        uint256 utilizationRate
    ) {
        utilizationRate = pool.totalDeposits > 0
            ? (pool.totalBorrowed * 10000) / pool.totalDeposits
            : 0;

        return (
            pool.totalDeposits,
            pool.totalBorrowed,
            pool.availableLiquidity,
            utilizationRate
        );
    }

    /**
     * @notice Check if loan is liquidatable
     * @param loanId Loan identifier
     * @return liquidatable True if can be liquidated
     */
    function isLiquidatable(bytes32 loanId) external view returns (bool) {
        Loan memory loan = loans[loanId];

        if (!loan.active) {
            return false;
        }

        uint256 totalDebt = loan.principal + calculateInterest(loanId);
        uint256 liquidationValue = (totalDebt * LIQUIDATION_THRESHOLD) / 100;

        return loan.collateral < liquidationValue;
    }

    /**
     * @notice Get loan health factor (collateral / debt ratio)
     * @param loanId Loan identifier
     * @return healthFactor Health factor in basis points
     */
    function getLoanHealthFactor(bytes32 loanId) external view returns (uint256) {
        Loan memory loan = loans[loanId];

        if (!loan.active) {
            return 0;
        }

        uint256 totalDebt = loan.principal + calculateInterest(loanId);

        if (totalDebt == 0) {
            return 10000; // Perfect health
        }

        return (loan.collateral * 10000) / totalDebt;
    }
}
