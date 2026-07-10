"""
Nix Flake Checker — Detect build-time injection in Nix expressions.

Attack vectors detected:
    1. shellHook with suspicious commands (curl pipe, eval, /dev/tcp)
    2. builtins.fetchGit / builtins.fetchTarball without pinned rev/sha256
    3. Unusual XDG/HOME redirections (attacker-controlled paths)
    4. nativeBuildInputs from non-Nixpkgs sources
    5. Flake inputs pointing to non-GitHub/non-pinned URLs

Usage:
    checker = NixFlakeChecker("/path/to/flake.nix")
    findings = checker.scan()
"""

import re
from dataclasses import dataclass, field
from pathlib import Path


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------
@dataclass
class FlakeFinding:
    """A suspicious finding in a Nix flake or shell expression."""

    severity: str  # CRITICAL, HIGH, MEDIUM, LOW
    category: str  # shellHook, fetch, input, redirect
    location: str  # file:line or section
    description: str
    evidence: str = ""
    remediation: str = ""


@dataclass
class FlakeScanResult:
    """Complete scan result for a Nix flake."""

    flake_path: str
    findings: list[FlakeFinding] = field(default_factory=list)
    has_critical: bool = False

    @property
    def safe(self) -> bool:
        return not self.has_critical


# ---------------------------------------------------------------------------
# Suspicious patterns
# ---------------------------------------------------------------------------

# Shell commands that should NEVER appear in a shellHook
SHELL_HOOK_MALICIOUS = [
    (r"curl\s+.*\|\s*(?:ba)?sh", "CRITICAL", "curl pipe to shell — execução remota arbitrária"),
    (r"wget\s+.*\|\s*(?:ba)?sh", "CRITICAL", "wget pipe to shell — execução remota arbitrária"),
    (r"/dev/tcp", "CRITICAL", "Reverse shell via /dev/tcp — backdoor de rede"),
    (r"nc\s+-[el]", "CRITICAL", "Netcat listener — shell reverso"),
    (r"eval\s+", "HIGH", "Eval dinâmico — pode executar código arbitrário"),
    (r"base64\s.*-d", "HIGH", "Base64 decode — ofuscação de payload"),
    (r"chmod\s+\+x", "MEDIUM", "Torna arquivo executável"),
    (r"python\s+-c\s", "MEDIUM", "Python inline — execução de código"),
    (r"nix\s+develop", "MEDIUM", "Nested nix develop — escape de sandbox"),
    (r"nix\s+build", "MEDIUM", "Trigger Nix build — rebuild não autorizado"),
    (r"nixos-rebuild", "HIGH", "Trigger system rebuild — comprometimento do OS"),
    (r"sudo\s", "HIGH", "Escalação de privilégio via sudo"),
    (r"git\s+clone", "MEDIUM", "Git clone em shellHook — potencial repo malicioso"),
    (r"npm\s+install\s+-g", "HIGH", "npm global install — poluição do sistema"),
    (r"pip\s+install", "MEDIUM", "pip install em shellHook — dependência não verificada"),
]

# Suspicious XDG/HOME redirections
SUSPICIOUS_REDIRECTIONS = [
    (r'HOME\s*=\s*"\$PWD/', "HIGH", "HOME redirecionado para dentro do projeto"),
    (r'HOME\s*=\s*"\$PROJECT_ROOT/', "HIGH", "HOME redirecionado para dentro do projeto"),
    (r'HOME\s*=\s*"\$\(pwd\)/', "HIGH", "HOME redirecionado para diretório atual"),
]

# Unpinned Nix fetchers
UNPINNED_FETCHERS = [
    (r"builtins\.fetchGit\b(?!.*\brev\s*=\s*)", "HIGH", "fetchGit sem 'rev' — entrada não pinada"),
    (
        r"builtins\.fetchTarball\b(?!.*\bsha256\s*=\s*)",
        "HIGH",
        "fetchTarball sem 'sha256' — integridade não verificável",
    ),
    (
        r"builtins\.fetchurl\b(?!.*\bsha256\s*=\s*)",
        "HIGH",
        "fetchurl sem 'sha256' — integridade não verificável",
    ),
    (
        r'url\s*=\s*"[^"]*github[^"]*/(?!.*\brev\s*=\s*)',
        "MEDIUM",
        "Flake input sem 'rev' — versão flutuante",
    ),
]

# Suspicious flake inputs (non-standard sources)
SUSPICIOUS_INPUTS = [
    (
        r'url\s*=\s*"https?://(?!github\.com|gitlab\.com|nixos\.org)',
        "HIGH",
        "Flake input de URL não padrão",
    ),
    (r'url\s*=\s*"git://', "MEDIUM", "Git protocol sem criptografia (git://)"),
    (r'url\s*=\s*"file://', "MEDIUM", "Flake input de arquivo local — bypass de verificação"),
]


# ---------------------------------------------------------------------------
# Checker
# ---------------------------------------------------------------------------
class NixFlakeChecker:
    """Scan a Nix flake for build-time injection indicators."""

    def __init__(self, flake_path: str):
        self.flake_path = Path(flake_path).resolve()
        self._content: str | None = None

    def scan(self) -> FlakeScanResult:
        """Run all checks on the flake. Returns FlakeScanResult."""
        result = FlakeScanResult(flake_path=str(self.flake_path))

        if not self.flake_path.exists():
            result.findings.append(
                FlakeFinding(
                    severity="MEDIUM",
                    category="missing",
                    location=str(self.flake_path),
                    description="Flake file not found",
                    remediation="Verifique o caminho",
                )
            )
            return result

        self._content = self.flake_path.read_text(errors="replace")

        self._check_shellhook(result)
        self._check_redirections(result)
        self._check_fetchers(result)
        self._check_inputs(result)
        self._check_buildinputs(result)

        result.has_critical = any(f.severity == "CRITICAL" for f in result.findings)
        return result

    # ------------------------------------------------------------------
    # shellHook scanning
    # ------------------------------------------------------------------
    def _check_shellhook(self, result: FlakeScanResult):
        """Scan shellHook for malicious patterns."""
        # Find all shellHook blocks
        hook_pattern = re.compile(r"shellHook\s*=\s*''(.*?)'';", re.DOTALL)
        hooks = hook_pattern.findall(self._content)

        for hook_idx, hook_content in enumerate(hooks):
            lines = hook_content.split("\n")
            for line_no, line in enumerate(lines):
                for pattern, severity, desc in SHELL_HOOK_MALICIOUS:
                    if re.search(pattern, line, re.IGNORECASE):
                        result.findings.append(
                            FlakeFinding(
                                severity=severity,
                                category="shellHook",
                                location=f"shellHook #{hook_idx + 1}, line ~{line_no + 1}",
                                description=f"{desc}: {line.strip()[:100]}",
                                evidence=line.strip(),
                                remediation="Remova este comando do shellHook. "
                                "Shell hooks devem apenas configurar ambiente, "
                                "não executar código arbitrário.",
                            )
                        )

    # ------------------------------------------------------------------
    # XDG/HOME redirections
    # ------------------------------------------------------------------
    def _check_redirections(self, result: FlakeScanResult):
        """Detect suspicious HOME/XDG redirections."""
        for pattern, severity, desc in SUSPICIOUS_REDIRECTIONS:
            if re.search(pattern, self._content):
                result.findings.append(
                    FlakeFinding(
                        severity=severity,
                        category="redirection",
                        location=str(self.flake_path),
                        description=f"{desc} — pode ser usado para isolar o ambiente "
                        f"ou para esconder arquivos do atacante.",
                        evidence="",
                        remediation="Garanta que HOME não aponte para diretórios de "
                        "projetos de terceiros.",
                    )
                )

    # ------------------------------------------------------------------
    # Unpinned fetchers
    # ------------------------------------------------------------------
    def _check_fetchers(self, result: FlakeScanResult):
        """Detect unpinned Nix fetchers."""
        for pattern, severity, desc in UNPINNED_FETCHERS:
            for match in re.finditer(pattern, self._content):
                line_start = self._content[: match.start()].count("\n") + 1
                result.findings.append(
                    FlakeFinding(
                        severity=severity,
                        category="fetch",
                        location=f"line ~{line_start}",
                        description=f"{desc}: {match.group(0)[:80]}",
                        evidence=match.group(0),
                        remediation="Adicione 'rev' ou 'sha256' para pinnar a versão.",
                    )
                )

    # ------------------------------------------------------------------
    # Suspicious flake inputs
    # ------------------------------------------------------------------
    def _check_inputs(self, result: FlakeScanResult):
        """Detect suspicious flake input URLs."""
        # Find the inputs section
        inputs_section = re.search(r"inputs\s*=\s*\{(.*?)\};", self._content, re.DOTALL)
        if not inputs_section:
            return

        section = inputs_section.group(1)
        for pattern, severity, desc in SUSPICIOUS_INPUTS:
            for match in re.finditer(pattern, section):
                result.findings.append(
                    FlakeFinding(
                        severity=severity,
                        category="input",
                        location="inputs section",
                        description=f"{desc}: {match.group(0)[:100]}",
                        evidence=match.group(0),
                        remediation="Prefera GitHub/GitLab/NixOS com hash pinado.",
                    )
                )

    # ------------------------------------------------------------------
    # Suspicious buildInputs
    # ------------------------------------------------------------------
    def _check_buildinputs(self, result: FlakeScanResult):
        """Detect buildInputs from non-Nixpkgs sources."""
        # Look for packages that use callPackage with non-local paths
        non_local = re.findall(
            r"callPackage\s+(?!\.\/|\.\.\/)([^\s{]+)",
            self._content,
        )
        for match in non_local:
            if match.strip() and not match.startswith("pkgs."):
                result.findings.append(
                    FlakeFinding(
                        severity="MEDIUM",
                        category="buildInput",
                        location="mkShell packages",
                        description=f"callPackage de fonte não local: {match.strip()[:80]}",
                        evidence=match.strip(),
                        remediation="Verifique a origem deste pacote.",
                    )
                )
