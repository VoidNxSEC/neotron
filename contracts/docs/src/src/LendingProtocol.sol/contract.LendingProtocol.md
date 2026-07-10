# LendingProtocol
**Inherits:**
[LGPDConsent](/src/LGPDConsent.sol/contract.LGPDConsent.md), [AuditLogger](/src/AuditLogger.sol/contract.AuditLogger.md)

**Title:**
LendingProtocol

**Author:**
NEXUS Platform

DeFi lending protocol with FULL compliance enforcement (4 layers)

First-ever DeFi protocol with kernel-level compliance integration
Defense-in-Depth Compliance (ALL 4 LAYERS):
┌────────────────────────────────────────────────────────────┐
│  Layer 1: SENTINEL (Application - Python validation)      │
│  Layer 2: BASTION (Kernel - seccomp-BPF syscalls)         │
│  Layer 3: BASTION-SC (Smart Contract - this contract)     │
│  Layer 4: Audit Trail (IPFS + Arweave via AuditLogger)    │
└────────────────────────────────────────────────────────────┘
Features:
- Borrow/lend with LGPD Article 7 consent enforcement
- Collateralized loans (150% collateral ratio)
- Interest accrual (5% APY)
- Liquidation mechanism
- Complete audit trail (on-chain + IPFS/Arweave)
- Compliance violations → automatic revert


## State Variables
### COLLATERAL_RATIO
Minimum collateral ratio (150%)


```solidity
uint256 public constant COLLATERAL_RATIO = 150
```


### INTEREST_RATE
Annual interest rate (5%)


```solidity
uint256 public constant INTEREST_RATE = 500
```


### LIQUIDATION_THRESHOLD
Liquidation threshold (120%)


```solidity
uint256 public constant LIQUIDATION_THRESHOLD = 120
```


### loans
Mapping: loanId => Loan


```solidity
mapping(bytes32 => Loan) public loans
```


### borrowerLoans
Mapping: borrower => loanIds[]


```solidity
mapping(address => bytes32[]) public borrowerLoans
```


### pool
Lending pool state


```solidity
LendingPool public pool
```


### totalLoans
Total loans created


```solidity
uint256 public totalLoans
```


## Functions
### deposit

Deposit funds into lending pool

Anyone can deposit to earn interest from borrowers


```solidity
function deposit() external payable;
```

### withdraw

Withdraw funds from lending pool


```solidity
function withdraw(uint256 amount) external;
```
**Parameters**

|Name|Type|Description|
|----|----|-----------|
|`amount`|`uint256`|Amount to withdraw|


### applyForLoan

Apply for loan (requires LGPD Article 7 consent)

COMPLIANCE ENFORCED: Automatic revert if no consent granted


```solidity
function applyForLoan(uint256 amount)
    external
    payable
    lgpdArticle7Consent(msg.sender) // ← COMPLIANCE LAYER 3: Smart contract enforcement
    returns (bytes32 loanId);
```
**Parameters**

|Name|Type|Description|
|----|----|-----------|
|`amount`|`uint256`|Amount to borrow|

**Returns**

|Name|Type|Description|
|----|----|-----------|
|`loanId`|`bytes32`|Unique loan identifier|


### repayLoan

Repay loan with interest


```solidity
function repayLoan(bytes32 loanId) external payable;
```
**Parameters**

|Name|Type|Description|
|----|----|-----------|
|`loanId`|`bytes32`|Loan identifier|


### liquidate

Liquidate undercollateralized loan


```solidity
function liquidate(bytes32 loanId) external;
```
**Parameters**

|Name|Type|Description|
|----|----|-----------|
|`loanId`|`bytes32`|Loan identifier|


### calculateInterest

Calculate accrued interest for a loan


```solidity
function calculateInterest(bytes32 loanId) public view returns (uint256);
```
**Parameters**

|Name|Type|Description|
|----|----|-----------|
|`loanId`|`bytes32`|Loan identifier|

**Returns**

|Name|Type|Description|
|----|----|-----------|
|`<none>`|`uint256`|interest Interest accrued|


### getLoan

Get loan details


```solidity
function getLoan(bytes32 loanId) external view returns (Loan memory);
```
**Parameters**

|Name|Type|Description|
|----|----|-----------|
|`loanId`|`bytes32`|Loan identifier|

**Returns**

|Name|Type|Description|
|----|----|-----------|
|`<none>`|`Loan`|loan Loan struct|


### getBorrowerLoans

Get all loans for a borrower


```solidity
function getBorrowerLoans(address borrower) external view returns (bytes32[] memory);
```
**Parameters**

|Name|Type|Description|
|----|----|-----------|
|`borrower`|`address`|Borrower address|

**Returns**

|Name|Type|Description|
|----|----|-----------|
|`<none>`|`bytes32[]`|loanIds Array of loan IDs|


### getPoolStatus

Get lending pool status


```solidity
function getPoolStatus()
    external
    view
    returns (uint256 totalDeposits, uint256 totalBorrowed, uint256 availableLiquidity, uint256 utilizationRate);
```
**Returns**

|Name|Type|Description|
|----|----|-----------|
|`totalDeposits`|`uint256`|Total deposits|
|`totalBorrowed`|`uint256`|Total borrowed|
|`availableLiquidity`|`uint256`|Available liquidity|
|`utilizationRate`|`uint256`|Utilization rate (basis points)|


### isLiquidatable

Check if loan is liquidatable


```solidity
function isLiquidatable(bytes32 loanId) external view returns (bool);
```
**Parameters**

|Name|Type|Description|
|----|----|-----------|
|`loanId`|`bytes32`|Loan identifier|

**Returns**

|Name|Type|Description|
|----|----|-----------|
|`<none>`|`bool`|liquidatable True if can be liquidated|


### getLoanHealthFactor

Get loan health factor (collateral / debt ratio)


```solidity
function getLoanHealthFactor(bytes32 loanId) external view returns (uint256);
```
**Parameters**

|Name|Type|Description|
|----|----|-----------|
|`loanId`|`bytes32`|Loan identifier|

**Returns**

|Name|Type|Description|
|----|----|-----------|
|`<none>`|`uint256`|healthFactor Health factor in basis points|


## Events
### Deposited

```solidity
event Deposited(address indexed lender, uint256 amount, uint256 timestamp);
```

### LoanRequested

```solidity
event LoanRequested(
    bytes32 indexed loanId, address indexed borrower, uint256 principal, uint256 collateral, uint256 timestamp
);
```

### LoanApproved

```solidity
event LoanApproved(bytes32 indexed loanId, address indexed borrower, uint256 amount, uint256 timestamp);
```

### LoanRepaid

```solidity
event LoanRepaid(
    bytes32 indexed loanId, address indexed borrower, uint256 principal, uint256 interest, uint256 timestamp
);
```

### LoanLiquidated

```solidity
event LoanLiquidated(
    bytes32 indexed loanId,
    address indexed borrower,
    address indexed liquidator,
    uint256 collateralSeized,
    uint256 timestamp
);
```

### Withdrawn

```solidity
event Withdrawn(address indexed lender, uint256 amount, uint256 timestamp);
```

## Errors
### InsufficientLiquidity

```solidity
error InsufficientLiquidity(uint256 requested, uint256 available);
```

### InsufficientCollateral

```solidity
error InsufficientCollateral(uint256 provided, uint256 required);
```

### LoanNotFound

```solidity
error LoanNotFound(bytes32 loanId);
```

### LoanNotActive

```solidity
error LoanNotActive(bytes32 loanId);
```

### UnauthorizedRepayment

```solidity
error UnauthorizedRepayment(bytes32 loanId, address caller);
```

### LoanNotLiquidatable

```solidity
error LoanNotLiquidatable(bytes32 loanId);
```

### InsufficientBalance

```solidity
error InsufficientBalance(uint256 balance, uint256 requested);
```

## Structs
### Loan

```solidity
struct Loan {
    address borrower;
    uint256 principal; // Amount borrowed
    uint256 collateral; // ETH collateral
    uint256 interestRate; // Basis points (500 = 5%)
    uint256 borrowedAt; // Timestamp
    uint256 lastAccrualTime; // Last interest calculation
    uint256 accruedInterest; // Interest accrued
    bool active;
    bool liquidated;
}
```

### LendingPool

```solidity
struct LendingPool {
    uint256 totalDeposits;
    uint256 totalBorrowed;
    uint256 availableLiquidity;
}
```

