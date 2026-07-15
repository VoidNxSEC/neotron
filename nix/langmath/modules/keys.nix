{ config
, lib
, pkgs
, ...
}:

with lib;

let
  cfg = config.services.neotron.langmath.apiKeys;
in
{
  options.services.neotron.langmath.apiKeys = {
    enable = mkEnableOption "Expose LangMath API keys from SOPS secrets";

    sopsFile = mkOption {
      type = types.nullOr types.path;
      default = null;
      description = "Optional SOPS file containing LangMath provider API keys.";
    };

    owner = mkOption {
      type = types.str;
      default = "root";
      description = "Owner for decrypted LangMath API key files.";
    };

    group = mkOption {
      type = types.str;
      default = "root";
      description = "Group for decrypted LangMath API key files.";
    };
  };

  config = mkIf (cfg.enable && cfg.sopsFile != null) {
    sops.secrets = {
      "anthropic_api_key" = {
        sopsFile = cfg.sopsFile;
        mode = "0440";
        owner = cfg.owner;
        group = cfg.group;
      };

      "openai_api_key" = {
        sopsFile = cfg.sopsFile;
        mode = "0440";
        owner = cfg.owner;
        group = cfg.group;
      };

      "openrouter_api_key" = {
        sopsFile = cfg.sopsFile;
        mode = "0440";
        owner = cfg.owner;
        group = cfg.group;
      };

      "gemini_api_key" = {
        sopsFile = cfg.sopsFile;
        mode = "0440";
        owner = cfg.owner;
        group = cfg.group;
      };

      "nvidia_api_key" = {
        sopsFile = cfg.sopsFile;
        mode = "0440";
        owner = cfg.owner;
        group = cfg.group;
      };

      "groq_api_key" = {
        sopsFile = cfg.sopsFile;
        mode = "0440";
        owner = cfg.owner;
        group = cfg.group;
      };

      "together_api_key" = {
        sopsFile = cfg.sopsFile;
        mode = "0440";
        owner = cfg.owner;
        group = cfg.group;
      };

      "huggingface_api_key" = {
        sopsFile = cfg.sopsFile;
        mode = "0440";
        owner = cfg.owner;
        group = cfg.group;
      };
    };

    environment.etc."load-api-keys.sh" = {
      text = ''
        #!/usr/bin/env bash
        # Load decrypted API keys from /run/secrets
        # Usage: source /etc/load-api-keys.sh

        export ANTHROPIC_API_KEY="$(cat /run/secrets/anthropic_api_key 2>/dev/null || echo "")"
        export OPENAI_API_KEY="$(cat /run/secrets/openai_api_key 2>/dev/null || echo "")"
        export OPENROUTER_API_KEY="$(cat /run/secrets/openrouter_api_key 2>/dev/null || echo "")"
        export GEMINI_API_KEY="$(cat /run/secrets/gemini_api_key 2>/dev/null || echo "")"
        export NVIDIA_API_KEY="$(cat /run/secrets/nvidia_api_key 2>/dev/null || echo "")"
        export GROQ_API_KEY="$(cat /run/secrets/groq_api_key 2>/dev/null || echo "")"
        export TOGETHER_API_KEY="$(cat /run/secrets/together_api_key 2>/dev/null || echo "")"
        export HUGGINGFACE_API_KEY="$(cat /run/secrets/huggingface_api_key 2>/dev/null || echo "")"

        echo "✓ LangMath API keys loaded from SOPS"
        echo "  - ANTHROPIC_API_KEY: ''${ANTHROPIC_API_KEY:0:15}..."
        echo "  - OPENAI_API_KEY: ''${OPENAI_API_KEY:0:15}..."
        echo "  - OPENROUTER_API_KEY: ''${OPENROUTER_API_KEY:0:15}..."
        echo "  - GEMINI_API_KEY: ''${GEMINI_API_KEY:0:15}..."
        echo "  - NVIDIA_API_KEY: ''${NVIDIA_API_KEY:0:15}..."
        echo "  - GROQ_API_KEY: ''${GROQ_API_KEY:0:15}..."
        echo "  - TOGETHER_API_KEY: ''${TOGETHER_API_KEY:0:15}..."
        echo "  - HUGGINGFACE_API_KEY: ''${HUGGINGFACE_API_KEY:0:15}..."
      '';
      mode = "0755";
    };
  };
}
