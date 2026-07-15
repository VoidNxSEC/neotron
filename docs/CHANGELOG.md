# Changelog

All notable changes to the NEXUS Platform will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
-   **SENTINEL**: Core compliance engine with 'Block', 'Warn', and 'Audit' modes.
-   **SENTINEL**: LGPD Article 18 & 20 support.
-   **SENTINEL**: Immutable PostgreSQL audit trail.
-   **CORTEX**: Multi-agent consensus engine (Majority, Unanimous, Weighted).
-   **Docs**: Comprehensive `docs/` structure including CI/CD and Integration guides.
-   **Infra**: Nix Flake environment with `uv` and CUDA support.

### Changed
-   Migrated from Poetry-only to `uv` + Nix hybrid for faster dependency resolution.
-   Updated `README.md` with Mermaid diagrams and professional badges.

## [0.1.0] - 2026-01-01

### Initial Release
-   Basic project scaffolding.
-   Initial architecture design documents.
