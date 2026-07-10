"""
Git Scanner — Detect repository-level supply chain attacks.

Attack vectors detected:
    1. Non-standard git hooks (post-checkout, pre-commit, etc.)
       The French recruiter attack: hook modifies flake.nix before Nix sees it.

    2. Git config remapping (url.insteadOf)
       Redirects git fetch to attacker-controlled repos.

    3. Suspicious remotes (non-GitHub/GitLab URLs)

    4. Uncommitted changes in critical files (flake.nix, shell.nix)

Usage:
    scanner = GitScanner("/path/to/repo")
    findings = scanner.scan()
    for f in findings:
        print(f.severity, f.description)
"""

import stat
from dataclasses import dataclass, field
from pathlib import Path

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class GitHookFinding:
    """A suspicious git hook finding."""

    severity: str  # CRITICAL, HIGH, MEDIUM, LOW
    category: str  # hook, config, remote
    path: str
    description: str
    evidence: str = ""
    remediation: str = ""

    def to_cli(self) -> str:
        color = {"CRITICAL": "red", "HIGH": "yellow", "MEDIUM": "blue", "LOW": "white"}
        return (
            f"[{self.severity}] {self.category}: {self.path}\n"
            f"  → {self.description}\n"
            f"  → Fix: {self.remediation}"
        )


@dataclass
class GitConfigFinding:
    """A suspicious git config finding."""

    severity: str
    key: str
    value: str
    description: str
    remediation: str = ""


@dataclass
class ScanResult:
    """Complete scan result for a repository."""

    repo_path: str
    hooks_findings: list[GitHookFinding] = field(default_factory=list)
    config_findings: list[GitConfigFinding] = field(default_factory=list)
    remote_findings: list[GitConfigFinding] = field(default_factory=list)
    has_critical: bool = False

    @property
    def total_findings(self) -> int:
        return len(self.hooks_findings) + len(self.config_findings) + len(self.remote_findings)

    @property
    def safe(self) -> bool:
        return not self.has_critical


# ---------------------------------------------------------------------------
# Known malicious patterns
# ---------------------------------------------------------------------------

# Git hooks that should NEVER exist without explicit user intent
SUSPICIOUS_HOOKS = {
    "post-checkout": {
        "risk": "CRITICAL",
        "why": "Executa APÓS git checkout/clone. O ataque francês usou isso para modificar flake.nix.",
        "fix": "rm .git/hooks/post-checkout && git config --unset core.hooksPath",
    },
    "post-merge": {
        "risk": "HIGH",
        "why": "Executa após git merge/pull. Pode injetar código em source files.",
        "fix": "rm .git/hooks/post-merge",
    },
    "pre-commit": {
        "risk": "MEDIUM",
        "why": "Executa ANTES de cada commit. Pode exfiltrar dados.",
        "fix": "Revise o conteúdo manualmente. Se não foi você que criou, remova.",
    },
    "pre-push": {
        "risk": "MEDIUM",
        "why": "Executa antes de git push. Pode vazar secrets.",
        "fix": "Revise e remova se não for seu.",
    },
    "post-rewrite": {
        "risk": "HIGH",
        "why": "Executa após rebase/amend. Oportunidade de injeção.",
        "fix": "rm .git/hooks/post-rewrite",
    },
    "prepare-commit-msg": {
        "risk": "MEDIUM",
        "why": "Modifica mensagens de commit. Pode esconder evidência.",
        "fix": "rm .git/hooks/prepare-commit-msg",
    },
    "fsmonitor-watchman": {
        "risk": "HIGH",
        "why": "Executa em todo evento de filesystem. Backdoor persistente.",
        "fix": "rm .git/hooks/fsmonitor-watchman",
    },
    "post-update": {
        "risk": "HIGH",
        "why": "Executa em git push no lado servidor. Escalação de privilégio.",
        "fix": "rm .git/hooks/post-update",
    },
}

# Suspicious git config keys that redirect repository sources
SUSPICIOUS_CONFIG_KEYS = [
    "url.insteadof",  # Redirects git:// to attacker's repo
    "core.hookspath",  # Overrides hooks directory
    "core.fsmonitor",  # Custom filesystem monitor
    "protocol.allow",  # Allows dangerous protocols
    "credential.helper",  # Credential exfiltration
]

# Suspicious strings in hook content
MALICIOUS_PATTERNS = [
    r"/dev/tcp",  # Reverse shell
    r"curl.*\|.*sh",  # Pipe to shell
    r"wget.*-O.*\|.*sh",  # Pipe to shell
    r"eval\s",  # Dynamic eval
    r"base64.*-d",  # Base64 decode (obfuscation)
    r"chmod\s\+x",  # Make executable
    r"nc\s+-[el]",  # Netcat backdoor
    r"python.*-c\s",  # Inline Python
    r"exec\s",  # Shell exec
    r"nix\s+develop",  # Trigger Nix build
    r"nix\s+build",  # Trigger Nix build
    r"shellHook\s*=",  # Nix shellHook injection
    r"builtins\.fetchGit",  # Unpinned fetch
    r"builtins\.fetchTarball",  # Unpinned fetch
]


# ---------------------------------------------------------------------------
# Scanner
# ---------------------------------------------------------------------------
class GitScanner:
    """Scan a git repository for supply chain attack indicators."""

    def __init__(self, repo_path: str):
        self.repo_path = Path(repo_path).resolve()
        self.git_dir = self.repo_path / ".git"

    def scan(self) -> ScanResult:
        """Run all scan checks. Returns ScanResult."""
        result = ScanResult(repo_path=str(self.repo_path))

        if not self.git_dir.exists():
            # Not a git repo — skip
            return result

        self._scan_hooks(result)
        self._scan_config(result)
        self._scan_remotes(result)
        self._scan_critical_files(result)

        result.has_critical = any(f.severity == "CRITICAL" for f in result.hooks_findings)
        return result

    # ------------------------------------------------------------------
    # Hook scanning
    # ------------------------------------------------------------------
    def _scan_hooks(self, result: ScanResult):
        hooks_dir = self.git_dir / "hooks"
        if not hooks_dir.exists():
            return

        for hook_file in hooks_dir.iterdir():
            if hook_file.suffix == ".sample":
                continue  # Sample hooks are safe
            if not hook_file.is_file():
                continue

            hook_name = hook_file.name
            content = hook_file.read_text(errors="replace")[:4096]
            is_executable = hook_file.stat().st_mode & stat.S_IXUSR

            # Check against known suspicious hooks
            if hook_name in SUSPICIOUS_HOOKS:
                info = SUSPICIOUS_HOOKS[hook_name]
                finding = GitHookFinding(
                    severity=info["risk"],
                    category="hook",
                    path=str(hook_file.relative_to(self.repo_path)),
                    description=info["why"],
                    evidence=content[:500],
                    remediation=info["fix"],
                )
                result.hooks_findings.append(finding)
                continue

            # Unknown hook — flag anyway
            if is_executable or hook_file.stat().st_size > 0:
                finding = GitHookFinding(
                    severity="HIGH",
                    category="hook:unknown",
                    path=str(hook_file.relative_to(self.repo_path)),
                    description=f"Hook desconhecido e executável: '{hook_name}'",
                    evidence=content[:500],
                    remediation=f"Revise manualmente: cat {hook_file}",
                )
                result.hooks_findings.append(finding)

            # Scan hook content for malicious patterns
            for pattern in MALICIOUS_PATTERNS:
                import re

                if re.search(pattern, content, re.IGNORECASE):
                    finding = GitHookFinding(
                        severity="CRITICAL",
                        category="hook:pattern",
                        path=str(hook_file.relative_to(self.repo_path)),
                        description=f"Padrão suspeito no hook '{hook_name}': {pattern}",
                        evidence=content[:500],
                        remediation=f"Remova imediatamente: rm {hook_file}",
                    )
                    result.hooks_findings.append(finding)
                    break  # One pattern match is enough

    # ------------------------------------------------------------------
    # Config scanning
    # ------------------------------------------------------------------
    def _scan_config(self, result: ScanResult):
        config_path = self.git_dir / "config"
        if not config_path.exists():
            return

        content = config_path.read_text(errors="replace")
        current_section = ""

        for line in content.splitlines():
            line = line.strip()
            if line.startswith("[") and line.endswith("]"):
                current_section = line[1:-1]
                continue

            if "=" not in line:
                continue

            key, _, value = line.partition("=")
            key = key.strip().lower()
            value = value.strip()

            # Check for URL redirect
            if "insteadof" in key.lower():
                finding = GitConfigFinding(
                    severity="CRITICAL",
                    key=key,
                    value=value,
                    description=f"Git URL redirect ativo: '{key} = {value}'. "
                    f"Isso redireciona TODOS os clones para um servidor controlado.",
                    remediation=f"Remova: git config --unset {current_section}.{key}",
                )
                result.config_findings.append(finding)

            # Check for hooksPath override
            if "hookspath" in key.lower():
                finding = GitConfigFinding(
                    severity="CRITICAL",
                    key=key,
                    value=value,
                    description=f"core.hooksPath aponta para diretório externo: {value}",
                    remediation="git config --unset core.hooksPath",
                )
                result.config_findings.append(finding)

            # Check for fsmonitor
            if "fsmonitor" in key.lower() and value:
                finding = GitConfigFinding(
                    severity="HIGH",
                    key=key,
                    value=value,
                    description=f"Filesystem monitor customizado: {value}",
                    remediation="git config --unset core.fsmonitor",
                )
                result.config_findings.append(finding)

    # ------------------------------------------------------------------
    # Remote scanning
    # ------------------------------------------------------------------
    def _scan_remotes(self, result: ScanResult):
        config_path = self.git_dir / "config"
        if not config_path.exists():
            return

        content = config_path.read_text(errors="replace")

        for line in content.splitlines():
            if "url =" in line.lower():
                _, _, url = line.partition("=")
                url = url.strip()

                # Flag non-standard URLs
                if url and not any(
                    domain in url
                    for domain in [
                        "github.com",
                        "gitlab.com",
                        "bitbucket.org",
                        "codeberg.org",
                        "git.sr.ht",
                        "git.kernel.org",
                    ]
                ):
                    finding = GitConfigFinding(
                        severity="HIGH",
                        key="remote.url",
                        value=url,
                        description=f"Remote aponta para domínio não padrão: {url}",
                        remediation="Verifique: git remote -v",
                    )
                    result.remote_findings.append(finding)

    # ------------------------------------------------------------------
    # Critical files check
    # ------------------------------------------------------------------
    def _scan_critical_files(self, result: ScanResult):
        """Check if critical build files have uncommitted changes."""
        critical_files = [
            "flake.nix",
            "flake.lock",
            "shell.nix",
            "default.nix",
            "pyproject.toml",
            "Cargo.toml",
            "package.json",
        ]

        for cf in critical_files:
            fp = self.repo_path / cf
            if not fp.exists():
                continue

            # Check if file has git diff (uncommitted)
            import subprocess

            try:
                proc = subprocess.run(
                    ["git", "diff", "--name-only", cf],
                    cwd=str(self.repo_path),
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if cf in proc.stdout:
                    finding = GitHookFinding(
                        severity="HIGH",
                        category="uncommitted",
                        path=cf,
                        description=f"Arquivo crítico '{cf}' tem alterações não commitadas. "
                        f"Isso pode ser injeção via hook.",
                        evidence="",
                        remediation="Revise com 'git diff' e commite ou descarte.",
                    )
                    result.hooks_findings.append(finding)
            except (subprocess.TimeoutExpired, FileNotFoundError):
                pass
