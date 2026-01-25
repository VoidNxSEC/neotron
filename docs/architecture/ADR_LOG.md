# Architectural Decision Log

## ADR-001: Enforcement of Security-as-Code via Blocking Gates

- **Status**: Accepted
- **Context**: Traditional security audits occur post-deployment, increasing remediation costs and exposure windows. The `neutron` project handles sensitive ML workloads.
- **Decision**: Inject Trivy vulnerability scanning directly into the CI build stage (Gate 1).
- **Consequence**: Builds will fail immediately if high-severity CVEs are detected in dependencies or container images, enforcing a "shift-left" security posture. Validates both OS-level (Nix) and Application-level (Python/uv) dependencies.

## ADR-002: Ephemeral Substrate Orchestration via Nix

- **Status**: Accepted
- **Context**: "Works on my machine" syndrome destroys velocity in complex ML pipelines involving Temporal, Ray, and MLflow.
- **Decision**: Use `nix develop` + `docker-compose` as the single source of truth for both local development and CI execution.
- **Consequence**: The CI pipeline (`.github/workflows/ci.yml`) executes the exact same binary paths and environment variables as the local developer shell, eliminating environment drift. `uv` is used for high-speed Python resolution within the Nix shell.
