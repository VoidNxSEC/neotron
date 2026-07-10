// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 VoidNXLabs
pragma solidity ^0.8.20;

import {Script, console2} from "forge-std/Script.sol";
import {AgentRewardToken} from "../src/dao/AgentRewardToken.sol";
import {IntelAgentDAO} from "../src/dao/IntelAgentDAO.sol";
import {AuditLogger} from "../src/AuditLogger.sol";

/// @notice Deploy AgentRewardToken + AuditLogger + IntelAgentDAO, wire ownership.
contract DeployDAO is Script {
    AgentRewardToken public token;
    AuditLogger      public logger;
    IntelAgentDAO    public dao;

    function run() external {
        uint256 deployerKey = vm.envUint("PRIVATE_KEY");
        address deployer    = vm.addr(deployerKey);

        console2.log("=== IntelAgent DAO Deployment ===");
        console2.log("Deployer:", deployer);
        console2.log("Chain ID:", block.chainid);

        vm.startBroadcast(deployerKey);

        token  = new AgentRewardToken();
        logger = new AuditLogger();
        dao    = new IntelAgentDAO(address(token), address(logger));

        // Transfer token ownership to DAO — only DAO can mint/slash
        token.transferOwnership(address(dao));

        console2.log("AgentRewardToken:", address(token));
        console2.log("AuditLogger:     ", address(logger));
        console2.log("IntelAgentDAO:   ", address(dao));

        vm.stopBroadcast();

        _write();
        console2.log("=== Deployment Complete ===");
    }

    function _write() internal {
        string memory net  = block.chainid == 31337 ? "localhost" : vm.toString(block.chainid);
        string memory json = string.concat(
            "{\n",
            '  "network": "', net, '",\n',
            '  "chainId": ', vm.toString(block.chainid), ",\n",
            '  "AgentRewardToken": "', vm.toString(address(token)), '",\n',
            '  "AuditLogger": "',      vm.toString(address(logger)), '",\n',
            '  "IntelAgentDAO": "',    vm.toString(address(dao)), '"\n',
            "}"
        );
        vm.writeFile(string.concat("deployments/dao-", net, ".json"), json);
    }
}
