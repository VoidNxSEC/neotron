════════════════════════════════════════════════════════════
  🚀 Neutron ML Pipeline Dev Environment (uv)
════════════════════════════════════════════════════════════

📦 Python Environment:
  Python: Python 3.13.11
  uv: uv 0.9.26
  CUDA: 12.8

⛓️  Blockchain Development:
  Foundry: forge Version: 1.5.1-dev
  IPFS: ipfs version 0.39.0
  Commands: forge, cast, anvil, chisel, ipfs

📦 Available commands:
  just --list         # List all tasks
  uv sync             # Install dependencies
  uv run <cmd>        # Run command in venv
  forge test          # Run smart contract tests

🌐 Services (after 'just infra-up'):
  Temporal UI: http://localhost:8088
  MLflow UI:   http://localhost:5000
  Ray Dashboard: http://localhost:8265

✅ Environment ready!
════════════════════════════════════════════════════════════
🤖 Neutron Compliance Agent (Self-Audit Mode)
---------------------------------------------

📨 Broadcasting Audit Task to Swarm...

📊 Audit Results:
  [SecurityAuditor] Verdict: Processed by SecurityAuditor
  [NixCompliance] Verdict: Processed by NixCompliance
  [ArchitectureReview] Verdict: Processed by ArchitectureReview

🏆 Final Consensus: Processed by SecurityAuditor
