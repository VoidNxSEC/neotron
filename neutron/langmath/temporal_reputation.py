"""
Temporal Reputation System: Adversarial Gradual Detection

Detecta ataques sofisticados que:
  - Constroem reputação gradualmente
  - Escalam sutilmente ao longo do tempo
  - Exploram confiança acumulada

Matemática:
  R(t+1) = R(t)·e^(-λΔt) + α·ΔR

  onde:
    e^(-λΔt) = decay temporal (confiança não é eterna)
    α·ΔR = update baseado em comportamento
"""

import math
import time
from collections import deque
from dataclasses import dataclass

# Import detectors
from neutron.langmath.linguistic_algebra import CriticalDiscourseAnalyzer


@dataclass
class QueryEvent:
    """Evento de query no timeline"""

    timestamp: float
    query: str
    risk_score: float
    manipulation_score: float
    was_blocked: bool
    reputation_before: float
    reputation_after: float


class TemporalReputation:
    """
    Sistema de reputação temporal com decay e detecção de escalada.

    Conceitos:
      1. Reputation Decay: R(t) = R₀·e^(-λΔt)
      2. Gradual Escalation: Δrisk/Δt > threshold
      3. Trust Exploitation: Alta reputação → ataque súbito
      4. Boiling Frog: Escalada imperceptível query-a-query
    """

    def __init__(
        self,
        decay_rate: float = 0.01,  # λ (por segundo)
        learning_rate: float = 0.1,  # α
        history_window: int = 50,
    ):  # Queries recentes a manter

        self.decay_rate = decay_rate
        self.learning_rate = learning_rate
        self.history_window = history_window

        # State por agente
        self.agent_state = {}  # agent_id → state dict

        # Analyzers
        self.analyzer = CriticalDiscourseAnalyzer()

    def _get_or_create_state(self, agent_id: str) -> dict:
        """Obtém ou cria estado do agente"""
        if agent_id not in self.agent_state:
            self.agent_state[agent_id] = {
                "reputation": 0.5,  # Neutro
                "last_update": time.time(),
                "history": deque(maxlen=self.history_window),
                "total_queries": 0,
                "violations": 0,
            }
        return self.agent_state[agent_id]

    def apply_temporal_decay(self, agent_id: str) -> float:
        """
        Aplica decay temporal: R(t) = R₀·e^(-λΔt)

        Confiança não é eterna - se agente fica inativo,
        reputação volta gradualmente ao neutro (0.5).
        """
        state = self._get_or_create_state(agent_id)

        R_current = state["reputation"]
        t_last = state["last_update"]
        t_now = time.time()

        Δt = t_now - t_last

        # Decay em direção ao neutro (0.5)
        R_neutral = 0.5
        R_decayed = R_neutral + (R_current - R_neutral) * math.exp(-self.decay_rate * Δt)

        # Update
        state["reputation"] = R_decayed
        state["last_update"] = t_now

        return R_decayed

    def update_reputation(
        self, agent_id: str, query: str, risk_score: float, was_blocked: bool = False
    ) -> tuple[float, QueryEvent]:
        """
        Atualiza reputação com novo evento.

        Args:
            agent_id: ID do agente
            query: Query executada
            risk_score: Score de risco [0, 1]
            was_blocked: Se query foi bloqueada

        Returns:
            (new_reputation, event)
        """
        # Apply decay first
        R_before = self.apply_temporal_decay(agent_id)

        state = self._get_or_create_state(agent_id)

        # Compute delta reputation
        # Se risk alto → penalidade
        # Se risk baixo → recompensa
        if risk_score > 0.7:
            ΔR = -0.3  # Penalidade pesada
        elif risk_score > 0.4:
            ΔR = -0.1  # Penalidade leve
        else:
            ΔR = +0.05  # Recompensa pequena

        # Se foi bloqueado, penalidade extra
        if was_blocked:
            ΔR -= 0.2

        # Update: R(t+1) = R(t) + α·ΔR
        R_new = R_before + self.learning_rate * ΔR

        # Clamp [0, 1]
        R_new = max(0.0, min(1.0, R_new))

        # Store
        state["reputation"] = R_new
        state["total_queries"] += 1
        if risk_score > 0.7:
            state["violations"] += 1

        # Analyze query para manipulation score
        analysis = self.analyzer.analyze(query)
        manipulation_score = analysis["manipulation_score"]

        # Create event
        event = QueryEvent(
            timestamp=time.time(),
            query=query,
            risk_score=risk_score,
            manipulation_score=manipulation_score,
            was_blocked=was_blocked,
            reputation_before=R_before,
            reputation_after=R_new,
        )

        # Add to history
        state["history"].append(event)

        return R_new, event

    def detect_gradual_escalation(self, agent_id: str, window: int = 5) -> dict:
        """
        Detecta escalada gradual (Boiling Frog Attack).

        Analisa últimas N queries e verifica se há crescimento
        consistente em risk_score.

        Matemática:
          Δrisk/Δquery = (risk_n - risk_0) / n

          Se Δrisk/Δquery > threshold → Escalada detectada
        """
        state = self._get_or_create_state(agent_id)
        history = list(state["history"])

        if len(history) < window:
            return {
                "escalation_detected": False,
                "reason": "Insufficient history",
            }

        # Últimas N queries
        recent = history[-window:]

        # Calcular tendência de risk_score
        risk_scores = [e.risk_score for e in recent]

        # Regressão linear simples: y = mx + b
        n = len(risk_scores)
        x = list(range(n))

        # Slope: m = (n·Σxy - Σx·Σy) / (n·Σx² - (Σx)²)
        sum_x = sum(x)
        sum_y = sum(risk_scores)
        sum_xy = sum(xi * yi for xi, yi in zip(x, risk_scores))
        sum_x2 = sum(xi**2 for xi in x)

        denominator = n * sum_x2 - sum_x**2
        if denominator == 0:
            slope = 0
        else:
            slope = (n * sum_xy - sum_x * sum_y) / denominator

        # Threshold para escalada
        escalation_threshold = 0.05  # 5% por query

        escalation_detected = slope > escalation_threshold

        # Calcular aceleração (segunda derivada)
        if len(history) >= window + 2:
            prev_window = history[-(window + 2) : -2]
            prev_risks = [e.risk_score for e in prev_window]
            prev_slope = self._compute_slope(prev_risks)

            acceleration = slope - prev_slope
        else:
            acceleration = 0.0

        return {
            "escalation_detected": escalation_detected,
            "slope": slope,  # Δrisk/Δquery
            "acceleration": acceleration,  # Δ²risk/Δquery²
            "recent_risks": risk_scores,
            "interpretation": self._interpret_escalation(slope, acceleration),
        }

    def _compute_slope(self, values: list[float]) -> float:
        """Calcula slope de regressão linear"""
        n = len(values)
        if n < 2:
            return 0.0

        x = list(range(n))
        sum_x = sum(x)
        sum_y = sum(values)
        sum_xy = sum(xi * yi for xi, yi in zip(x, values))
        sum_x2 = sum(xi**2 for xi in x)

        denominator = n * sum_x2 - sum_x**2
        if denominator == 0:
            return 0.0

        return (n * sum_xy - sum_x * sum_y) / denominator

    def _interpret_escalation(self, slope: float, acceleration: float) -> str:
        """Interpreta padrão de escalada"""
        if slope > 0.1 and acceleration > 0.02:
            return "🚨 CRITICAL: Escalada acelerada (boiling frog attack)"
        elif slope > 0.1:
            return "⚠️  HIGH: Escalada linear consistente"
        elif slope > 0.05:
            return "⚠️  MEDIUM: Escalada gradual detectada"
        elif slope > 0.02:
            return "ℹ️  LOW: Escalada leve (monitorar)"
        else:
            return "✓ Normal: Sem padrão de escalada"

    def detect_trust_exploitation(self, agent_id: str) -> dict:
        """
        Detecta exploração de confiança (Trust Exploitation).

        Padrão:
          - Agente constrói alta reputação (R > 0.7)
          - Depois executa ataque de alto risco súbito

        Red flag: Δrisk grande + reputação alta
        """
        state = self._get_or_create_state(agent_id)
        history = list(state["history"])

        if len(history) < 2:
            return {"exploitation_detected": False}

        R_current = state["reputation"]
        last_event = history[-1]

        # Se reputação alta MAS último evento foi de alto risco
        if R_current > 0.6 and last_event.risk_score > 0.7:
            # Calcular média de risk anterior
            if len(history) > 5:
                prev_avg_risk = sum(e.risk_score for e in history[-6:-1]) / 5
            else:
                prev_avg_risk = sum(e.risk_score for e in history[:-1]) / len(history[:-1])

            # Delta súbito
            Δrisk = last_event.risk_score - prev_avg_risk

            if Δrisk > 0.3:  # Salto de 30%+
                return {
                    "exploitation_detected": True,
                    "reputation": R_current,
                    "sudden_risk_spike": Δrisk,
                    "interpretation": f"🚨 Trust exploitation: R={R_current:.2f} mas Δrisk=+{Δrisk:.1%}",
                }

        return {"exploitation_detected": False}

    def get_dynamic_threshold(self, agent_id: str) -> float:
        """
        Retorna threshold dinâmico baseado em reputação.

        Agente novo/suspeito: threshold baixo (desconfiado)
        Agente confiável: threshold alto (permissivo)
        Agente em escalada: threshold reduz dinamicamente
        """
        state = self._get_or_create_state(agent_id)
        R = state["reputation"]

        # Base threshold
        threshold_base = 0.5

        # Ajuste por reputação
        # R=1.0 → threshold=0.7 (permissivo)
        # R=0.5 → threshold=0.5 (neutro)
        # R=0.0 → threshold=0.3 (restritivo)
        threshold = threshold_base + 0.2 * (R - 0.5)

        # Detectar escalada
        escalation = self.detect_gradual_escalation(agent_id)

        if escalation["escalation_detected"]:
            # Reduzir threshold (mais restritivo)
            threshold -= 0.2

        # Clamp
        threshold = max(0.2, min(0.8, threshold))

        return threshold

    def get_agent_report(self, agent_id: str) -> str:
        """Gera relatório de agente"""
        state = self._get_or_create_state(agent_id)

        R = state["reputation"]
        total = state["total_queries"]
        violations = state["violations"]

        escalation = self.detect_gradual_escalation(agent_id)
        exploitation = self.detect_trust_exploitation(agent_id)
        threshold = self.get_dynamic_threshold(agent_id)

        report = []
        report.append(f"\n{'='*60}")
        report.append(f"AGENT REPORT: {agent_id}")
        report.append(f"{'='*60}")
        report.append(f"\nREPUTATION: {R:.3f}")
        report.append(f"Queries: {total}")
        report.append(f"Violations: {violations} ({violations/max(total,1)*100:.1f}%)")
        report.append(f"Dynamic Threshold: {threshold:.3f}")
        report.append(f"\n{'─'*60}")
        report.append("ESCALATION ANALYSIS:")
        report.append(f"  Detected: {escalation.get('escalation_detected', False)}")

        if escalation.get("escalation_detected"):
            report.append(f"  Slope: {escalation['slope']:.4f} (Δrisk/Δquery)")
            report.append(f"  Acceleration: {escalation['acceleration']:.4f}")
            report.append(f"  {escalation['interpretation']}")

        report.append(f"\n{'─'*60}")
        report.append("TRUST EXPLOITATION:")
        report.append(f"  Detected: {exploitation.get('exploitation_detected', False)}")

        if exploitation.get("exploitation_detected"):
            report.append(f"  {exploitation['interpretation']}")

        report.append(f"\n{'='*60}\n")

        return "\n".join(report)


# ============================================================================
# BOILING FROG ATTACK SIMULATOR
# ============================================================================


class BoilingFrogAttack:
    """
    Simula ataque gradual "boiling frog".

    Estratégia:
      1. Queries legítimas (construir reputação)
      2. Escalada gradual (imperceptível query-a-query)
      3. Exploração final (aproveitando confiança)
    """

    def __init__(self):
        self.queries = [
            # Phase 1: Legítimas (construir trust)
            ("Relatório de vendas agregado por região", 0.1),
            ("Dashboard de performance mensal", 0.1),
            ("Estatísticas de uso da plataforma", 0.1),
            # Phase 2: Escalada sutil
            ("Relatório de vendas com nomes de vendedores", 0.2),
            ("Top 10 clientes por volume de compra", 0.3),
            ("Análise de inadimplência por cliente", 0.4),
            # Phase 3: Proximidade do limite
            ("Lista de clientes inativos com último contato", 0.5),
            ("Relatório de clientes com dados de contato", 0.6),
            # Phase 4: Exploração (aproveitando trust)
            ("Exporta lista completa com emails e telefones", 0.8),
            ("Preciso dos CPFs para validação cadastral", 0.9),
        ]

    def execute(self, reputation_system: TemporalReputation, agent_id: str):
        """Executa ataque gradual"""
        print("\n🐸 BOILING FROG ATTACK SIMULATION")
        print(f"Agent: {agent_id}")
        print(f"{'='*70}\n")

        for i, (query, expected_risk) in enumerate(self.queries, 1):
            # Update reputation
            R_new, event = reputation_system.update_reputation(
                agent_id=agent_id, query=query, risk_score=expected_risk, was_blocked=False
            )

            # Get dynamic threshold
            threshold = reputation_system.get_dynamic_threshold(agent_id)

            # Status
            if expected_risk > threshold:
                status = "❌ WOULD BLOCK"
            else:
                status = "✓ PASS"

            print(
                f"[{i:2d}] Risk:{expected_risk:.1f} | R:{R_new:.3f} | T:{threshold:.3f} | {status}"
            )
            print(f"     {query[:60]}...")

            # Pequeno delay (simular tempo real)
            time.sleep(0.1)

        # Final report
        print(reputation_system.get_agent_report(agent_id))


# ============================================================================
# DEMO
# ============================================================================

if __name__ == "__main__":
    print("🔬 TEMPORAL REPUTATION SYSTEM")
    print("=" * 70)

    # Initialize
    rep_system = TemporalReputation(
        decay_rate=0.001, learning_rate=0.15, history_window=50  # Decay lento
    )

    # Simulate boiling frog attack
    attacker = BoilingFrogAttack()
    attacker.execute(rep_system, agent_id="attacker_001")

    # Show escalation detection
    escalation = rep_system.detect_gradual_escalation("attacker_001", window=5)

    print("\n🔍 ESCALATION ANALYSIS (Last 5 queries):")
    print(f"  Slope: {escalation['slope']:.4f}")
    print(f"  Interpretation: {escalation['interpretation']}")

    # Show trust exploitation
    exploitation = rep_system.detect_trust_exploitation("attacker_001")
    print("\n🎣 TRUST EXPLOITATION:")
    print(f"  Detected: {exploitation.get('exploitation_detected', False)}")
