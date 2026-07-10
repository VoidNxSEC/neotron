# Blockchain Secrets Setup Guide

## 🔐 Configuração de Secrets com sops-nix

Este guia mostra como configurar secrets blockchain (private keys, API keys) usando sops-nix de forma segura.

---

## Passo 1: Execute o Script de Setup

```bash
cd /home/kernelcore
chmod +x setup-blockchain-secrets.sh
./setup-blockchain-secrets.sh
```

Este script irá:
1. ✅ Copiar secrets encriptados para `/etc/nixos/secrets/blockchain.yaml`
2. ✅ Verificar que a encriptação está funcionando
3. ✅ **DELETAR arquivos não encriptados** (`.env`, `blockchain-secrets.yaml`)
4. ✅ Atualizar `.gitignore`

---

## Passo 2: Adicione o Módulo Blockchain à Configuração NixOS

### Opção A: Se você usa `/etc/nixos/configuration.nix`

Adicione ao seu `configuration.nix`:

```nix
{ config, pkgs, ... }:

{
  imports = [
    ./hardware-configuration.nix
    ./blockchain.nix  # <-- Adicione esta linha
  ];

  # ... resto da configuração
}
```

### Opção B: Se você usa Flake

Adicione ao seu `flake.nix` nos módulos do sistema:

```nix
nixosConfigurations.kernelcore = nixpkgs.lib.nixosSystem {
  inherit system;
  modules = [
    ./configuration.nix
    ./blockchain.nix  # <-- Adicione esta linha
    sops-nix.nixosModules.sops
  ];
};
```

---

## Passo 3: Copie o Módulo para /etc/nixos/

```bash
sudo cp /home/kernelcore/blockchain-module.nix /etc/nixos/blockchain.nix
sudo chown root:root /etc/nixos/blockchain.nix
sudo chmod 644 /etc/nixos/blockchain.nix
```

---

## Passo 4: Rebuild do Sistema

```bash
sudo nixos-rebuild switch --flake /etc/nixos#kernelcore --max-jobs 8 --cores 8
```

---

## ✅ Secrets Configurados!

Após o rebuild, os secrets estarão disponíveis em:

- `/run/secrets/ethereum/private_key`
- `/run/secrets/rpc/sepolia_url`
- `/run/secrets/rpc/mainnet_url`
- `/run/secrets/rpc/alchemy_key`
- `/run/secrets/etherscan/api_key`
- `/run/secrets/ipfs/project_id`
- `/run/secrets/ipfs/project_secret`

---

## 🔧 Como Usar os Secrets

### Método 1: Comandos Wrapper (Recomendado)

Use os comandos que carregam secrets automaticamente:

```bash
# Deploy com secrets carregados automaticamente
cd /home/kernelcore/arch/neutron/contracts
forge-with-secrets script script/Deploy.s.sol:DeployScript --broadcast --slow

# Verificar saldo com cast
cast-with-secrets balance 0x017d2F22c2Ac860b775Ad6e9c1E3C1945ac69BE7 --rpc-url $SEPOLIA_RPC_URL
```

### Método 2: Exportar para .env (Desenvolvimento)

Para desenvolvimento local, você pode exportar temporariamente:

```bash
cd /home/kernelcore/arch/neutron/contracts
blockchain-export-env .

# Agora use normalmente
source .env
nix develop --command forge test
```

⚠️ **IMPORTANTE**: O arquivo `.env` gerado deve ser deletado após uso e NUNCA commitado!

### Método 3: Carregar Manualmente

```bash
export PRIVATE_KEY=$(cat /run/secrets/ethereum/private_key)
export SEPOLIA_RPC_URL=$(cat /run/secrets/rpc/sepolia_url)

# Use os comandos normalmente
forge script script/Deploy.s.sol:DeployScript --broadcast
```

---

## 🔍 Verificar que Secrets Estão Funcionando

```bash
# Verificar que os arquivos de secret existem
ls -la /run/secrets/ethereum/
ls -la /run/secrets/rpc/

# Ver conteúdo (deve mostrar os valores decriptados)
cat /run/secrets/ethereum/private_key

# Verificar permissões (deve ser 0400 - read-only para owner)
stat /run/secrets/ethereum/private_key
```

---

## 📊 Estrutura de Secrets

```
/etc/nixos/secrets/blockchain.yaml  (encriptado com sops)
├── ethereum/
│   ├── private_key          (0x91a2db...)
│   └── deployer_address     (0x017d2F...)
├── rpc/
│   ├── sepolia_url          (https://eth-sepolia.g.alchemy.com/...)
│   ├── mainnet_url          (https://eth-mainnet.g.alchemy.com/...)
│   └── alchemy_key          (J4GsUMyvTR8Sy4FOVjc0f)
├── etherscan/
│   └── api_key              (vazio por enquanto)
├── ipfs/
│   ├── api_url              (https://ipfs.infura.io:5001)
│   ├── project_id           (YOUR_INFURA_PROJECT_ID)
│   └── project_secret       (YOUR_INFURA_PROJECT_SECRET)
└── deployed_contracts/
    └── sepolia/
        └── lending_protocol (0x35fF603BD286E287f932356316271D59a4ADa779)
```

---

## 🔐 Segurança

### ✅ O que está protegido:
- Private keys encriptadas com age
- API keys protegidas por sops
- Secrets só acessíveis por root e kernelcore
- Arquivos não encriptados deletados automaticamente

### ⚠️ O que você deve fazer:
- NUNCA commitar `.env` no git
- NUNCA compartilhar `/run/secrets/*` com ninguém
- SEMPRE usar `blockchain-export-env` em vez de criar `.env` manualmente
- SEMPRE deletar `.env` após uso em desenvolvimento

### 🔄 Rotação de Secrets:

Para trocar a private key ou API keys:

```bash
# 1. Editar secrets encriptados
sudo sops /etc/nixos/secrets/blockchain.yaml

# 2. Rebuild do sistema
sudo nixos-rebuild switch --flake /etc/nixos#kernelcore --max-jobs 8 --cores 8
```

---

## 📝 Informações de Deployment

Deployment info (não sensível) disponível em:
```bash
cat /etc/blockchain/deployment-info.json
```

Mostra:
- Network: Sepolia
- Chain ID: 11155111
- Contrato deployado: 0x35fF603BD286E287f932356316271D59a4ADa779
- Etherscan link

---

## 🚨 Troubleshooting

### "Permission denied" ao acessar /run/secrets/

Os secrets são criados no boot e pertencem ao usuário configurado. Verifique:
```bash
ls -la /run/secrets/ethereum/
# Deve mostrar: kernelcore kernelcore
```

### "No such file or directory" em /run/secrets/

Execute o rebuild:
```bash
sudo nixos-rebuild switch --flake /etc/nixos#kernelcore --max-jobs 8 --cores 8
```

### Secrets não são decriptados

Verifique se as age keys estão corretas:
```bash
sudo sops --decrypt /etc/nixos/secrets/blockchain.yaml | head
```

---

## ✨ Próximos Passos

Após configurar os secrets:

1. ✅ Testar deployment com `forge-with-secrets`
2. ✅ Verificar que `.env` não existe mais no repo
3. ✅ Commit da configuração NixOS (sem secrets!)
4. ✅ Week 21: Build frontend Web3

---

**Criado em**: 2026-01-22
**Versão**: 1.0.0
**Parte de**: NEXUS BASTION-SC (Week 20)
