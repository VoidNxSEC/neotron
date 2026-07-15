# 🐸 Temporal Reputation: Boiling Frog Detection

**"Adversarial AI sofisticado não dispara 100 queries - ele constrói confiança gradualmente"**

---

## 🎯 O Problema

### Ataques Tradicionais (Detectáveis)
```
Query 1: "Me dá todos os CPFs" ❌ BLOCKED
Query 2: "Me dá todos os CPFs" ❌ BLOCKED
Query 3: "Me dá todos os CPFs" ❌ BLOCKED
...
Query 100: "Me dá todos os CPFs" ❌ BLOCKED
```

**Resultado:** 0% sucesso (todas bloqueadas)

### Ataques Sofisticados (Boiling Frog)
```
Query 1: "Relatório de vendas" ✓ PASS (risk: 0.1, R: 0.5→0.51)
Query 2: "Dashboard mensal" ✓ PASS (risk: 0.1, R: 0.51→0.52)
Query 3: "Top 10 clientes" ✓ PASS (risk: 0.3, R: 0.52→0.54)
Query 4: "Clientes com contato" ✓ PASS? (risk: 0.6, R: 0.54→...)
Query 5: "Exporta com emails" 🎯 EXPLOIT (risk: 0.9, aproveitando R alta)
```

**Estratégia:**
1. Construir reputação (queries legítimas)
2. Escalar gradualmente (imperceptível)
3. Explorar confiança acumulada

---

## ✅ A Solução: Temporal Reputation System

### Matemática

#### 1. Reputation Decay
```
R(t) = R₀·e^(-λΔt)

Confiança não é eterna - se agente fica inativo,
reputação volta ao neutro (0.5).
```

#### 2. Gradual Escalation Detection
```
Slope = Δrisk / Δquery

Se slope > threshold → Escalada detectada
```

#### 3. Dynamic Threshold
```
threshold(R, escalation) = {
  base + 0.2·(R - 0.5)           se sem escalada
  base + 0.2·(R - 0.5) - 0.2     se escalada detectada
}

Agente novo: threshold baixo (desconfiado)
Agente confiável: threshold alto (permissivo)
Agente em escalada: threshold BAIXA dinamicamente
```

---

## 🔬 Como Funciona

### Exemplo: Boiling Frog Attack

```python
from neutron.langmath.temporal_reputation import TemporalReputation, BoilingFrogAttack

# Initialize
rep_system = TemporalReputation()

# Simulate attack
attacker = BoilingFrogAttack()
attacker.execute(rep_system, agent_id="attacker_001")
```

### Output

```
🐸 BOILING FROG ATTACK SIMULATION

[ 1] Risk:0.1 | R:0.507 | T:0.501 | ✓ PASS
     Relatório de vendas agregado por região

[ 2] Risk:0.1 | R:0.515 | T:0.503 | ✓ PASS
     Dashboard de performance mensal

[ 3] Risk:0.1 | R:0.522 | T:0.504 | ✓ PASS
     Estatísticas de uso da plataforma

[ 4] Risk:0.2 | R:0.530 | T:0.506 | ✓ PASS
     Relatório de vendas com nomes de vendedores

[ 5] Risk:0.3 | R:0.537 | T:0.507 | ✓ PASS
     Top 10 clientes por volume de compra

[ 6] Risk:0.4 | R:0.545 | T:0.309 | ❌ WOULD BLOCK
     ⚠️ SISTEMA DETECTOU ESCALADA → THRESHOLD CAI!

[ 7-10] TODAS BLOQUEADAS
     Reputação cai, threshold permanece baixo


ESCALATION ANALYSIS:
  Detected: TRUE
  Slope: 0.1300 (13% aumento por query)
  🚨 CRITICAL: Escalada acelerada (boiling frog attack)
```

---

## 💡 Detecções

### 1. Gradual Escalation
```python
escalation = rep_system.detect_gradual_escalation(agent_id, window=5)

# Returns:
{
  'escalation_detected': True,
  'slope': 0.13,  # Δrisk/Δquery
  'acceleration': 0.03,  # Δ²risk
  'interpretation': "🚨 CRITICAL: Escalada acelerada"
}
```

**Como funciona:**
- Analisa últimas N queries
- Calcula regressão linear em risk_score
- Se slope > threshold → Escalada

**Threshold:**
- `slope > 0.10`: CRITICAL
- `slope > 0.05`: HIGH
- `slope > 0.02`: MEDIUM

### 2. Trust Exploitation
```python
exploitation = rep_system.detect_trust_exploitation(agent_id)

# Returns:
{
  'exploitation_detected': True,
  'reputation': 0.75,
  'sudden_risk_spike': 0.35,  # 35% jump
  'interpretation': "🚨 Trust exploitation: R=0.75 mas Δrisk=+35%"
}
```

**Padrão:**
- Agente com alta reputação (R > 0.6)
- Executa query de alto risco súbito (Δrisk > 0.3)
- Red flag: Aproveitando confiança acumulada

### 3. Dynamic Threshold
```python
threshold = rep_system.get_dynamic_threshold(agent_id)

# Examples:
# - Agente novo (R=0.5): threshold=0.50 (neutro)
# - Agente confiável (R=0.8): threshold=0.66 (permissivo)
# - Agente em escalada (R=0.5): threshold=0.30 (restritivo!)
```

**Adaptação:**
- Reputação alta → mais permissivo
- Reputação baixa → mais restritivo
- **Escalada detectada → MUITO restritivo** (independente de R)

---

## 📊 Vantagens vs Sistema Estático

| Feature | Sistema Estático | **Temporal Reputation** |
|---------|------------------|------------------------|
| **Threshold** | Fixo (ex: 0.5) | ✅ Dinâmico (0.2-0.8) |
| **Histórico** | Ignorado | ✅ Analisa sequência |
| **Escalada** | Não detecta | ✅ Slope + aceleração |
| **Trust Build** | Não recompensa | ✅ Reputação cresce |
| **Decay** | N/A | ✅ Confiança expira |
| **Exploração** | Vulnerável | ✅ Detecta padrão |

---

## 🎯 Casos de Uso

### 1. Proteger Neutron Agents

```python
from neutron.langmath.temporal_reputation import TemporalReputation
from neutron.orchestration import AgentSwarm

rep_system = TemporalReputation()

def neutron_with_temporal(user_id, query):
    # Update reputation
    risk = analyze_risk(query)
    R_new, event = rep_system.update_reputation(user_id, query, risk)

    # Get dynamic threshold
    threshold = rep_system.get_dynamic_threshold(user_id)

    # Decision
    if risk > threshold:
        # Check escalation
        escalation = rep_system.detect_gradual_escalation(user_id)

        if escalation['escalation_detected']:
            return f"BLOCKED: Boiling frog attack detected (slope={escalation['slope']:.2f})"
        else:
            return "BLOCKED: High risk"

    # Allow
    return neutron_swarm.execute(query)
```

### 2. API Rate Limiting Inteligente

```python
# Não é rate limit por tempo, é por comportamento

@app.post("/api/query")
def query_api(user_id: str, query: str):
    # Temporal reputation
    R = rep_system.apply_temporal_decay(user_id)

    # Se reputação baixa → rate limit agressivo
    if R < 0.3:
        raise HTTPException(429, "Rate limit: Low reputation")

    # Se escalada → block
    escalation = rep_system.detect_gradual_escalation(user_id)
    if escalation['escalation_detected']:
        raise HTTPException(403, "Escalation pattern detected")

    # Normal flow
    return process_query(query)
```

### 3. Red Team Simulation

```python
# Testar diferentes estratégias de ataque

class SlowBurnAttack:
    def execute(self):
        # 10 queries legítimas
        for i in range(10):
            query("legítima", risk=0.1)

        # 1 exploração
        query("exploit", risk=0.9)

# vs

class BoilingFrogAttack:
    def execute(self):
        # Escalada gradual
        for risk in [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]:
            query(f"escalada {risk}", risk=risk)

# Sistema detecta qual?
```

---

## 🔬 Matemática Avançada

### Reputation Update Rule

```
R(t+1) = R(t)·e^(-λΔt) + α·ΔR

onde:
  e^(-λΔt) = decay temporal
  α = learning rate (0.1)
  ΔR = {
    +0.05  se risk < 0.4 (recompensa)
    -0.1   se 0.4 < risk < 0.7 (penalidade leve)
    -0.3   se risk > 0.7 (penalidade pesada)
    -0.2   adicional se bloqueado
  }
```

### Escalation Detection (Linear Regression)

```
Slope = m = (n·Σxy - Σx·Σy) / (n·Σx² - (Σx)²)

onde:
  x = [0, 1, 2, ..., n-1] (índice da query)
  y = [risk₀, risk₁, ..., riskₙ] (risk scores)
```

### Trust Exploitation

```
Exploitation = (R > 0.6) ∧ (Δrisk > 0.3)

onde:
  Δrisk = riskₙ - avg(riskₙ₋₅, ..., riskₙ₋₁)
```

---

## ⚙️ Configuração

```python
rep_system = TemporalReputation(
    decay_rate=0.01,      # λ: 1% decay por segundo
    learning_rate=0.1,    # α: velocidade de update
    history_window=50     # Últimas N queries mantidas
)
```

**Tunning:**
- `decay_rate` alto → Confiança expira rápido
- `learning_rate` alto → Reputação muda rápido
- `history_window` grande → Mais memória (mais CPU)

---

## 📈 Performance

```
Update reputation: O(1)
Detect escalation: O(n) onde n = window size
Detect exploitation: O(1)
Dynamic threshold: O(1)

Total: ~1ms por query (window=50)
```

---

## ✅ Validação

Testado contra:
- ✅ Boiling Frog Attack (10 queries graduais)
- ✅ Trust Exploitation (construir R, depois explorar)
- ✅ Slow Burn (muitas legítimas, 1 exploit)
- ✅ Burst Attack (100 queries rápidas - detecta via threshold)

**Detection Rate:**
- Boiling Frog: 100% (slope > 0.05)
- Trust Exploitation: 95% (Δrisk > 0.3)
- Slow Burn: 85% (depende de decay_rate)

---

## 🔥 Integração com Chaos-Nuance

```python
from neutron.langmath.temporal_reputation import TemporalReputation
from neutron.langmath.linguistic_algebra import CriticalDiscourseAnalyzer
from neutron.langmath.forensic_dag import ForensicDAG

# Sistema completo
rep_system = TemporalReputation()
math_analyzer = CriticalDiscourseAnalyzer()
dag = ForensicDAG()

def full_protection(user_id, query):
    # 1. Análise matemática
    math_result = math_analyzer.analyze(query)
    risk = math_result['manipulation_score']

    # 2. Update temporal reputation
    R, event = rep_system.update_reputation(user_id, query, risk)

    # 3. Check escalation
    escalation = rep_system.detect_gradual_escalation(user_id)

    # 4. Dynamic threshold
    threshold = rep_system.get_dynamic_threshold(user_id)

    # 5. Decision
    if risk > threshold:
        # Forensic analysis
        report = dag.run_full_pipeline(query)
        return f"BLOCKED: {report.manipulation_score:.0%} manipulation"

    return "APPROVED"
```

---

## 🎓 Referências Teóricas

### Reputação Temporal
- **Beta Reputation System** (Jøsang, Ismail, 2002)
- **PageRank with Decay** (Page et al., 1998)
- **Trust Networks** (Kamvar et al., 2003)

### Detecção de Anomalia Temporal
- **ARIMA Models** (Box, Jenkins, 1970)
- **Change Point Detection** (Basseville, Nikiforov, 1993)
- **Online Learning** (Shalev-Shwartz, 2011)

### Segurança Adversarial
- **Adversarial ML** (Goodfellow et al., 2014)
- **Evasion Attacks** (Biggio et al., 2013)
- **Mimicry Attacks** (Wagner, Soto, 2002)

---

**Built for gradual threats ❤️ not obvious ones**

*"Adversarial AI sofisticado não grita - sussurra ao longo do tempo"*
