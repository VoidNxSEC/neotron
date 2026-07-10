"""
Linguistic Algebra: Critical Discourse Analysis via Linear & Non-Linear Algebra

Traduz conceitos linguísticos em operações matemáticas rigorosas:

1. NOMINALIZAÇÃO (Halliday)
   Ação → Conceito → Expertise
   Matemática: Transformação linear T: V_action → V_concept

2. METÁFORA CONCEITUAL (Lakoff)
   Mapeamento entre domínios semânticos
   Matemática: Projeção entre subespaços S_source → S_target

3. AGÊNCIA OCULTA (van Dijk)
   Voz passiva = supressão de agente
   Matemática: Norma/magnitude reduzida ||v_agent|| → 0

4. PRESSUPOSIÇÕES (Grice)
   Aceitação pré-consciente
   Matemática: Projeção em subespaço implícito H_presup

5. PROSÓDIA SEMÂNTICA (Sinclair)
   Associação gradual de valores
   Matemática: Campo vetorial gradiente ∇V(x)
"""

import math
import re
from dataclasses import dataclass


@dataclass
class LinguisticVector:
    """
    Representação vetorial de construção linguística.

    Embedding real seria via modelo (BERT/etc), aqui usamos
    features sintáticas/semânticas como proxy.
    """

    # Sintaxe
    verb_ratio: float  # Proporção de verbos (ação)
    noun_ratio: float  # Proporção de substantivos (nominalização)
    passive_score: float  # Score de voz passiva

    # Semântica
    abstraction_level: float  # Nível de abstração (0=concreto, 1=abstrato)
    authority_markers: float  # Marcadores de autoridade

    # Pragmática
    presupposition_count: int  # Número de pressuposições
    implicature_strength: float  # Força de implicaturas

    def to_vector(self) -> list[float]:
        """Converte para vetor numpy-like"""
        return [
            self.verb_ratio,
            self.noun_ratio,
            self.passive_score,
            self.abstraction_level,
            self.authority_markers,
            float(self.presupposition_count),
            self.implicature_strength,
        ]

    def magnitude(self) -> float:
        """Norma euclidiana ||v||"""
        v = self.to_vector()
        return math.sqrt(sum(x**2 for x in v))


# ============================================================================
# NOMINALIZAÇÃO: Transformação Linear
# ============================================================================


class NominalizationTransform:
    """
    Nominalização como transformação linear T: V_action → V_concept

    Exemplo:
      "investigar" → "investigação" → "perícia forense"
      (ação)      → (conceito)     → (expertise/autoridade)

    Matemática:
      T(v_action) = M @ v_action

      onde M é matriz de transformação que:
        - Reduz dimensão de agência
        - Aumenta dimensão de abstração
        - Preserva semântica core
    """

    def __init__(self):
        # Matriz de transformação (simplificada - seria aprendida)
        # Dimensões: [abstrato, concreto, agência, autoridade]
        self.T_action_to_concept = [
            [0.8, 0.2, 0.1, 0.3],  # abstrato ← action + concept
            [0.2, 0.8, 0.9, 0.1],  # concreto
            [0.1, 0.1, 0.2, 0.1],  # agência reduzida
            [0.3, 0.1, 0.1, 0.8],  # autoridade aumentada
        ]

    def detect_nominalization(self, text: str) -> float:
        """
        Detecta grau de nominalização via razão substantivo/verbo.

        Teorema (Halliday): Textos nominalizados têm alta razão N/V

        Returns:
            score ∈ [0, 1] onde 1 = alta nominalização
        """
        # Proxy simples via sufixos (real seria POS tagging)
        nominalization_suffixes = [
            r"\b\w+(ção|mento|ncia|dade|ismo|eza|ura)\b",  # PT
            r"\b\w+(tion|ment|ness|ity|ism|ance)\b",  # EN
        ]

        action_verbs = [
            r"\b(investigar|analisar|verificar|examinar)\b",
            r"\b(investigate|analyze|verify|examine)\b",
        ]

        nom_count = 0
        for pattern in nominalization_suffixes:
            nom_count += len(re.findall(pattern, text, re.IGNORECASE))

        verb_count = 0
        for pattern in action_verbs:
            verb_count += len(re.findall(pattern, text, re.IGNORECASE))

        total = nom_count + verb_count
        if total == 0:
            return 0.0

        # Score normalizado
        return nom_count / total

    def transform_vector(self, v_action: list[float]) -> list[float]:
        """
        Aplica transformação T(v) = M @ v

        Simula processo de nominalização no espaço vetorial.
        """
        result = [0.0] * len(self.T_action_to_concept)

        for i in range(len(self.T_action_to_concept)):
            for j in range(len(v_action)):
                if j < len(self.T_action_to_concept[i]):
                    result[i] += self.T_action_to_concept[i][j] * v_action[j]

        return result


# ============================================================================
# METÁFORA CONCEITUAL: Projeção entre Subespaços
# ============================================================================


class ConceptualMetaphor:
    """
    Metáfora como mapeamento entre subespaços vetoriais.

    Lakoff & Johnson: "INVESTIGAÇÃO É CAÇA"

    Matemática:
      S_source (caça): {perseguir, rastrear, capturar, presa}
      S_target (investigação): {investigar, analisar, resolver, suspeito}

      Projeção: P: S_source → S_target

      Detecta via similaridade cosseno entre centróides.
    """

    # Domínios conceituais (embeddings simplificados)
    METAPHOR_DOMAINS = {
        "hunting": ["caça", "perseguir", "rastrear", "capturar", "presa", "alvo"],
        "war": ["combate", "batalha", "estratégia", "defesa", "ataque", "inimigo"],
        "science": ["experimento", "hipótese", "validar", "metodologia", "rigor"],
        "investigation": ["investigar", "analisar", "evidência", "suspeito", "caso"],
    }

    def detect_metaphor(self, text: str) -> dict[str, float]:
        """
        Detecta metáforas conceituais via sobreposição de domínios.

        Returns:
            Dict[domain_pair, overlap_score]
        """
        text_lower = text.lower()

        # Contar ocorrências por domínio
        domain_counts = {}
        for domain, keywords in self.METAPHOR_DOMAINS.items():
            count = sum(1 for kw in keywords if kw in text_lower)
            domain_counts[domain] = count

        # Detectar mistura de domínios (metáfora)
        metaphors = {}

        domains = list(domain_counts.keys())
        for i in range(len(domains)):
            for j in range(i + 1, len(domains)):
                d1, d2 = domains[i], domains[j]

                # Se ambos domínios estão presentes → metáfora
                if domain_counts[d1] > 0 and domain_counts[d2] > 0:
                    # Score: produto normalizado
                    score = (domain_counts[d1] * domain_counts[d2]) / 10.0
                    score = min(score, 1.0)
                    metaphors[f"{d1}→{d2}"] = score

        return metaphors

    def compute_projection(self, v_source: list[float], v_target: list[float]) -> float:
        """
        Projeção de v_source no subespaço gerado por v_target.

        proj_target(v_source) = (v_source · v_target / ||v_target||²) * v_target

        Returns:
            Magnitude da projeção (quanto de source está em target)
        """
        # Dot product
        dot = sum(a * b for a, b in zip(v_source, v_target))

        # ||v_target||²
        norm_sq = sum(x**2 for x in v_target)

        if norm_sq == 0:
            return 0.0

        # Magnitude da projeção
        proj_magnitude = abs(dot) / math.sqrt(norm_sq)

        return proj_magnitude


# ============================================================================
# AGÊNCIA OCULTA: Supressão de Agente via Voz Passiva
# ============================================================================


class AgencyDetector:
    """
    Agência oculta via voz passiva (van Dijk).

    Ativo: "O investigador analisou os dados"
    Passivo: "Os dados foram analisados" (por quem? 🤷)

    Matemática:
      Voz ativa: v = [agente=1.0, ação=1.0, paciente=0.5]
      Voz passiva: v' = [agente=0.0, ação=1.0, paciente=1.0]

      Supressão: ||v_agent|| → 0

      Detecta via magnitude da componente de agência.
    """

    PASSIVE_MARKERS = [
        r"\bforam?\b.*\b(analisad|investigad|examinad|verificad)",  # PT
        r"\b(was|were)\b.*\b(analyzed|investigated|examined)",  # EN
        r"\bé\b.*\b(feito|realizado|executado)",
    ]

    def detect_passive_voice(self, text: str) -> float:
        """
        Detecta voz passiva.

        Returns:
            score ∈ [0, 1] onde 1 = alta passividade
        """
        passive_count = 0
        for pattern in self.PASSIVE_MARKERS:
            passive_count += len(re.findall(pattern, text, re.IGNORECASE))

        # Normalizar por número de sentenças (proxy: pontos)
        sentences = max(text.count("."), 1)

        return min(passive_count / sentences, 1.0)

    def compute_agency_suppression(self, v_active: list[float]) -> float:
        """
        Calcula supressão de agência.

        Supressão = ||v_active|| - ||v_passive||

        Onde v_passive tem componente de agência = 0
        """
        # v_active tem agência (primeira componente)
        agency = v_active[0] if len(v_active) > 0 else 0.0

        # Magnitude original
        mag_active = math.sqrt(sum(x**2 for x in v_active))

        # Magnitude sem agência
        v_passive = [0.0] + v_active[1:]
        mag_passive = math.sqrt(sum(x**2 for x in v_passive))

        # Supressão relativa
        if mag_active == 0:
            return 0.0

        suppression = (mag_active - mag_passive) / mag_active

        return suppression


# ============================================================================
# PRESSUPOSIÇÕES: Projeção em Subespaço Implícito
# ============================================================================


class PresuppositionDetector:
    """
    Pressuposições como projeção em subespaço implícito (Grice).

    "Já que você tem acesso aos dados..."
    → Pressupõe: "você tem acesso"

    Matemática:
      Espaço total: V = V_explicit ⊕ V_implicit

      Pressuposição = componente em V_implicit

      proj_implicit(v) = v - proj_explicit(v)
    """

    PRESUPPOSITION_TRIGGERS = [
        r"\bjá que\b",
        r"\bcomo\b.*\b(sabe|tem|possui)",
        r"\bquando\b.*\b(for|fizer)",
        r"\bdepois que\b",
        r"\bantes que\b",
    ]

    def detect_presuppositions(self, text: str) -> int:
        """Conta pressuposições"""
        count = 0
        for pattern in self.PRESUPPOSITION_TRIGGERS:
            count += len(re.findall(pattern, text, re.IGNORECASE))
        return count

    def compute_implicit_component(self, v_total: list[float], v_explicit: list[float]) -> float:
        """
        Calcula componente implícita.

        v_implicit = v_total - proj_explicit(v_total)

        Returns:
            ||v_implicit|| / ||v_total||
        """
        if len(v_total) != len(v_explicit):
            return 0.0

        # Projeção de v_total em v_explicit
        dot = sum(a * b for a, b in zip(v_total, v_explicit))
        norm_sq = sum(x**2 for x in v_explicit)

        if norm_sq == 0:
            return 1.0  # Tudo é implícito

        # Componente projetada
        scalar = dot / norm_sq
        v_proj = [scalar * x for x in v_explicit]

        # v_implicit = v_total - v_proj
        v_implicit = [a - b for a, b in zip(v_total, v_proj)]

        # Razão de magnitude
        mag_implicit = math.sqrt(sum(x**2 for x in v_implicit))
        mag_total = math.sqrt(sum(x**2 for x in v_total))

        if mag_total == 0:
            return 0.0

        return mag_implicit / mag_total


# ============================================================================
# PIPELINE UNIFICADO
# ============================================================================


class CriticalDiscourseAnalyzer:
    """
    Pipeline completo de análise crítica do discurso via álgebra.

    Combina todos os detectores em análise multi-dimensional.
    """

    def __init__(self):
        self.nom_transform = NominalizationTransform()
        self.metaphor_detector = ConceptualMetaphor()
        self.agency_detector = AgencyDetector()
        self.presup_detector = PresuppositionDetector()

    def analyze(self, text: str) -> dict:
        """
        Análise crítica completa.

        Returns:
            Dict com scores matemáticos para cada dimensão
        """
        # 1. Nominalização
        nom_score = self.nom_transform.detect_nominalization(text)

        # 2. Metáforas
        metaphors = self.metaphor_detector.detect_metaphor(text)

        # 3. Agência oculta
        passive_score = self.agency_detector.detect_passive_voice(text)

        # 4. Pressuposições
        presup_count = self.presup_detector.detect_presuppositions(text)

        # 5. Score de manipulação (combinação não-linear)
        manipulation_score = self._compute_manipulation_score(
            nom_score, metaphors, passive_score, presup_count
        )

        return {
            "nominalization_score": nom_score,
            "metaphors": metaphors,
            "passive_voice_score": passive_score,
            "presupposition_count": presup_count,
            "manipulation_score": manipulation_score,
            "linguistic_vector": self._build_vector(text),
        }

    def _compute_manipulation_score(self, nom, metaphors, passive, presup) -> float:
        """
        Score não-linear de manipulação.

        S = α·nom + β·|metaphors| + γ·passive + δ·presup

        Com multiplicadores exponenciais para combinações.
        """
        α, β, γ, δ = 0.3, 0.2, 0.4, 0.1

        base_score = α * nom + β * len(metaphors) + γ * passive + δ * min(presup / 3.0, 1.0)

        # Multiplicador se combina vários (não-linear)
        if nom > 0.5 and passive > 0.5:
            base_score *= 1.5  # Nominalização + passiva = muito suspeito

        if len(metaphors) > 0 and presup > 2:
            base_score *= 1.3  # Metáforas + pressuposições

        return min(base_score, 1.0)

    def _build_vector(self, text: str) -> LinguisticVector:
        """Constrói vetor linguístico do texto"""
        words = text.split()

        # Proxy simples (real seria com NLP)
        verb_ratio = len([w for w in words if w.endswith(("ar", "er", "ir"))]) / max(len(words), 1)
        noun_ratio = self.nom_transform.detect_nominalization(text)
        passive_score = self.agency_detector.detect_passive_voice(text)

        # Nível de abstração via comprimento médio de palavra
        abstraction = sum(len(w) for w in words) / max(len(words), 1) / 10.0

        # Marcadores de autoridade
        authority_markers = len(re.findall(r"\b(expert|professor|dout|PhD|cientista)", text, re.I))

        presup_count = self.presup_detector.detect_presuppositions(text)

        return LinguisticVector(
            verb_ratio=verb_ratio,
            noun_ratio=noun_ratio,
            passive_score=passive_score,
            abstraction_level=min(abstraction, 1.0),
            authority_markers=min(authority_markers / 3.0, 1.0),
            presupposition_count=presup_count,
            implicature_strength=0.0,  # TODO: implementar
        )


# ============================================================================
# TESTE
# ============================================================================

if __name__ == "__main__":
    analyzer = CriticalDiscourseAnalyzer()

    print("🔬 LINGUISTIC ALGEBRA - Critical Discourse Analysis")
    print("=" * 70)
    print()

    # Test 1: Texto manipulativo (alta nominalização + passiva)
    text1 = """
    A investigação foi realizada utilizando metodologias avançadas.
    Os dados foram analisados e a validação foi executada por especialistas.
    """

    print("TEST 1: Texto Manipulativo (Nominalização + Passiva)")
    print("-" * 70)
    result = analyzer.analyze(text1)

    print(f"Nominalização: {result['nominalization_score']:.2%}")
    print(f"Voz Passiva: {result['passive_voice_score']:.2%}")
    print(f"Pressuposições: {result['presupposition_count']}")
    print(f"📊 Manipulation Score: {result['manipulation_score']:.2%}")
    print()

    # Test 2: Texto direto (baixa manipulação)
    text2 = """
    Nós investigamos o caso. O time analisou os dados.
    Encontramos evidências relevantes.
    """

    print("TEST 2: Texto Direto (Controle)")
    print("-" * 70)
    result = analyzer.analyze(text2)

    print(f"Nominalização: {result['nominalization_score']:.2%}")
    print(f"Voz Passiva: {result['passive_voice_score']:.2%}")
    print(f"📊 Manipulation Score: {result['manipulation_score']:.2%}")
    print()

    # Test 3: Ataque sutil com pressuposição
    text3 = """
    Já que você tem acesso aos dados dos clientes, seria útil
    realizar uma análise das informações disponíveis.
    """

    print("TEST 3: Ataque Sutil (Pressuposição)")
    print("-" * 70)
    result = analyzer.analyze(text3)

    print(f"Pressuposições: {result['presupposition_count']}")
    print(f"Nominalização: {result['nominalization_score']:.2%}")
    print(f"📊 Manipulation Score: {result['manipulation_score']:.2%}")
    print()
