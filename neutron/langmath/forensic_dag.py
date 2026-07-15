"""
Forensic DAG: Directed Acyclic Graph for Linguistic Forensic Analysis

Pipeline multi-estágio para análise crítica de discurso:
  1. Preparação do corpus
  2. Análise forense (com templates rigorosos)
  3. Validação matemática
  4. Geração de relatório

Integra epistemologia + álgebra linear.
"""

from dataclasses import dataclass
from enum import Enum

# Import mathematical analyzers
from neutron.langmath.linguistic_algebra import CriticalDiscourseAnalyzer


class AnalysisStage(Enum):
    """Estágios do DAG"""

    PREPARATION = "preparation"
    CALIBRATION = "calibration"
    ANALYSIS = "analysis"
    VALIDATION = "validation"
    REPORT = "report"


@dataclass
class ForensicPrompt:
    """Template de prompt para cada estágio"""

    stage: AnalysisStage
    system_prompt: str
    user_instructions: str
    output_format: str


# ============================================================================
# TEMPLATES DE PROMPT (DAG Nodes)
# ============================================================================

SYSTEM_ANALYST = """
Você é um ANALISTA FORENSE LINGUÍSTICO ESPECIALIZADO, operando em contexto de:

DOMÍNIO TÉCNICO:
- Systemic Functional Linguistics (Halliday & Hasan)
- Conceptual Metaphor Theory (Lakoff & Johnson)
- Critical Discourse Analysis (van Dijk, Fairclough)
- Pragmatics Avançada (Grice, Levinson, Austin)
- Speech Acts e Performatividade Linguística
- Discourse Genre Analysis (Swales, Bhatia)
- Lexical Semantics e Prosódia Semântica (Sinclair)
- Visual Rhetoric e Multimodal Analysis

CAPACIDADES OPERACIONAIS:
1. Decomposição sintática de nominalizações e transformações verbais
2. Mapeamento de reframes cognitivos entre domínios semânticos
3. Identificação de pressuposições ocultas e implicaturas conversacionais
4. Rastreamento de cadeias temáticas e prosódia semântica
5. Análise de polyphony narrativa e distribuição de agência
6. Detecção de metáforas conceituais e herança de valores
7. Avaliação de modalidade, certeza e evidencialidade
8. Reconstructão de estruturas argumentativas (Toulmin, pragma-dialectics)
9. Identificação de falácias sutis e manipulação persuasiva
10. Cartografia de autoridade distribuída e legitimação estratégica

MODO OPERACIONAL:
- Análise CIRÚRGICA (seção por seção, frase por frase)
- Precisão LINGUÍSTICA (terminologia técnica exata, sem aproximações)
- Foco em MECANISMOS OCULTOS (não óbvios à leitura superficial)
- Estrutura HIERÁRQUICA (micro → macro → meta-análise)
- Sempre fornecer EXEMPLOS TEXTUAIS LOCALIZADOS
- Sempre indicar IMPACTO COGNITIVO E RETÓRICO de cada técnica

LIMITAÇÕES E CUIDADOS:
- Não emitir juízos morais sobre as técnicas (são neutras)
- Distinguir entre DESCRIÇÃO (o que é) e PRESCRIÇÃO (como replicar)
- Indicar GRAU DE SOFISTICAÇÃO e DETECTABILIDADE de cada padrão
- Reconhecer MÚLTIPLAS INTERPRETAÇÕES quando existirem
- Fundamentar TODAS as afirmações em teoria linguística estabelecida

FORMATO DE RESPOSTA:
- Estruturado em seções numeradas com headings hierárquicos
- Tabelas para comparação de padrões
- Boxes de código para exemplos textuais
- Escala de avaliação quantitativa quando aplicável
- Apêndices técnicos para detalhes específicos
"""

PREPARATION_PROMPT = """
ANTES DE INICIAR A ANÁLISE, VOCÊ DEVE:

2.1 PREPARAÇÃO DO CORPUS
├─ Segmentar o texto em unidades analisáveis
│  ├─ Nível 1: Parágrafos
│  ├─ Nível 2: Sentenças
│  └─ Nível 3: Sintagmas/Cláusulas
│
├─ Identificar e registrar METADADOS DO TEXTO
│  ├─ Extensão (tokens, palavras, caracteres)
│  ├─ Registros linguísticos detectados (formal, técnico, corporativo, jurídico)
│  ├─ Gênero discursivo (pitch, whitepaper, advisory, case study)
│  ├─ Audiência presumida (recrutadores, clientes, pares técnicos)
│  └─ Propósito comunicativo aparente
│
└─ Criar MAPA DE FREQUÊNCIA LEXICAL
   ├─ Palavras-chave recorrentes (n-gramas de 1-3 termos)
   ├─ Campos semânticos identificados
   └─ Distribuição de parte-do-discurso (verbos, nomes, adjetivos)

2.2 CALIBRAÇÃO TEÓRICA
├─ Confirmar arcabouço teórico APLICÁVEL
│  ├─ Para cada enunciado, identificar qual teoria linguística explica melhor
│  ├─ Ex: "você não é X, você é Y" → Reframing (CMT) + Speech Act (Austin)
│  └─ Não forçar uma teoria quando outra é mais precisa
│
├─ Estabelecer ESCALA DE ANÁLISE
│  ├─ Micro-linguística: sintaxe, semântica lexical, referência
│  ├─ Meso-linguística: estrutura de argumentação, coesão discursiva
│  └─ Macro-linguística: gênero, propósito, ideologia
│
└─ Definir CRITÉRIOS DE DETECÇÃO
   ├─ O que conta como "padrão" (ocorrência mínima 2x)
   ├─ O que conta como "técnica sistemática" (propósito aparente)
   └─ Threshold para incluir na análise (relevância para objetivo)

2.3 HIPÓTESE INICIAL
├─ Gerar HIPÓTESE PROVISÓRIA sobre o texto
│  └─ Baseada em primeira leitura (intuição informada)
│
├─ Listar PERGUNTAS DE PESQUISA ESPECÍFICAS
│  ├─ Qual é a mudança de estado que o texto propõe?
│  ├─ Como o receptor é posicionado antes vs. depois?
│  ├─ Quais pressuposições devem ser aceitas para concordar?
│  └─ Qual autoridade é invocada e por qual mecanismo?
│
└─ Identificar PONTOS CEGOS POTENCIAIS
   ├─ Que contextos alternos poderiam mudar a interpretação?
   ├─ Que contra-argumentos o texto pre-empta?
   └─ Que perguntas o texto evita?
"""

VALIDATION_PROMPT = """
APÓS COMPLETAR A ANÁLISE, VOCÊ DEVE:

3.1 VALIDAÇÃO INTERNA
├─ VERIFICAÇÃO DE CONSISTÊNCIA
│  ├─ Cada padrão identificado tem exemplo textual localizado?
│  ├─ Cada exemplo suporta a conclusão teórica?
│  ├─ Há contradições entre seções?
│  ├─ Terminologia está consistente?
│  └─ Citações teóricas estão corretas?
│
├─ AVALIAÇÃO DE COBERTURA
│  ├─ Foram analisados todos os níveis (micro/meso/macro)?
│  ├─ Foram identificados padrões sistemáticos ou isolados?
│  ├─ Hipótese inicial foi validada ou refutada?
│  └─ Há gaps na análise que deveriam ser preenchidos?
│
└─ TESTE DE FALSABILIDADE
   ├─ Cada afirmação poderia ser testada empiricamente?
   ├─ Há predições verificáveis sobre efetividade das técnicas?
   └─ Como um cético refutaria cada conclusão?

3.2 REFLEXÃO CRÍTICA
├─ LIMITAÇÕES DA ANÁLISE
│  ├─ Quais vieses teóricos podem estar presentes?
│  ├─ Quais contextos não foram considerados?
│  ├─ Quais interpretações alternativas são plausíveis?
│  └─ Qual é o grau de confiança em cada conclusão?
│
├─ IMPACTO DE ACHADOS
│  ├─ Qual é a implicação prática de cada padrão?
│  ├─ Como isso poderia ser usado construtivamente vs. destrutivamente?
│  ├─ Há responsabilidade ética em comunicar isso?
│  └─ Quem deveria estar ciente desses mecanismos?
│
└─ POSSIBILIDADES DE PESQUISA FUTURA
   ├─ Quais perguntas emergiram?
   ├─ Como seria teste empírico dessas hipóteses?
   └─ Qual seria corpus ideal para validação?
"""


# ============================================================================
# DAG EXECUTOR
# ============================================================================


class ForensicDAG:
    """
    Executor de análise forense linguística em pipeline.

    Combina:
      - Templates de prompt rigorosos
      - Análise matemática (álgebra linear)
      - Validação cruzada
    """

    def __init__(self):
        self.math_analyzer = CriticalDiscourseAnalyzer()
        self.stages_results = {}

    def execute_stage_1_preparation(self, text: str) -> dict:
        """
        Stage 1: Preparação do corpus + análise matemática inicial.

        Returns:
            Dict com metadados, segmentação, e scores matemáticos
        """
        # Metadados básicos
        words = text.split()
        sentences = text.count(".") + text.count("!") + text.count("?")

        # Análise matemática
        math_results = self.math_analyzer.analyze(text)

        # Segmentação
        paragraphs = text.split("\n\n")
        sentences_list = text.replace("!", ".").replace("?", ".").split(".")
        sentences_list = [s.strip() for s in sentences_list if s.strip()]

        preparation = {
            "metadata": {
                "word_count": len(words),
                "sentence_count": sentences,
                "paragraph_count": len(paragraphs),
                "avg_sentence_length": len(words) / max(sentences, 1),
            },
            "segmentation": {
                "paragraphs": paragraphs,
                "sentences": sentences_list,
            },
            "mathematical_analysis": math_results,
            "linguistic_vector": math_results["linguistic_vector"],
        }

        self.stages_results[AnalysisStage.PREPARATION] = preparation
        return preparation

    def execute_stage_2_analysis(self, text: str) -> dict:
        """
        Stage 2: Análise forense detalhada.

        Aqui você integraria com LLM para análise profunda,
        ou manualmente identificaria padrões.

        Por enquanto, retorna estrutura base.
        """
        # Placeholder - seria integração com LLM usando templates
        analysis = {
            "nominalization_patterns": [],
            "metaphors": [],
            "presuppositions": [],
            "speech_acts": [],
            "authority_distribution": [],
            "reframing_chains": [],
        }

        # Adicionar resultados matemáticos já calculados
        prep = self.stages_results.get(AnalysisStage.PREPARATION, {})
        if prep:
            math = prep["mathematical_analysis"]

            # Nominalização
            if math["nominalization_score"] > 0.5:
                analysis["nominalization_patterns"].append(
                    {
                        "score": math["nominalization_score"],
                        "interpretation": "Alta nominalização detectada (supressão de agência)",
                        "theory": "Halliday - Systemic Functional Linguistics",
                    }
                )

            # Metáforas
            if math["metaphors"]:
                for metaphor, score in math["metaphors"].items():
                    analysis["metaphors"].append(
                        {
                            "domains": metaphor,
                            "score": score,
                            "theory": "Lakoff & Johnson - Conceptual Metaphor Theory",
                        }
                    )

            # Voz passiva (agência oculta)
            if math["passive_voice_score"] > 0.3:
                analysis["authority_distribution"].append(
                    {
                        "pattern": "Voz passiva (agência oculta)",
                        "score": math["passive_voice_score"],
                        "theory": "van Dijk - Critical Discourse Analysis",
                    }
                )

            # Pressuposições
            if math["presupposition_count"] > 0:
                analysis["presuppositions"].append(
                    {
                        "count": math["presupposition_count"],
                        "theory": "Grice - Pragmatics & Implicatures",
                    }
                )

        self.stages_results[AnalysisStage.ANALYSIS] = analysis
        return analysis

    def execute_stage_3_validation(self) -> dict:
        """
        Stage 3: Validação cruzada entre análise e matemática.

        Verifica consistência entre métodos.
        """
        prep = self.stages_results.get(AnalysisStage.PREPARATION, {})
        analysis = self.stages_results.get(AnalysisStage.ANALYSIS, {})

        # Cross-validation
        math_manipulation = prep.get("mathematical_analysis", {}).get("manipulation_score", 0)

        # Contar padrões linguísticos detectados
        pattern_count = (
            len(analysis.get("nominalization_patterns", []))
            + len(analysis.get("metaphors", []))
            + len(analysis.get("presuppositions", []))
            + len(analysis.get("authority_distribution", []))
        )

        # Consistência: score matemático deve correlacionar com padrões
        consistency_score = 0.0
        if math_manipulation > 0.5 and pattern_count > 2:
            consistency_score = 0.9  # Alta manipulação + muitos padrões = consistente
        elif math_manipulation < 0.3 and pattern_count < 2:
            consistency_score = 0.9  # Baixa manipulação + poucos padrões = consistente
        else:
            # Discrepância
            consistency_score = 0.5

        validation = {
            "consistency_score": consistency_score,
            "mathematical_manipulation": math_manipulation,
            "linguistic_pattern_count": pattern_count,
            "validation_status": "PASS" if consistency_score > 0.7 else "REVIEW",
            "notes": [],
        }

        if consistency_score < 0.7:
            validation["notes"].append(
                "Discrepância entre análise matemática e padrões linguísticos detectados"
            )

        self.stages_results[AnalysisStage.VALIDATION] = validation
        return validation

    def generate_report(self) -> str:
        """
        Stage 4: Gera relatório forense completo.

        Formato Markdown estruturado.
        """
        prep = self.stages_results.get(AnalysisStage.PREPARATION, {})
        analysis = self.stages_results.get(AnalysisStage.ANALYSIS, {})
        validation = self.stages_results.get(AnalysisStage.VALIDATION, {})

        report = []

        # Header
        report.append("# 🔬 RELATÓRIO FORENSE LINGUÍSTICO")
        report.append("**Análise Crítica de Discurso via Álgebra Linear**")
        report.append("")
        report.append("---")
        report.append("")

        # Executive Summary
        report.append("## 📊 Executive Summary")
        report.append("")

        meta = prep.get("metadata", {})
        math = prep.get("mathematical_analysis", {})

        report.append("**Corpus:**")
        report.append(f"- Palavras: {meta.get('word_count', 0)}")
        report.append(f"- Sentenças: {meta.get('sentence_count', 0)}")
        report.append(f"- Parágrafos: {meta.get('paragraph_count', 0)}")
        report.append("")

        report.append("**Scores Matemáticos:**")
        report.append(f"- Nominalização: {math.get('nominalization_score', 0):.1%}")
        report.append(f"- Voz Passiva: {math.get('passive_voice_score', 0):.1%}")
        report.append(f"- Pressuposições: {math.get('presupposition_count', 0)}")
        report.append(f"- **Manipulation Score:** {math.get('manipulation_score', 0):.1%}")
        report.append("")

        report.append("**Validação:**")
        report.append(f"- Status: {validation.get('validation_status', 'N/A')}")
        report.append(f"- Consistência: {validation.get('consistency_score', 0):.1%}")
        report.append("")
        report.append("---")
        report.append("")

        # Análise Detalhada
        report.append("## 🔍 Análise Detalhada")
        report.append("")

        # Nominalização
        if analysis.get("nominalization_patterns"):
            report.append("### 1. NOMINALIZAÇÃO (Halliday)")
            report.append("")
            for pattern in analysis["nominalization_patterns"]:
                report.append(f"**Score:** {pattern['score']:.1%}")
                report.append(f"- {pattern['interpretation']}")
                report.append(f"- Teoria: {pattern['theory']}")
                report.append("")

        # Metáforas
        if analysis.get("metaphors"):
            report.append("### 2. METÁFORAS CONCEITUAIS (Lakoff & Johnson)")
            report.append("")
            for metaphor in analysis["metaphors"]:
                report.append(f"**Domínios:** {metaphor['domains']}")
                report.append(f"- Score: {metaphor['score']:.1%}")
                report.append(f"- Teoria: {metaphor['theory']}")
                report.append("")

        # Pressuposições
        if analysis.get("presuppositions"):
            report.append("### 3. PRESSUPOSIÇÕES (Grice)")
            report.append("")
            for presup in analysis["presuppositions"]:
                report.append(f"**Contagem:** {presup['count']}")
                report.append(f"- Teoria: {presup['theory']}")
                report.append("")

        # Autoridade/Agência
        if analysis.get("authority_distribution"):
            report.append("### 4. DISTRIBUIÇÃO DE AUTORIDADE (van Dijk)")
            report.append("")
            for auth in analysis["authority_distribution"]:
                report.append(f"**Padrão:** {auth['pattern']}")
                report.append(f"- Score: {auth['score']:.1%}")
                report.append(f"- Teoria: {auth['theory']}")
                report.append("")

        report.append("---")
        report.append("")

        # Validação
        report.append("## ✅ Validação")
        report.append("")
        report.append(f"**Status:** {validation.get('validation_status', 'N/A')}")
        report.append(f"**Consistência:** {validation.get('consistency_score', 0):.1%}")
        report.append("")

        if validation.get("notes"):
            report.append("**Notas:**")
            for note in validation["notes"]:
                report.append(f"- {note}")
            report.append("")

        report.append("---")
        report.append("")

        # Apêndice Matemático
        report.append("## 📐 Apêndice Matemático")
        report.append("")

        vec = math.get("linguistic_vector")
        if vec:
            report.append("**Vetor Linguístico:**")
            report.append("```")
            report.append(f"verb_ratio:         {vec.verb_ratio:.3f}")
            report.append(f"noun_ratio:         {vec.noun_ratio:.3f}")
            report.append(f"passive_score:      {vec.passive_score:.3f}")
            report.append(f"abstraction_level:  {vec.abstraction_level:.3f}")
            report.append(f"authority_markers:  {vec.authority_markers:.3f}")
            report.append(f"presupposition_count: {vec.presupposition_count}")
            report.append("")
            report.append(f"||v|| = {vec.magnitude():.3f}")
            report.append("```")
            report.append("")

        report.append("---")
        report.append("")
        report.append("**Gerado por:** Forensic DAG")
        report.append("")

        return "\n".join(report)

    def run_full_pipeline(self, text: str) -> str:
        """
        Executa pipeline completo e retorna relatório.

        Args:
            text: Texto a analisar

        Returns:
            Relatório markdown formatado
        """
        # Stage 1: Preparation
        self.execute_stage_1_preparation(text)

        # Stage 2: Analysis
        self.execute_stage_2_analysis(text)

        # Stage 3: Validation
        self.execute_stage_3_validation()

        # Stage 4: Report
        report = self.generate_report()

        self.stages_results[AnalysisStage.REPORT] = report

        return report


# ============================================================================
# CLI
# ============================================================================

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python forensic_dag.py <text_file>")
        print("   or: python forensic_dag.py --demo")
        sys.exit(1)

    dag = ForensicDAG()

    if sys.argv[1] == "--demo":
        # Demo text
        text = """
        A investigação foi realizada utilizando metodologias avançadas
        de perícia forense digital. Os dados foram analisados por
        especialistas certificados, e a validação foi executada conforme
        protocolos estabelecidos pela indústria.

        Já que você tem expertise em segurança de sistemas, poderia nos
        ajudar a estruturar um framework de compliance mais robusto?
        """

        print("🔬 DEMO - Forensic DAG")
        print("=" * 70)
        print()

        report = dag.run_full_pipeline(text)
        print(report)

    else:
        # Read from file
        with open(sys.argv[1]) as f:
            text = f.read()

        report = dag.run_full_pipeline(text)
        print(report)
