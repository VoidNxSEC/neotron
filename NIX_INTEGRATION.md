# Nix Integration Guide
**Integração declarativa total com teu nix fort knox**

## 🎯 Filosofia da Integração

Você já tem 129 módulos organizados em 12 categorias. Este pipeline se encaixa como mais um módulo composable:

```
your-nixos-config/
├── modules/
│   ├── security/      (teus 129 módulos)
│   ├── networking/
│   ├── services/
│   └── ml-pipeline/   ← Este módulo novo
│       ├── default.nix
│       ├── worker.nix
│       ├── monitoring.nix
│       └── cost-tracking.nix
```

## 🚀 Quick Start

### 1. Add Flake Input

No teu `flake.nix` principal:

```nix
{
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    
    # Teus outros inputs...
    # home-manager.url = ...
    # agenix.url = ...
    
    # ML Pipeline
    adaptive-ml-pipeline = {
      url = "path:/path/to/adaptive_ml_pipeline";
      # ou: url = "github:user/adaptive-ml-pipeline";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs = { self, nixpkgs, adaptive-ml-pipeline, ... }: {
    nixosConfigurations.your-host = nixpkgs.lib.nixosSystem {
      modules = [
        ./configuration.nix
        adaptive-ml-pipeline.nixosModules.default
        # Teus outros módulos...
      ];
    };
  };
}
```

### 2. Enable Service

No teu `configuration.nix` ou módulo dedicado:

```nix
{ config, ... }: {
  services.adaptive-ml-pipeline = {
    enable = true;
    
    # Minimal config
    worker.instances = 2;
    worker.maxGPUs = 1;
    
    # Cost tracking
    costTracking = {
      enable = true;
      gpuCostPerHour = 0.90;  # Oracle Cloud GPU pricing
    };
  };
}
```

### 3. Rebuild

```bash
sudo nixos-rebuild switch --flake .#your-host
```

Done. Workers rodando como systemd services, MLflow tracking, cost monitoring automático.

## 🏗️ Deployment Patterns

### Pattern 1: Development Workstation

```nix
{ config, pkgs, ... }: {
  services.adaptive-ml-pipeline = {
    enable = true;
    
    # Local development
    postgresql.enable = true;  # Local DB
    mlflow.enable = true;
    
    worker = {
      enable = true;
      instances = 1;
      maxGPUs = 1;  # Tua RTX local
    };
    
    costTracking.enable = false;  # Desnecessário em dev
  };
  
  # Dev tools
  environment.systemPackages = with pkgs; [
    just
    (writeShellScriptBin "ml-dev" ''
      cd /path/to/project
      nix develop .#cuda
    '')
  ];
}
```

### Pattern 2: Production Server (Single Node)

```nix
{ config, pkgs, ... }: {
  services.adaptive-ml-pipeline = {
    enable = true;
    user = "ml-pipeline";
    dataDir = "/data/ml-pipeline";  # SSD mount
    
    postgresql.enable = true;
    
    mlflow = {
      enable = true;
      port = 5000;
      # S3 backend pra artifacts
      artifactRoot = "s3://my-bucket/mlflow-artifacts";
      backendStore = "postgresql://mlflow:${mlflowPassword}@localhost/mlflow";
    };
    
    worker = {
      enable = true;
      instances = 4;  # 4 workers pra redundância
      maxGPUs = 2;    # 8 GPUs total (4 workers * 2 GPUs)
    };
    
    costTracking = {
      enable = true;
      gpuCostPerHour = 0.90;
    };
  };
  
  # Security hardening
  systemd.services.mlflow.serviceConfig = {
    PrivateTmp = true;
    ProtectSystem = "strict";
    NoNewPrivileges = true;
    PrivateDevices = true;
  };
  
  # Backups
  services.restic.backups.ml-pipeline = {
    paths = [ config.services.adaptive-ml-pipeline.dataDir ];
    repository = "s3:s3.amazonaws.com/backups";
    timerConfig.OnCalendar = "daily";
  };
  
  # Monitoring
  services.prometheus.scrapeConfigs = [{
    job_name = "ml-pipeline";
    static_configs = [{ targets = [ "localhost:5000" ]; }];
  }];
}
```

### Pattern 3: Distributed Cluster (Multi-Node)

```nix
# head-node.nix
{ config, ... }: {
  services.adaptive-ml-pipeline = {
    enable = true;
    
    # Head node roda infrastructure
    postgresql.enable = true;
    mlflow.enable = true;
    temporal.enable = true;
    
    # No workers no head node
    worker.enable = false;
  };
  
  # Ray head node
  systemd.services.ray-head = {
    enable = true;
    serviceConfig = {
      ExecStart = "${pkgs.ray}/bin/ray start --head --port=6379 --dashboard-host=0.0.0.0";
    };
  };
  
  networking.firewall.allowedTCPPorts = [ 6379 8265 ];
}

# worker-node.nix
{ config, ... }: {
  services.adaptive-ml-pipeline = {
    enable = true;
    
    # Worker node só roda workers
    worker = {
      enable = true;
      instances = 8;   # 8 workers
      maxGPUs = 1;     # 8 GPUs total
    };
  };
  
  # Connect to head node
  systemd.services.ray-worker = {
    enable = true;
    serviceConfig = {
      ExecStart = "${pkgs.ray}/bin/ray start --address=head-node:6379 --num-gpus=8";
    };
  };
}
```

## 💰 Cost Optimization Strategies

### 1. Spot Instance Pattern

```nix
# Use spot instances pra non-critical workloads
{ config, ... }: {
  services.adaptive-ml-pipeline.worker = {
    instances = 4;
    maxGPUs = 1;
  };
  
  # Tag services pra spot instance termination handling
  systemd.services."ml-pipeline-worker@".serviceConfig = {
    # Graceful shutdown em 2 min (spot instance warning)
    TimeoutStopSec = 120;
    
    # Auto-restart em outra instância
    Restart = "always";
    RestartSec = 10;
  };
  
  # Checkpoint automation
  systemd.timers.ml-checkpoint = {
    timerConfig.OnUnitActiveSec = "5min";  # Checkpoint a cada 5min
  };
}
```

### 2. Auto-Scaling Pattern

```nix
{ config, lib, ... }:
let
  # Scale workers baseado em queue depth
  scaleWorkers = pkgs.writeShellScript "scale-workers" ''
    QUEUE_DEPTH=$(temporal workflow count --query 'ExecutionStatus="Running"')
    CURRENT_WORKERS=$(systemctl list-units 'ml-pipeline-worker@*.service' --state=active | wc -l)
    
    if [ $QUEUE_DEPTH -gt $((CURRENT_WORKERS * 2)) ]; then
      # Scale up
      systemctl start ml-pipeline-worker@$((CURRENT_WORKERS + 1)).service
    elif [ $QUEUE_DEPTH -lt $CURRENT_WORKERS ]; then
      # Scale down
      systemctl stop ml-pipeline-worker@$CURRENT_WORKERS.service
    fi
  '';
in {
  systemd.timers.ml-autoscale = {
    timerConfig.OnUnitActiveSec = "1min";
  };
  
  systemd.services.ml-autoscale = {
    serviceConfig.ExecStart = scaleWorkers;
  };
}
```

### 3. Resource Packing Optimization

```nix
{ config, ... }: {
  # Pack multiple small jobs num único GPU
  services.adaptive-ml-pipeline.worker = {
    instances = 2;    # Menos workers
    maxGPUs = 4;      # Mas cada um com múltiplos GPUs
  };
  
  # CUDA MPS (Multi-Process Service) pra GPU sharing
  systemd.services.nvidia-mps = {
    enable = true;
    wantedBy = [ "multi-user.target" ];
    serviceConfig = {
      ExecStart = "${pkgs.linuxPackages.nvidia_x11}/bin/nvidia-cuda-mps-control -d";
      Type = "forking";
    };
  };
}
```

## 🔒 Security Patterns

### 1. Secrets Management (com agenix)

```nix
{ config, ... }: {
  age.secrets = {
    mlflow-db-password = {
      file = ./secrets/mlflow-db-password.age;
      owner = config.services.adaptive-ml-pipeline.user;
    };
    
    aws-credentials = {
      file = ./secrets/aws-credentials.age;
      owner = config.services.adaptive-ml-pipeline.user;
    };
  };
  
  services.adaptive-ml-pipeline.mlflow = {
    backendStore = "postgresql://mlflow:$(cat ${config.age.secrets.mlflow-db-password.path})@localhost/mlflow";
  };
  
  systemd.services.mlflow.serviceConfig = {
    EnvironmentFile = config.age.secrets.aws-credentials.path;
  };
}
```

### 2. Network Isolation

```nix
{ config, ... }: {
  # Separate network namespace pra workers
  systemd.services."ml-pipeline-worker@".serviceConfig = {
    PrivateNetwork = false;  # Precisa de network pra Ray
    RestrictAddressFamilies = [ "AF_INET" "AF_INET6" "AF_UNIX" ];
    
    # Só pode conectar em hosts específicos
    IPAddressAllow = [
      "localhost"
      "10.0.0.0/8"      # Internal network
      "172.16.0.0/12"
    ];
    IPAddressDeny = "any";
  };
}
```

## 🎮 Integration com PHANTOM (DAG-based)

### Hook Pattern

Crie um módulo de integração:

```nix
# modules/ml-pipeline/phantom-integration.nix
{ config, lib, pkgs, ... }:
let
  # Script que converte PHANTOM DAG pra Temporal workflow
  phantomToTemporal = pkgs.writeShellScriptBin "phantom-to-temporal" ''
    #!/usr/bin/env bash
    PHANTOM_DAG=$1
    
    # Parse PHANTOM DAG JSON
    ${pkgs.python3}/bin/python3 << EOF
    import json
    import sys
    
    with open('$PHANTOM_DAG') as f:
        dag = json.load(f)
    
    # Convert to Temporal workflow config
    workflow_config = {
        'experiment_name': dag['name'],
        'tasks': []
    }
    
    for task in dag['tasks']:
        if task['type'] == 'ml_training':
            workflow_config['tasks'].append({
                'activity': 'train_model_batch',
                'params': task['params'],
                'depends_on': task.get('dependencies', [])
            })
    
    # Save Temporal config
    with open('temporal_workflow.json', 'w') as f:
        json.dump(workflow_config, f, indent=2)
    
    print(f"Converted {len(workflow_config['tasks'])} tasks")
    EOF
    
    # Execute no Temporal
    python -c "
    import asyncio
    import json
    from workflows import start_adaptive_pipeline
    from models import PipelineConfig
    
    config = PipelineConfig(**json.load(open('temporal_workflow.json')))
    asyncio.run(start_adaptive_pipeline(config))
    "
  '';
in {
  environment.systemPackages = [ phantomToTemporal ];
  
  # Service que monitora PHANTOM output e dispara workflows
  systemd.services.phantom-ml-bridge = {
    enable = true;
    serviceConfig = {
      ExecStart = "${pkgs.bash}/bin/bash -c 'inotifywait -m /var/lib/phantom/output -e create | while read path action file; do ${phantomToTemporal}/bin/phantom-to-temporal $path/$file; done'";
    };
  };
}
```

## 📊 Cost Tracking Dashboard

Integra com teu monitoring stack:

```nix
{ config, ... }: {
  services.grafana.provision.dashboards.settings.providers = [{
    name = "ML Pipeline";
    options.path = ./dashboards;
  }];
  
  # Dashboard JSON com métricas de custo
  environment.etc."grafana/dashboards/ml-cost.json".source = 
    pkgs.writeText "ml-cost-dashboard.json" (builtins.toJSON {
      title = "ML Pipeline Cost Tracking";
      panels = [
        {
          title = "GPU Hours per Experiment";
          targets = [{
            expr = "sum(ml_training_time_seconds) by (experiment_name) / 3600";
          }];
        }
        {
          title = "Cost per Accuracy Point";
          targets = [{
            expr = "ml_total_cost / (ml_best_accuracy * 100)";
          }];
        }
        {
          title = "Resource Efficiency";
          targets = [{
            expr = "ml_successful_trials / ml_total_trials";
          }];
        }
      ];
    });
}
```

## 🚀 Advanced Patterns

### 1. Multi-Tenancy

```nix
{ config, lib, ... }:
let
  mkTenant = name: {
    services.adaptive-ml-pipeline-${name} = {
      enable = true;
      user = "ml-${name}";
      dataDir = "/var/lib/ml-pipeline/${name}";
      
      mlflow.port = 5000 + lib.strings.toInt (builtins.hashString "md5" name);
    };
  };
in {
  # Tenants separados
  imports = [
    (mkTenant "team-alpha")
    (mkTenant "team-beta")
    (mkTenant "team-gamma")
  ];
  
  # Resource quotas
  systemd.slices."ml-pipeline-team-alpha" = {
    sliceConfig = {
      MemoryMax = "32G";
      CPUQuota = "400%";
    };
  };
}
```

### 2. Disaster Recovery

```nix
{ config, ... }: {
  # Continuous replication
  services.postgresql.settings = {
    wal_level = "replica";
    max_wal_senders = 3;
  };
  
  # Automated failover
  systemd.services.ml-pipeline-failover = {
    serviceConfig = {
      ExecStart = pkgs.writeScript "failover" ''
        # Check primary health
        if ! curl -s http://primary:5000/health; then
          # Promote standby
          pg_ctl promote -D /var/lib/postgresql/data
          systemctl start mlflow
          systemctl start ml-pipeline-workers.target
        fi
      '';
    };
  };
}
```

## 🎯 Best Practices

1. **Declarative Everything**: Todas configs no Nix, nada manual
2. **Immutable Infrastructure**: Rebuild em vez de patch
3. **Cost Visibility**: Track every GPU second
4. **Auto-scaling**: Scale baseado em queue depth
5. **Backup Everything**: MLflow artifacts, PostgreSQL, checkpoints
6. **Monitor Metrics**: Prometheus + Grafana pra observability total

## 🔧 Troubleshooting

```bash
# Check service status
systemctl status ml-pipeline-worker@1

# View logs
journalctl -u ml-pipeline-worker@1 -f

# Cost analysis
ml-cost-tracker experiment-name

# Resource usage
systemctl status ml-pipeline-workers.target --no-pager
```

---

**The Nix Way**: Tudo declarativo, tudo reproduzível, tudo rastreável. É o oposto de "works on my machine" - é "works everywhere, always, the same way".

Agora você tem ML orchestration que se integra perfeitamente com teu nix fort knox. 🏰
