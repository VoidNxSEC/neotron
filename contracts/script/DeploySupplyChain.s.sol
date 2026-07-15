// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 VoidNXLabs
pragma solidity ^0.8.20;

import {Script, console2} from "forge-std/Script.sol";
import {SupplyChainGuardian} from "../src/supplychain/SupplyChainGuardian.sol";

/// @title DeploySupplyChain
/// @notice Deploys SupplyChainGuardian (which internally instantiates SBOM + BuildAttestation + LicenseRegistry)
contract DeploySupplyChain is Script {
    SupplyChainGuardian public guardian;

    function run() external {
        uint256 deployerKey = vm.envUint("PRIVATE_KEY");
        address deployer = vm.addr(deployerKey);

        console2.log("=== Supply Chain Deployment ===");
        console2.log("Deployer:", deployer);
        console2.log("Chain ID:", block.chainid);

        vm.startBroadcast(deployerKey);

        // Guardian deploys SBOM + BuildAttestation + LicenseRegistry internally
        guardian = new SupplyChainGuardian();
        console2.log("SupplyChainGuardian:   ", address(guardian));
        console2.log("  SBOMRegistry:        ", address(guardian.sbomRegistry()));
        console2.log("  BuildAttestation:    ", address(guardian.buildAttestation()));
        console2.log("  LicenseRegistry:     ", address(guardian.licenseRegistry()));

        vm.stopBroadcast();

        _writeDeployment();
        console2.log("=== Deployment Complete ===");
    }

    function _writeDeployment() internal {
        string memory net = block.chainid == 31337 ? "localhost" : vm.toString(block.chainid);
        string memory json = string.concat(
            "{\n",
            '  "network": "', net, '",\n',
            '  "chainId": ', vm.toString(block.chainid), ",\n",
            '  "SupplyChainGuardian": "', vm.toString(address(guardian)), '",\n',
            '  "SBOMRegistry": "', vm.toString(address(guardian.sbomRegistry())), '",\n',
            '  "BuildAttestation": "', vm.toString(address(guardian.buildAttestation())), '",\n',
            '  "LicenseRegistry": "', vm.toString(address(guardian.licenseRegistry())), '"\n',
            "}"
        );
        vm.writeFile(string.concat("deployments/supply-chain-", net, ".json"), json);
    }
}
