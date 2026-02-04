#!/usr/bin/env bash
set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Paths
NEUTRON_DIR="/home/kernelcore/arch/neutron"
SPECTRE_DIR="/home/kernelcore/arch/spectre"

echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}   🚀 NEOLAND PLATFORM LAUNCHER (MVP)                       ${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"

# 1. Start Infrastructure (Docker)
echo -e "\n${YELLOW}[1/4] Starting Infrastructure (Temporal + Postgres)...${NC}"
cd "$NEUTRON_DIR"
just infra-up

# 2. Start Neutron Worker (The Brain)
echo -e "\n${YELLOW}[2/4] Starting Neutron Worker (Temporal)...${NC}"
# Run in background via nohup/screen logic or simple background job
# Using a new terminal tab would be ideal, but here we run in bg and store PID
cd "$NEUTRON_DIR"
# Ensure dependencies
uv sync
nohup python -m neutron.orchestration.worker > worker.log 2>&1 &
WORKER_PID=$!
echo -e "${GREEN}✅ Neutron Worker started (PID: $WORKER_PID)${NC}"

# 3. Start Neutron API (The Interface)
echo -e "\n${YELLOW}[3/4] Starting Neutron API (FastAPI)...${NC}"
nohup uv run uvicorn neutron.api.server:app --host 0.0.0.0 --port 8000 > api.log 2>&1 &
API_PID=$!
echo -e "${GREEN}✅ Neutron API started (PID: $API_PID) at http://localhost:8000${NC}"

# 4. Start Spectre Proxy (The Shield)
echo -e "\n${YELLOW}[4/4] Starting Spectre Proxy (Rust Gateway)...${NC}"
cd "$SPECTRE_DIR"
# Use Spectre's own Nix environment for building/running
# MVP Secret (In production this comes from cognitive-vault)
export JWT_SECRET="neoland-mvp-secret-key-2026-do-not-use-in-prod"
export RUST_LOG=info

nix develop --command cargo build --bin spectre-proxy --release
nohup nix develop --command cargo run --bin spectre-proxy --release > proxy.log 2>&1 &
PROXY_PID=$!
echo -e "${GREEN}✅ Spectre Proxy started (PID: $PROXY_PID) at http://localhost:3000${NC}"

# 5. Wait / Cleanup
echo -e "\n${BLUE}════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}🎉 PLATFORM ONLINE!${NC}"
echo -e "   - Neutron API: http://localhost:8000/docs"
echo -e "   - Temporal UI: http://localhost:8088"
echo -e "   - MLflow UI:   http://localhost:5001"
echo -e "   - Spectre Proxy: http://localhost:3000"
echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}Press Ctrl+C to stop all services...${NC}"

cleanup() {
    echo -e "\n${RED}🛑 Stopping services...${NC}"
    kill $WORKER_PID 2>/dev/null || true
    kill $API_PID 2>/dev/null || true
    kill $PROXY_PID 2>/dev/null || true
    
    echo -e "${YELLOW}Stopping infrastructure...${NC}"
    cd "$NEUTRON_DIR"
    just infra-down
    echo -e "${GREEN}✅ Shutdown complete.${NC}"
    exit 0
}

trap cleanup SIGINT

# Keep script running
wait
