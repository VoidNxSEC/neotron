{ config
, lib
, ...
}:

with lib;

let
  cfg = config.services.neotron.langmath;
in
{
  options.services.neotron.langmath = {
    enable = mkEnableOption "Neotron LangMath Layer 0 runtime integration";

    llmProvider = mkOption {
      type = types.enum [
        "nvidia"
        "llamacpp"
      ];
      default = "llamacpp";
      description = "Default provider used by the vendored LangMath oracle helpers.";
    };

    llamaCppBaseUrl = mkOption {
      type = types.str;
      default = "http://localhost:8081/v1";
      description = "OpenAI-compatible llama.cpp endpoint for LangMath local inference.";
    };

    llamaCppModel = mkOption {
      type = types.str;
      default = "local-model";
      description = "Model name sent to the llama.cpp OpenAI-compatible endpoint.";
    };

    chromaDbDir = mkOption {
      type = types.str;
      default = "/var/lib/neotron/langmath-brain";
      description = "Persistent Chroma directory used by LangMath RAG helpers.";
    };
  };

  config = mkIf cfg.enable {
    environment.sessionVariables = {
      LANGMATH_LLM_PROVIDER = cfg.llmProvider;
      LANGMATH_LLAMA_CPP_BASE_URL = cfg.llamaCppBaseUrl;
      LANGMATH_LLAMA_CPP_MODEL = cfg.llamaCppModel;
      LANGMATH_CHROMA_DB_DIR = cfg.chromaDbDir;
    };

    systemd.tmpfiles.rules = [
      "d ${cfg.chromaDbDir} 0750 root root - -"
    ];
  };
}
