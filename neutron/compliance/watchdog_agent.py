"""
Watchdog Agent — Autonomous Security Guardian

Monitors compliance violations and anomalies on the NATS event bus.
When a sandboxed container's Behavior Safety Score drops below 120% (Red Alert),
this agent automatically calls the `liquidate(loanId)` transaction on the
LendingProtocol smart contract, halting execution via BASTION (Landlock LSM)
and claiming the escrow deposit bounty.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
from typing import Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("neutron.watchdog")

NATS_URL = os.environ.get("NATS_URL", "nats://localhost:4222")
WEB3_PROVIDER = os.environ.get("WEB3_PROVIDER_URL", "")
CONTRACT_ADDRESS = os.environ.get(
    "LENDING_PROTOCOL_ADDRESS", "0x5FbDB2315678afecb367f032d93F642f64180aa3"
)
PRIVATE_KEY = os.environ.get("WATCHDOG_PRIVATE_KEY", "")


class WatchdogAgent:
    """Autonomous watchdog agent subscribing to NATS compliance subjects."""

    def __init__(self, nats_url: str = NATS_URL) -> None:
        self.nats_url = nats_url
        self.running = False
        self.w3: Any = None
        self.contract: Any = None

        # Setup Web3 if configured
        if WEB3_PROVIDER and PRIVATE_KEY:
            try:
                from web3 import Web3

                self.w3 = Web3(Web3.HTTPProvider(WEB3_PROVIDER))
                if self.w3.is_connected():
                    logger.info("Connected to Web3 provider: %s", WEB3_PROVIDER)
                    # Minimal ABI for LendingProtocol.liquidate
                    abi = [
                        {
                            "inputs": [
                                {
                                    "internalType": "bytes32",
                                    "name": "loanId",
                                    "type": "bytes32",
                                }
                            ],
                            "name": "liquidate",
                            "outputs": [],
                            "stateMutability": "nonpayable",
                            "type": "function",
                        }
                    ]
                    self.contract = self.w3.eth.contract(
                        address=Web3.to_checksum_address(CONTRACT_ADDRESS),
                        abi=abi,
                    )
                else:
                    logger.warning("Web3 configured but connection failed.")
            except ImportError:
                logger.warning("web3.py not installed. Running in Simulation Mode.")
            except Exception as e:
                logger.error("Web3 setup failed: %s", e)

    async def start(self) -> None:
        """Start NATS subscription loop."""
        import nats
        from nats.errors import ConnectionClosedError, NoServersError, TimeoutError

        self.running = True
        logger.info("Starting Watchdog Agent. Connecting to NATS at %s...", self.nats_url)

        try:
            nc = await nats.connect(self.nats_url)
            logger.info("Watchdog NATS Connected.")

            # Subscribe to both temporal verdicts and direct violations
            subjects = [
                "neotron.compliance.temporal.v1",
                "neotron.compliance.violation.v1",
            ]

            for subj in subjects:
                await nc.subscribe(subj, cb=self.handle_event)
                logger.info("Subscribed to NATS subject: %s", subj)

            while self.running:
                await asyncio.sleep(1)

        except (NoServersError, TimeoutError) as e:
            logger.error("Could not connect to NATS server: %s", e)
        except ConnectionClosedError:
            logger.error("NATS connection closed unexpectedly.")
        except Exception as e:
            logger.critical("Unexpected error in NATS consumer: %s", e)

    async def handle_event(self, msg: Any) -> None:
        """Process captured compliance events."""
        subject = msg.subject
        data = json.loads(msg.data.decode())

        # Extract behavioral risk parameters
        agent_id = data.get("agent_id", "unknown")
        passed = data.get("passed", True)
        reputation = data.get("reputation", 1.0)
        risk_score = data.get("risk_score", 0.0)

        # Calculate behavioral safety score (percentage equivalent)
        safety_score = reputation * 100

        # We trigger container intercept if the safety score is under 120%
        # or if the event is a hard sentinel block (passed = False)
        if not passed or safety_score < 120.0:
            logger.warning(
                "🚨 [THREAT CAPTURED] Subject: %s | Agent ID: %s | Safety Score: %.2f%% | Passed: %s",
                subject,
                agent_id,
                safety_score,
                passed,
            )
            # Create a mock or real loan ID to call liquidate
            # In production, we'd query the agent's active sandbox task mapping to loanId
            loan_id_hex = "0x" + agent_id.encode("utf-8").hex().ljust(64, "0")[:64]
            await self.trigger_containment(loan_id_hex, agent_id, safety_score)

    async def trigger_containment(
        self, loan_id_hex: str, agent_id: str, safety_score: float
    ) -> None:
        """Call liquidate(loanId) to halt process namespace and claim bounty."""
        logger.info("⚡ [CONTAINMENT TRIGGERED] Calling LendingProtocol.liquidate(%s)", loan_id_hex)

        if self.contract and self.w3:
            # On-chain real execution
            try:
                account = self.w3.eth.account.from_key(PRIVATE_KEY)
                tx = self.contract.functions.liquidate(
                    self.w3.to_bytes(hexstr=loan_id_hex)
                ).build_transaction(
                    {
                        "from": account.address,
                        "nonce": self.w3.eth.get_transaction_count(account.address),
                        "gas": 200000,
                        "gasPrice": self.w3.eth.gas_price,
                    }
                )
                signed_tx = self.w3.eth.account.sign_transaction(tx, private_key=PRIVATE_KEY)
                tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
                logger.info("Transaction broadcasted: %s", self.w3.to_hex(tx_hash))

                # Wait for transaction receipt
                receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
                logger.info(
                    "🔒 [CONTAINMENT SUCCESS] Sandbox halted on-chain! Block: %d",
                    receipt.blockNumber,
                )
            except Exception as e:
                logger.error("On-chain liquidation failed: %s", e)
        else:
            # High-fidelity Simulation Mode
            logger.info(
                "🛡️ [SIMULATION] Halting Landlock LSM process namespace for agent '%s'...", agent_id
            )
            await asyncio.sleep(0.5)
            logger.info(
                "💰 [SIMULATION] Seizing security deposit escrow. Containment bounty claimed successfully!"
            )


if __name__ == "__main__":
    agent = WatchdogAgent()
    try:
        asyncio.run(agent.start())
    except KeyboardInterrupt:
        logger.info("Watchdog agent stopped by user.")
