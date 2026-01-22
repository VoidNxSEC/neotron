{
  description = "Neutron ML Pipeline - Temporal + Ray + MLflow orchestration (Poetry)";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs =
    {
      self,
      nixpkgs,
      flake-utils,
      ...
    }@inputs:
    flake-utils.lib.eachDefaultSystem (
      system:
      let
        pkgs = import nixpkgs {
          inherit system;
          config = {
            allowUnfree = true; # Para CUDA e drivers proprietários
            cudaSupport = true;
          };
        };

        # Custom script: Cost tracking
        costTrackerScript = pkgs.writeShellScriptBin "ml-cost-tracker" ''
          #!/usr/bin/env bash
          # Cost tracking utility - integra com MLflow

          EXPERIMENT=$1
          GPU_COST_PER_HOUR=''${ML_GPU_COST_PER_HOUR:-0.90}

          if [ -z "$EXPERIMENT" ]; then
              echo "Usage: ml-cost-tracker <experiment_name>"
              exit 1
          fi

          python -c '
          import mlflow
          import sys

          mlflow.set_tracking_uri("http://localhost:5000")
          exp = mlflow.get_experiment_by_name("'"$EXPERIMENT"'")

          if not exp:
              print(f"Experiment {sys.argv[1]} not found")
              sys.exit(1)

          runs = mlflow.search_runs(experiment_ids=[exp.experiment_id])
          gpu_hours = runs["metrics.training_time"].sum() / 3600
          cost = gpu_hours * float("'"$GPU_COST_PER_HOUR"'")

          print(f"Experiment: '"$EXPERIMENT"'")
          print(f"Total GPU Hours: {gpu_hours:.2f}h")
          print(f"Estimated Cost: ''${cost:.2f}")
          print(f"Cost per Run: ''${cost/len(runs):.2f}")
          ' "$EXPERIMENT"
        '';

        # Custom script: Resource limiter
        resourceLimiterScript = pkgs.writeShellScriptBin "ml-run-limited" ''
          #!/usr/bin/env bash
          # Run pipeline com resource limits

          MAX_GPUS=''${1:-1}
          MAX_MEMORY_GB=''${2:-16}
          COMMAND=''${3:-"python main.py 1"}

          echo "Running with limits:"
          echo "  GPUs: $MAX_GPUS"
          echo "  Memory: ''${MAX_MEMORY_GB}GB"

          export CUDA_VISIBLE_DEVICES=$(seq -s, 0 $(($MAX_GPUS - 1)))

          if command -v systemd-run &> /dev/null; then
              systemd-run --user --scope \
                  -p MemoryMax=$(($MAX_MEMORY_GB * 1024 * 1024 * 1024)) \
                  bash -c "$COMMAND"
          else
              bash -c "$COMMAND"
          fi
        '';

      in
      {
        # Development shells
        devShells = {
          # Default shell - Poetry + todas ferramentas
          default = pkgs.mkShell {
            name = "neutron-ml-pipeline-dev";

            buildInputs = with pkgs; [
              # Python environment via uv
              uv
              python313

              # System dependencies
              postgresql_15
              docker
              docker-compose
              just

              # GUI Dependencies
              gtk4
              libadwaita
              glib
              gobject-introspection
              wrapGAppsHook4
              cairo

              # Build tools
              gcc
              stdenv.cc.cc.lib
              zlib
              pkg-config

              # Blockchain development (Foundry)
              foundry-bin  # forge, cast, anvil, chisel

              # Decentralized storage
              kubo  # IPFS daemon and CLI (ipfs)

              # Monitoring tools
              htop
              nvtopPackages.full

              # CUDA (fornecido pelo Nix - versão específica)
              cudaPackages.cudatoolkit
              cudaPackages.cudnn

              # Custom scripts
              costTrackerScript
              resourceLimiterScript

              # Utilities
              curl
              wget
              git
            ];

            shellHook = ''
              echo "════════════════════════════════════════════════════════════"
              echo "  🚀 Neutron ML Pipeline Dev Environment (uv)"
              echo "════════════════════════════════════════════════════════════"
              echo ""

              # CUDA paths
              export CUDA_PATH="${pkgs.cudaPackages.cudatoolkit}"
              export CUDNN_PATH="${pkgs.cudaPackages.cudnn}"
              export LD_LIBRARY_PATH="${pkgs.stdenv.cc.cc.lib}/lib:${pkgs.cudaPackages.cudatoolkit}/lib:${pkgs.cudaPackages.cudnn}/lib:''${LD_LIBRARY_PATH:-}"

              # Environment variables
              export MLFLOW_TRACKING_URI="http://localhost:5000"
              export TEMPORAL_ADDRESS="localhost:7233"
              export RAY_ADDRESS="auto"
              export ML_GPU_COST_PER_HOUR="0.90"

              # uv configuration
              export UV_PYTHON=${pkgs.python313}/bin/python
              export UV_VENV_PATH=".venv"

              echo "📦 Python Environment:"
              echo "  Python: $(python --version)"
              echo "  uv: $(uv --version)"
              echo "  CUDA: ${pkgs.cudaPackages.cudatoolkit.version}"
              echo ""
              echo "⛓️  Blockchain Development:"
              echo "  Foundry: $(forge --version | head -n1)"
              echo "  IPFS: $(ipfs --version)"
              echo "  Commands: forge, cast, anvil, chisel, ipfs"
              echo ""
              echo "📦 Available commands:"
              echo "  just --list         # List all tasks"
              echo "  uv sync             # Install dependencies"
              echo "  uv run <cmd>        # Run command in venv"
              echo "  forge test          # Run smart contract tests"
              echo ""
              echo "🌐 Services (after 'just infra-up'):"
              echo "  Temporal UI: http://localhost:8088"
              echo "  MLflow UI:   http://localhost:5000"
              echo "  Ray Dashboard: http://localhost:8265"
              echo ""
              echo "✅ Environment ready!"
              echo "════════════════════════════════════════════════════════════"
            '';
          };

          # Production shell - sem dev tools
          production = pkgs.mkShell {
            name = "neutron-ml-pipeline-prod";

            buildInputs = with pkgs; [
              uv
              python313
              docker
              docker-compose
              costTrackerScript
              resourceLimiterScript
              cudaPackages.cudatoolkit
              cudaPackages.cudnn
            ];

            shellHook = ''
              export CUDA_PATH="${pkgs.cudaPackages.cudatoolkit}"
              export LD_LIBRARY_PATH="${pkgs.stdenv.cc.cc.lib}/lib:${pkgs.cudaPackages.cudatoolkit}/lib:${pkgs.cudaPackages.cudnn}/lib:''${LD_LIBRARY_PATH:-}"
              export MLFLOW_TRACKING_URI="http://localhost:5000"
              export TEMPORAL_ADDRESS="localhost:7233"
              echo "🚀 Neutron Production Environment Loaded"
            '';
          };
        };

        # Packages exportáveis
        packages = {
          # Worker como script executável
          worker = pkgs.writeShellScriptBin "neutron-worker" ''
            #!/usr/bin/env bash
            cd ${./.}
            python -m neutron.orchestration.worker "$@"
          '';

          # Cost tracker
          cost-tracker = costTrackerScript;

          # Resource limiter
          resource-limiter = resourceLimiterScript;
        };

        # Apps (entry points)
        apps = {
          worker = {
            type = "app";
            program = "${self.packages.${system}.worker}/bin/neutron-worker";
          };
        };

        # Formatter para nix code
        formatter = pkgs.nixpkgs-fmt;
      }
    )
    // {
      # NixOS module para deployment (mantido do original)
      nixosModules.default =
        {
          config,
          lib,
          pkgs,
          ...
        }:
        with lib;
        let
          cfg = config.services.neutron-ml-pipeline;
        in
        {
          options.services.neutron-ml-pipeline = {
            enable = mkEnableOption "Neutron ML Pipeline services";

            user = mkOption {
              type = types.str;
              default = "neutron";
              description = "User to run the ML pipeline services";
            };

            group = mkOption {
              type = types.str;
              default = "neutron";
              description = "Group for ML pipeline services";
            };

            dataDir = mkOption {
              type = types.path;
              default = "/var/lib/neutron-ml-pipeline";
              description = "Data directory for ML pipeline";
            };

            temporal = {
              enable = mkEnableOption "Temporal server";
              port = mkOption {
                type = types.port;
                default = 7233;
                description = "Temporal gRPC port";
              };
            };

            mlflow = {
              enable = mkEnableOption "MLflow tracking server";
              port = mkOption {
                type = types.port;
                default = 5000;
                description = "MLflow web UI port";
              };
              backendStore = mkOption {
                type = types.str;
                default = "postgresql://neutron:neutron@localhost:5432/mlflow";
                description = "MLflow backend store URI";
              };
              artifactRoot = mkOption {
                type = types.str;
                default = "/var/lib/neutron-ml-pipeline/mlflow-artifacts";
                description = "MLflow artifact storage path";
              };
            };

            worker = {
              enable = mkEnableOption "Temporal worker";
              instances = mkOption {
                type = types.int;
                default = 1;
                description = "Number of worker instances";
              };
              maxGPUs = mkOption {
                type = types.int;
                default = 1;
                description = "Max GPUs per worker";
              };
            };

            postgresql = {
              enable = mkEnableOption "PostgreSQL for Temporal and MLflow";
            };

            costTracking = {
              enable = mkEnableOption "Cost tracking and monitoring";
              gpuCostPerHour = mkOption {
                type = types.float;
                default = 0.90;
                description = "GPU cost per hour for tracking";
              };
            };
          };

          config = mkIf cfg.enable {
            # Create user and group
            users.users.${cfg.user} = {
              isSystemUser = true;
              group = cfg.group;
              home = cfg.dataDir;
              createHome = true;
            };

            users.groups.${cfg.group} = { };

            # PostgreSQL setup
            services.postgresql = mkIf cfg.postgresql.enable {
              enable = true;
              ensureDatabases = [
                "temporal"
                "mlflow"
              ];
              ensureUsers = [
                {
                  name = "temporal";
                  ensureDBOwnership = true;
                }
                {
                  name = "mlflow";
                  ensureDBOwnership = true;
                }
              ];
            };

            # MLflow service
            systemd.services.mlflow = mkIf cfg.mlflow.enable {
              description = "MLflow Tracking Server";
              wantedBy = [ "multi-user.target" ];
              after = [ "network.target" ] ++ optional cfg.postgresql.enable "postgresql.service";

              serviceConfig = {
                Type = "simple";
                User = cfg.user;
                Group = cfg.group;
                ExecStart = ''
                  mlflow server \
                    --backend-store-uri ${cfg.mlflow.backendStore} \
                    --default-artifact-root ${cfg.mlflow.artifactRoot} \
                    --host 0.0.0.0 \
                    --port ${toString cfg.mlflow.port}
                '';
                Restart = "always";
                RestartSec = "10s";

                # Security hardening
                PrivateTmp = true;
                ProtectSystem = "strict";
                ProtectHome = true;
                ReadWritePaths = [ cfg.dataDir ];
              };
            };

            # Temporal worker service (multi-instance capable)
            systemd.services."neutron-worker@" = mkIf cfg.worker.enable {
              description = "Neutron ML Pipeline Temporal Worker %i";
              wantedBy = [ "multi-user.target" ];
              after = [ "network.target" ];

              serviceConfig = {
                Type = "simple";
                User = cfg.user;
                Group = cfg.group;
                WorkingDirectory = cfg.dataDir;
                ExecStart = "${self.packages.${pkgs.system}.worker}/bin/neutron-worker";
                Restart = "always";
                RestartSec = "10s";

                # Resource limits
                MemoryMax = "16G";
                CPUQuota = "400%";

                # Environment
                Environment = [
                  "TEMPORAL_ADDRESS=localhost:${toString cfg.temporal.port}"
                  "MLFLOW_TRACKING_URI=http://localhost:${toString cfg.mlflow.port}"
                  "RAY_NUM_GPUS=${toString cfg.worker.maxGPUs}"
                ];
              };
            };

            # Enable worker instances
            systemd.targets.neutron-workers = mkIf cfg.worker.enable {
              description = "Neutron ML Pipeline Worker Pool";
              wantedBy = [ "multi-user.target" ];
              wants = map (i: "neutron-worker@${toString i}.service") (range 1 cfg.worker.instances);
            };

            # Cost tracking timer (daily report)
            systemd.timers.neutron-cost-report = mkIf cfg.costTracking.enable {
              description = "Daily Neutron ML Pipeline Cost Report";
              wantedBy = [ "timers.target" ];
              timerConfig = {
                OnCalendar = "daily";
                Persistent = true;
              };
            };

            systemd.services.neutron-cost-report = mkIf cfg.costTracking.enable {
              description = "Generate Neutron ML Pipeline Cost Report";
              serviceConfig = {
                Type = "oneshot";
                User = cfg.user;
                ExecStart = "${self.packages.${pkgs.system}.cost-tracker}/bin/ml-cost-tracker all";
              };
            };

            # Firewall rules
            networking.firewall.allowedTCPPorts = mkIf cfg.enable [
              cfg.temporal.port
              cfg.mlflow.port
              8088 # Temporal UI
              8265 # Ray dashboard
            ];
          };
        };
    };
}
