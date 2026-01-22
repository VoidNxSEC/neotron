// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {Script, console2} from "forge-std/Script.sol";
import {LendingProtocol} from "../src/LendingProtocol.sol";

/**
 * @title Deploy Script
 * @notice Foundry deployment script for NEXUS BASTION-SC contracts
 * @dev Deploys LendingProtocol (which includes LGPDConsent and AuditLogger)
 *
 * Usage:
 *   Local (Anvil):
 *     forge script script/Deploy.s.sol:DeployScript --fork-url http://localhost:8545 --broadcast
 *
 *   Sepolia Testnet:
 *     forge script script/Deploy.s.sol:DeployScript --rpc-url $SEPOLIA_RPC_URL --broadcast --verify -vvvv
 *
 *   Mainnet (DANGER):
 *     forge script script/Deploy.s.sol:DeployScript --rpc-url $MAINNET_RPC_URL --broadcast --verify -vvvv
 */
contract DeployScript is Script {
    // Deployment configuration
    string public constant DEPLOYMENT_NAME = "NEXUS BASTION-SC v1.0.0";

    // Deployed contract addresses (populated after deployment)
    LendingProtocol public lendingProtocol;

    function run() external {
        // Get deployer private key from environment
        uint256 deployerPrivateKey = vm.envUint("PRIVATE_KEY");
        address deployer = vm.addr(deployerPrivateKey);

        console2.log("========================================");
        console2.log("NEXUS BASTION-SC Deployment");
        console2.log("========================================");
        console2.log("Deployer:", deployer);
        console2.log("Deployer balance:", deployer.balance / 1e18, "ETH");
        console2.log("Chain ID:", block.chainid);
        console2.log("========================================");

        // Check deployer has sufficient balance
        require(deployer.balance > 0.01 ether, "Insufficient balance for deployment");

        // Start broadcasting transactions
        vm.startBroadcast(deployerPrivateKey);

        // Deploy LendingProtocol (includes LGPDConsent and AuditLogger via inheritance)
        console2.log("\nDeploying LendingProtocol...");
        lendingProtocol = new LendingProtocol();

        console2.log("LendingProtocol deployed at:", address(lendingProtocol));

        // Verify deployment
        console2.log("\nVerifying deployment...");
        verifyDeployment();

        // Log contract addresses for verification
        console2.log("\n========================================");
        console2.log("Deployment Complete!");
        console2.log("========================================");
        console2.log("LendingProtocol:", address(lendingProtocol));
        console2.log("\nContract info:");
        console2.log("- Collateral Ratio:", lendingProtocol.COLLATERAL_RATIO(), "%");
        console2.log("- Interest Rate:", lendingProtocol.INTEREST_RATE(), "bps (basis points)");
        console2.log("- Liquidation Threshold:", lendingProtocol.LIQUIDATION_THRESHOLD(), "%");
        console2.log("\nNext steps:");
        console2.log("1. Verify contracts on Etherscan:");
        console2.log("   forge verify-contract <address> LendingProtocol --chain-id", block.chainid);
        console2.log("2. Save deployment addresses to deployments.json");
        console2.log("3. Test end-to-end workflow");
        console2.log("========================================");

        vm.stopBroadcast();

        // Write deployment addresses to file
        writeDeploymentFile();
    }

    /**
     * @notice Verify deployment was successful
     */
    function verifyDeployment() internal view {
        // Check LendingProtocol
        require(address(lendingProtocol) != address(0), "LendingProtocol deployment failed");
        require(lendingProtocol.COLLATERAL_RATIO() == 150, "Invalid collateral ratio");
        require(lendingProtocol.INTEREST_RATE() == 500, "Invalid interest rate");
        require(lendingProtocol.LIQUIDATION_THRESHOLD() == 120, "Invalid liquidation threshold");

        console2.log("✓ LendingProtocol deployment verified");
    }

    /**
     * @notice Write deployment addresses to JSON file
     */
    function writeDeploymentFile() internal {
        string memory chainName = getChainName(block.chainid);

        // Create JSON output
        string memory json = string.concat(
            "{\n",
            '  "network": "', chainName, '",\n',
            '  "chainId": ', vm.toString(block.chainid), ',\n',
            '  "timestamp": ', vm.toString(block.timestamp), ',\n',
            '  "deployer": "', vm.toString(msg.sender), '",\n',
            '  "contracts": {\n',
            '    "LendingProtocol": "', vm.toString(address(lendingProtocol)), '"\n',
            '  },\n',
            '  "config": {\n',
            '    "collateralRatio": ', vm.toString(lendingProtocol.COLLATERAL_RATIO()), ',\n',
            '    "interestRate": ', vm.toString(lendingProtocol.INTEREST_RATE()), ',\n',
            '    "liquidationThreshold": ', vm.toString(lendingProtocol.LIQUIDATION_THRESHOLD()), '\n',
            '  }\n',
            '}'
        );

        // Write to file
        string memory filename = string.concat("deployments/", chainName, ".json");
        vm.writeFile(filename, json);

        console2.log("\nDeployment info written to:", filename);
    }

    /**
     * @notice Get human-readable chain name
     */
    function getChainName(uint256 chainId) internal pure returns (string memory) {
        if (chainId == 1) return "mainnet";
        if (chainId == 11155111) return "sepolia";
        if (chainId == 31337) return "localhost";
        return vm.toString(chainId);
    }
}
