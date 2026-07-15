{
  description = "Template Nix: Poetry (Python), Rust e Cron";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
    sops-nix.url = "github:Mic92/sops-nix";
    sops-nix.inputs.nixpkgs.follows = "nixpkgs";

    rust-overlay = {
      url = "github:oxalica/rust-overlay";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    crane = {
      url = "github:ipetkov/crane";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    advisory-db = {
      url = "github:rustsec/advisory-db";
      flake = false;
    };

    neotron = {
      url = "github:VoidNxSEC/neotron";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs =
    { self
    , nixpkgs
    , crane
    , rust-overlay
    , advisory-db
    , sops-nix
    , flake-utils
    , ...
    }:
    let
      systemOutputs = flake-utils.lib.eachDefaultSystem (
        system:
        let
          VERSION = "0.1.0";

          pkgs = import nixpkgs {
            inherit system;
            config.allowUnfree = true;
            overlays = [ rust-overlay.overlays.default ];
          };

          rust-toolchain = pkgs.rust-bin.stable.latest.default.override {
            extensions = [
              "rust-src"
              "rust-analyzer"
              "clippy"
              "rustfmt"
            ];

            targets = [ "x86_64-unknown-linux-gnu" ];
          };

          craneLib = (crane.mkLib pkgs).overrideToolchain rust-toolchain;

          pythonEnv = pkgs.python313.withPackages (
            ps: with ps; [
              pip
              setuptools
              wheel
              uv
              nltk
              scikit-learn
              scipy
              numpy
              pandas
              matplotlib
              seaborn
              filetype
              chardet
              python-magic
              python-docx
              python-pptx
              exifread
              pdfminer-six
              openpyxl
              pyyaml
              toml
              jinja2
              rich
              tqdm
              typer
              requests
              python-dotenv
              aiofiles
              jsonschema
              pydantic
              chromadb
              faiss
              sentence-transformers
              transformers
              torch
              tiktoken
              fastapi
              uvicorn
              python-multipart
              httpx
              prometheus-client
              structlog
              pytest
              pytest-asyncio
              pytest-cov
              ruff
              mypy
            ]
          );

          systemTools = with pkgs; [
            jq
            poetry
            yq-go
            miller
            gron
            htmlq
            file
            exiftool
            binwalk
            hexyl
            b3sum
            xxHash
            rhash
            ripgrep
            fzf
            fd
            tree
            p7zip
            unrar
            unzip
            lz4
            zstd
            foremost
            sleuthkit
            bulk_extractor
            scalpel
            volatility3
            just
            parallel
          ];

          zshPackages = with pkgs; [
            zsh
            zplug
            zsh-syntax-highlighting
            zsh-autosuggestions
            zsh-completions
            zsh-history-substring-search
            zsh-navigation-tools
          ];
        in
        {
          devShells.default = pkgs.mkShell {
            buildInputs =
              with pkgs;
              [
                pythonEnv
                rust-toolchain
                kubo
                cron
                pkg-config
                openssl
                libiconv
                pkgs.sops
              ]
              ++ systemTools
              ++ zshPackages;

            shellHook = ''
              export POETRY_VIRTUALENVS_IN_PROJECT=true

              echo "🛠️ Ambiente de Desenvolvimento Ativo"
              echo "Python: $(python --version)"
              echo "Poetry: $(poetry --version)"
              echo "Rust:   $(rustc --version)"

              # Host ZSH detection and integration
              if [ -n "$ZSH_VERSION" ]; then
                  echo "🐚 Integrated with Host ZSH"
              elif [ -x "$(command -v zsh)" ]; then
                  export SHELL=$(command -v zsh)
                  echo "🚀 Switching to ZSH..."
                  exec zsh --login
              fi

              if [ -f "pyproject.toml" ]; then
                echo "📦 Sincronizando dependências (Poetry)..."
                if ! poetry install --no-interaction --sync 2>/dev/null; then
                  poetry install --no-interaction
                fi

                VENV_PATH=$(poetry env info --path 2>/dev/null)
                if [ -n "$VENV_PATH" ]; then
                   source "$VENV_PATH/bin/activate"
                fi
              fi
            '';

            env = {
              SOPS_CONFIG_DIR = "${self}/secrets";
            };
          };
        }
      );
    in
    systemOutputs
    // {
      nixosModules = {
        default = import ./modules/default.nix;
      };
    };
}
