# Relatório de Recuperação Operacional
**Data:** 26 de Janeiro de 2026
**Status:** Funcional (Com Alertas)

## 1. Procedimento de Inicialização Validado

Para levantar o ambiente sem erros, siga estritamente esta ordem em terminais separados:

### Terminal 1: Backend & Infraestrutura
```bash
# 1. Entrar no ambiente hermético
nix develop

# 2. Instalar dependências (Ignorar warning do lock file)
just install

# 3. Subir Banco de Dados e Temporal
just infra-up

# 4. Iniciar Worker (Necessário para workflows)
just worker-bg
```

### Terminal 2: Frontend
```bash
# 1. Entrar no ambiente
nix develop

# 2. Navegar para o diretório
cd frontend

# 3. Iniciar servidor
pnpm dev
```
> **Nota:** O Frontend iniciou na porta **http://localhost:3002** pois a 3000 estava em uso.

## 2. Pontos de Atenção (Issues Identificadas)

### A. Backend: Erro no Poetry Lock
O comando `poetry lock` falha com:
```text
Repository "pytorch-cu121" does not exist.
```
**Impacto:** Não é possível adicionar novas libs Python sem corrigir o `pyproject.toml` para apontar para o repositório correto do PyTorch ou usar a fonte padrão.
**Estado Atual:** As dependências atuais funcionam, mas o ambiente está "congelado".

### B. Frontend: Warnings de SSR
Logs apresentam erros de `ReferenceError: indexedDB is not defined` e `Module not found: Can't resolve '@react-native-async-storage/async-storage'`.
**Impacto:** Warnings de build relacionados ao suporte a Mobile/Metamask SDK no Server-Side Rendering (Next.js).
**Estado Atual:** Não bloqueante. A aplicação carrega e responde (`GET / 200`).

## 3. Próximos Passos Recomendados
1. Investigar processo rodando na porta 3000 (`lsof -i :3000`).
2. Corrigir URL do repositório PyTorch no `pyproject.toml`.
3. Adicionar tratativa `NoSSR` para componentes do RainbowKit/Wagmi.
