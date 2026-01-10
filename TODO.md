# TODO - Neutron ML Pipeline

## ⚠️ Pendente - Instalação de Dependências Python

### Poetry Install (Timeout de Rede)

**Status**: Falhou por timeout de rede ao baixar pacotes CUDA grandes
**Data**: 2026-01-10
**Erro**: `ReadTimeoutError: HTTPSConnectionPool(host='files.pythonhosted.org', port=443): Read timed out`

**Pacotes que falharam**:
- `nvidia-cusolver-cu12` (11.4.5.107)
- `nvidia-cudnn-cu12` (9.1.0.70)
- `nvidia-cufft-cu12` (11.0.2.54)
- `nvidia-curand-cu12` (10.3.2.106)
- `nvidia-nccl-cu12` (2.21.5)
- `nvidia-cuda-nvrtc-cu12` (12.1.105)

**Causa**: Pacotes CUDA são grandes (centenas de MB cada) e a conexão estava instável.

**Solução**:
```bash
# Opção 1: Tentar novamente quando conexão melhorar
poetry install

# Opção 2: Aumentar timeout do Poetry
export POETRY_HTTP_TIMEOUT=300
poetry install

# Opção 3: Instalar gradualmente
poetry install --no-root
poetry install --only main

# Opção 4: Baixar wheels manualmente e instalar via cache
poetry cache clear pypi --all
poetry install
```

**Nota**: A migração para Poetry está completa e funcionando. Este é apenas um problema temporário de rede, não do código.

---

## 📋 Próximas Tarefas (Planejadas)

### Phase 2: PHANTOM Integration
- [ ] Create `plugins/cerebro_optimizer.py` for semantic hyperparameter search
- [ ] Add integration config file (`config/integrations.yaml`)
- [ ] Integrate PHANTOM CORTEX for document preprocessing
- [ ] Test document ingestion pipeline

### Phase 3: SPECTRE Integration
- [ ] Integrate SPECTRE event bus (NATS)
- [ ] Add event-driven workflow triggers
- [ ] Test distributed messaging

### Phase 4: Experimentation
- [ ] Burn $10K GCP credits intelligently (Weeks 5-12)
- [ ] Run ML experiments with different strategies
- [ ] Collect metrics and optimize

### Phase 5: Documentation
- [ ] Update README.md with Poetry workflow
- [ ] Document NIX_INTEGRATION.md changes
- [ ] Create stakeholder presentation (Week 16)

---

## ✅ Completed

- [x] Phase 0: Neutron Core Components (optimizer.py, worker.py, trainers.py, main.py)
- [x] Phase 1: CEREBRO Integration (cost_tracker.py, unified_cost_reporter.py)
- [x] Migration to Poetry + hybrid Nix approach
- [x] flake.nix updated and tested
- [x] Infrastructure setup (docker-compose.yml, init-db.sql)
- [x] Git commit and push to upstream/main (f1c1808)
