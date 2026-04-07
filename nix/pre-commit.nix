{
  description = "Pre-commit hooks for Neutron NEXUS";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    pre-commit-hooks.url = "github:cachix/pre-commit-hooks.nix";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, pre-commit-hooks, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system: {
      checks = {
        pre-commit-check = pre-commit-hooks.lib.${system}.run {
          src = ./.;
          hooks = {
            # Nix
            nixpkgs-fmt.enable = true;

            # Python
            black.enable = true;
            ruff.enable = true;
            mypy.enable = true;

            # Solidity (Foundry)
            forge-fmt = {
              enable = true;
              name = "forge fmt";
              entry = "forge fmt";
              files = "\\.sol$";
              pass_filenames = false;
            };
          };
        };
      };

      devShells.default = nixpkgs.legacyPackages.${system}.mkShell {
        inherit (self.checks.${system}.pre-commit-check) shellHook;
        buildInputs = self.checks.${system}.pre-commit-check.enabledPackages;
      };
    });
}
