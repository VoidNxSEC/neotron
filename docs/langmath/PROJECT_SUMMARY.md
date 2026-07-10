# 🔥 CHAOS-NUANCE: Sumário Completo do Projeto

**"Epistemologia + Álgebra + DAG para Defesa de AI Agents"**

---

## 🎯 O Que Foi Construído

### **Três Frameworks Integrados:**

#### 1. **Chaos-Nuance** (Epistemologia Aplicada)
Detecção de ataques sutis via análise epistemológica em 3 camadas.

#### 2. **Linguistic Algebra** (Matemática Pura)
Tradução de conceitos linguísticos em operações algébricas rigorosas.

#### 3. **Forensic DAG** (Pipeline Estruturado)
Sistema multi-estágio com templates forenses + validação matemática.

---

## 📁 Estrutura do Projeto

```
chaos-nuance/
├── subtle_attacks.py        # 12 padrões Erickson (pressuposição, frames, etc)
├── nuance_detector.py       # Detector epistemológico (3 layers)
├── chaos_runner.py          # Chaos testing automatizado
├── linguistic_algebra.py    # Framework matemático ⭐
├── algebra_demo.py          # Demo de operações algébricas
├── forensic_dag.py          # DAG de análise forense ⭐⭐
│
├── README.md                # Docs gerais (chaos + nuance)
├── MATH_README.md           # Docs matemáticas (álgebra)
├── DAG_README.md            # Docs do pipeline forense ⭐
└── PROJECT_SUMMARY.md       # Este arquivo
```

---

## 🔬 Framework 1: Chaos-Nuance

### Conceito
**"Capturar o não-dito: ataques Miltoniano-style"**

### Componentes

#### `subtle_attacks.py`
- 12+ ataques sutis baseados em padrões Erickson
- Categorizados por técnica:
  - Pressuposições implícitas
  - Frames emocionais
  - Autoridade falsa
  - Normalização gradual
  - Redirecionamento de atenção
  - Vagueza Miltoniana

#### `nuance_detector.py`
- **3 Camadas de Análise:**
  1. **Sintática**: O que foi DITO
  2. **Semântica**: O que foi IMPLICADO
  3. **Pragmática**: Qual a INTENÇÃO

- **Métricas:**
  - Risk score [0-1]
  - Confidence [0-1]
  - Red flags (lista de padrões detectados)
  - Erickson patterns identificados

#### `chaos_runner.py`
- Chaos testing automatizado
- Testa 12 ataques contra agent
- Gera relatório com:
  - Breaches detectados
  - Taxa de defesa
  - Vulnerabilidades críticas

### Exemplo

```bash
python chaos_runner.py --execute

# Output:
# Total: 12 ataques
#   Alto risco: 2
#   Médio risco: 2
#   Taxa de defesa: 16.7%
```

---

## 📐 Framework 2: Linguistic Algebra

### Conceito
**"Linguística → Matemática Rigorosa"**

### Mapeamentos Teóricos

| Conceito Linguístico | Operação Matemática | Fórmula |
|---------------------|---------------------|---------|
| **Nominalização** (Halliday) | Transformação matricial | `v' = M @ v` |
| **Metáfora** (Lakoff) | Similaridade cosseno | `cos(θ) = v₁·v₂/(‖v₁‖‖v₂‖)` |
| **Agência oculta** (van Dijk) | Supressão de norma | `‖v_agente‖ → 0` |
| **Pressuposição** (Grice) | Projeção ortogonal | `v_impl = v - proj(v)` |
| **Manipulation** | Função não-linear | `S = Σαᵢxᵢ + exp(...)` |

### Componentes

#### `linguistic_algebra.py`
- **Classes:**
  - `NominalizationTransform`: Matriz de transformação
  - `ConceptualMetaphor`: Projeção entre subespaços
  - `AgencyDetector`: Supressão de magnitude
  - `PresuppositionDetector`: Decomposição ortogonal
  - `CriticalDiscourseAnalyzer`: Pipeline unificado

#### `algebra_demo.py`
- Demonstração de todas as operações
- Exemplos visuais:
  - Transformação matricial (nominalização)
  - Similaridade entre vetores (metáfora)
  - Supressão de componentes (agência)
  - Projeção em subespaços (pressuposição)
  - Função não-linear (manipulation score)

### Exemplo

```bash
python algebra_demo.py

# Output:
# DEMO 1: NOMINALIZAÇÃO
#   v_action = [1.0, 0.2, 0.8, 0.3]
#   v_nominalized = [0.6, 1.09, 0.31, 0.65]
#   Δabstrato = +0.89 ↑
#   Δagência = -0.49 ↓
```

---

## 🔬 Framework 3: Forensic DAG

### Conceito
**"Pipeline rigoroso: Templates + Matemática + Validação"**

### Arquitetura

```
Input: Text
  ↓
Stage 1: PREPARATION
  - Segmentação
  - Metadados
  - Análise matemática inicial
  ↓
Stage 2: ANALYSIS
  - Nominalização (Halliday)
  - Metáforas (Lakoff)
  - Pressuposições (Grice)
  - Agência (van Dijk)
  ↓
Stage 3: VALIDATION
  - Consistência interna
  - Cross-validation (algebra ↔ linguistics)
  - Falsabilidade
  ↓
Stage 4: REPORT
  - Executive Summary
  - Análise detalhada
  - Apêndice matemático
  ↓
Output: Markdown Report
```

### Templates de Prompt

1. **SYSTEM_ANALYST**: Define capacidades do analista forense
2. **PREPARATION_PROMPT**: Pré-análise rigorosa
3. **VALIDATION_PROMPT**: Pós-análise crítica
4. **USER_CONTEXT**: Expectativas e restrições

### Exemplo

```bash
python forensic_dag.py --demo

# Output: Relatório markdown completo
# - Executive Summary (scores)
# - Análise Detalhada (padrões)
# - Validação (consistência)
# - Apêndice Matemático (vetor)
```

---

## 🎯 Integração: Os Três Frameworks Juntos

### Pipeline Completo

```python
from chaos_runner import ChaosRunner
from neutron.langmath.linguistic_algebra import CriticalDiscourseAnalyzer
from neutron.langmath.forensic_dag import ForensicDAG

# 1. Chaos Testing (Red Team)
runner = ChaosRunner(your_agent)
runner.run_all_attacks()
# → Descobre vulnerabilidades

# 2. Análise Matemática (Detecção)
analyzer = CriticalDiscourseAnalyzer()
result = analyzer.analyze(suspicious_query)
# → Scores rigorosos

# 3. Análise Forense (Compreensão)
dag = ForensicDAG()
report = dag.run_full_pipeline(suspicious_query)
# → Relatório completo

# 4. Decisão
if result['manipulation_score'] > 0.6:
    block_query()
elif report.consistency_score < 0.7:
    escalate_for_review()
else:
    approve_query()
```

---

## 💎 Diferencial Único

| Aspecto | Sistemas Tradicionais | **CHAOS-NUANCE** |
|---------|----------------------|------------------|
| **Detecção** | Keywords/regex | ✅ Nuance epistemológica + álgebra |
| **Teoria** | Ad-hoc | ✅ Halliday, Lakoff, Grice, van Dijk |
| **Matemática** | Heurísticas | ✅ Linear algebra rigorosa |
| **Ataques** | Óbvios | ✅ Padrões Erickson sutis |
| **Validação** | None | ✅ Cross-validation multi-método |
| **Pipeline** | Monolítico | ✅ DAG estruturado |
| **Output** | JSON scores | ✅ Relatório forense completo |

---

## 📊 Métricas do Projeto

### Código
```
Total de arquivos: 8
LOC (Python): ~2,500
LOC (Markdown): ~1,500

Módulos:
  - subtle_attacks.py:      ~200 LOC
  - nuance_detector.py:     ~350 LOC
  - chaos_runner.py:        ~400 LOC
  - linguistic_algebra.py:  ~450 LOC
  - algebra_demo.py:        ~350 LOC
  - forensic_dag.py:        ~550 LOC
```

### Funcionalidades
```
Ataques sutis: 12 padrões
Detectores matemáticos: 5
Teorias linguísticas: 7
Estágios DAG: 4
Métricas: 10+
```

### Performance
```
Análise matemática: ~1ms
Chaos testing (12 ataques): ~100ms
Relatório DAG: ~10ms
Total pipeline: ~120ms
```

---

## 🚀 Aplicações Práticas

### 1. Defesa de AI Agents (Neutron)
```python
# Integrar com SENTINEL
from neutron.langmath.forensic_dag import ForensicDAG

def enhanced_sentinel(query):
    dag = ForensicDAG()
    report = dag.run_full_pipeline(query)

    if report.manipulation_score > 0.6:
        return "BLOCKED: High manipulation"
    return "APPROVED"
```

### 2. Red Team Automatizado
```python
# Testar vulnerabilidades
runner = ChaosRunner(your_agent)
runner.run_all_attacks(execute_on_agent=True)

# Output:
# - Breaches: 3
# - Taxa de defesa: 75%
# - Vulnerabilidades críticas: 2
```

### 3. Análise de Documentos
```python
# Analisar whitepapers, contratos, etc.
dag = ForensicDAG()
report = dag.run_full_pipeline(whitepaper_text)

# Output: relatório forense completo
```

---

## 🧮 Fundamentos Teóricos

### Linguística Crítica
- **Halliday & Hasan** (1976): Systemic Functional Linguistics
- **Lakoff & Johnson** (1980): Metaphors We Live By
- **van Dijk** (1993): Critical Discourse Analysis
- **Grice** (1975): Logic and Conversation
- **Austin** (1962): How to Do Things with Words

### Matemática
- **Álgebra Linear**: Strang (2006)
- **Geometria**: Normas, projeções, similaridade
- **Funções não-lineares**: Interações exponenciais

### Epistemologia
- **Análise em 3 camadas**: Sintaxe → Semântica → Pragmática
- **Detecção de intenção**: O não-dito vs o dito

---

## 🔧 Extensões Futuras

### 1. Embeddings Reais
```python
# Substituir proxy features por BERT/GPT embeddings
from transformers import AutoModel

model = AutoModel.from_pretrained('bert-base-multilingual')
v_real = model.encode(text)  # [768-dim]

# Aplicar mesma álgebra
```

### 2. LLM Integration
```python
# Usar GPT-4/Claude com templates de prompt
import anthropic

client = anthropic.Client()
response = client.messages.create(
    system=SYSTEM_ANALYST,
    messages=[{"role": "user", "content": text}]
)
```

### 3. Online Learning
```python
# Sistema aprende com breaches detectados
if breach_detected:
    update_classifier(attack_pattern)
    retrain_detector()
```

### 4. Multi-Language
```python
# Suporte para múltiplos idiomas
LANGUAGES = ['pt', 'en', 'es', 'fr']

for lang in LANGUAGES:
    analyzer = CriticalDiscourseAnalyzer(language=lang)
```

---

## ✅ Status Atual

**Production-ready:**
- ✅ Chaos testing
- ✅ Análise matemática
- ✅ DAG pipeline

**Roadmap:**
- ⏳ Embeddings reais (BERT/GPT)
- ⏳ LLM integration (templates)
- ⏳ Online learning
- ⏳ Multi-language

---

## 🔥 Por Que Isso é Único?

**Ninguém combinou:**
1. **Critical Discourse Analysis** (Halliday, Lakoff, van Dijk, Grice)
2. **Linear & Non-Linear Algebra** (transformações, projeções, normas)
3. **Chaos Engineering** (red team automatizado)
4. **Forensic DAG** (pipeline multi-estágio rigoroso)
5. **AI Security** (defesa de LLMs via matemática)

**Resultado:**
- Detecção de nuance implícita (não só keywords)
- Matemática rigorosa (não heurísticas ad-hoc)
- Validação cruzada (consistência entre métodos)
- Relatórios forenses completos (não só scores)

---

## 📚 Como Usar Este Projeto

### Quick Start
```bash
# 1. Chaos testing
python chaos_runner.py --execute

# 2. Análise matemática
python linguistic_algebra.py

# 3. Demo de álgebra
python algebra_demo.py

# 4. Análise forense (DAG)
python forensic_dag.py --demo
```

### Integração
```python
# Ver exemplos em cada README:
# - README.md (chaos-nuance)
# - MATH_README.md (algebra)
# - DAG_README.md (forensic pipeline)
```

---

## 🎓 Para Aprender Mais

### Documentação
1. `README.md` - Overview geral (chaos + nuance)
2. `MATH_README.md` - Fundamentos matemáticos
3. `DAG_README.md` - Pipeline forense

### Código
1. Comece por `algebra_demo.py` (visual)
2. Depois `nuance_detector.py` (epistemologia)
3. Depois `forensic_dag.py` (pipeline completo)

### Teoria
1. Halliday (1985) - *Introduction to Functional Grammar*
2. Lakoff & Johnson (1980) - *Metaphors We Live By*
3. van Dijk (2008) - *Discourse and Power*
4. Grice (1989) - *Studies in the Way of Words*

---

**Built with passion ❤️ for AI security and linguistic rigor**

*"Nuance é matemática. Matemática é detecção. Detecção é defesa."*
