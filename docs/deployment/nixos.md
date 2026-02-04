# Neutron NixOS Deployment Guide

## Overview

Neutron is designed to be deployed as a first-class NixOS service. The module `services.neutron-ml-pipeline` exposes configuration for:
- **Orchestration**: Temporal Server & Worker
- **Tracking**: MLflow
- **Agents**: Cortex (Swarm) & Synapse (Memory)
- **Secrets**: Encrypted via sops-nix

## Configuration Reference

Add the following to your `configuration.nix` or `flake.nix`:

```nix
{ config, pkgs, ... }: {
  
  # Enable the service
  services.neutron-ml-pipeline = {
    enable = true;
    user = "neutron";
    
    # 1. Orchestration (Temporal)
    temporal = {
      enable = true;
      port = 7233;
    };

    # 2. Tracking (MLflow)
    mlflow = {
      enable = true;
      backendStore = "postgresql://neutron:neutron@localhost:5432/mlflow";
      artifactRoot = "s3://neutron-artifacts"; # Or local path
    };

    # 3. Agent Configuration (NEW)
    agents = {
      cortex = {
        enable = true;
        consensusStrategy = "weighted_confidence"; # Options: majority_vote, unanimous
      };
      synapse = {
        enable = true;
        vectorStore = "pgvector";
      };
    };

    # 4. Secrets Management (Recommended)
    secrets = {
      sopsFile = ./secrets/neutron.yaml; # Encrypted with sops-nix
      openaiApiKeyFile = "/run/secrets/openai_api_key";
    };

    # 5. Worker Configuration
    worker = {
      enable = true;
      instances = 3;    # Scalable worker pool
      maxGPUs = 1;      # Resource isolation
    };
  };

  # Infra dependencies
  services.postgresql.enable = true;
}
```

## Secrets Setup (Sops-Nix)

Neutron expects API keys to be available as files (for systemd `LoadCredential` or simple file read).

1. **Create secrets.yaml**:
   ```yaml
   openai_api_key: "sk-..."
   anthropic_api_key: "sk-ant-..."
   ```

2. **Encrypt**:
   ```bash
   sops -e secrets.yaml > secrets.enc.yaml
   ```

3. **Configure Sops-Nix**:
   ```nix
   sops.secrets.openai_api_key = {
     sopsFile = ./secrets.enc.yaml;
     owner = "neutron";
   };
   ```

## Verification

After `nixos-rebuild switch`:

1. **Check Status**:
   ```bash
   systemctl status neutron-worker@1.service
   systemctl status mlflow.service
   ```

2. **View Logs**:
   ```bash
   journalctl -u neutron-worker@* -f
   ```

3. **Validate Agents**:
   The worker initializes `AgentSwarm` on startup. Check logs for:
   `[neutron.worker] Activity: run_agent_swarm received task...`
