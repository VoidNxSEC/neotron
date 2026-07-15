# 🚨 Problemas Atuais - Neutron/NEXUS

**Data**: 2026-01-31
**Status**: Levantamento Pós-Investigação

---

## 🔴 CRÍTICO (Bloqueadores de Produção)

### 1. Bug Semântico no Sistema de Consent

**Arquivo**: `contracts/src/LGPDConsent.sol:210`

**Problema**:
```solidity
function hasConsent(address dataSubject) internal view override returns (bool) {
    return hasConsent(dataSubject, msg.sender);  // ❌ ERRADO!
}
```

**Deveria ser**:
```solidity
function hasConsent(address dataSubject) internal view override returns (bool) {
    return hasConsent(dataSubject, address(this));  // ✅ CORRETO
}
```

**Impacto**:
- ❌ Semântica LGPD incorreta ("self-consent" vs "consent to processor")
- ❌ Contratos deployados no Sepolia podem estar bugados
- ❌ Risco legal se auditar compliance
- ⚠️ Testes passam mas com workaround (não reflete uso real)

**Esforço**: 5min código + 20min redeploy + 10min reteste = **35min**

**Decisão Necessária**: Fix correto agora OU documentar e fazer depois?

---

## 🟡 IMPORTANTE (Qualidade/Manutenibilidade)

### 2. Python Deprecation Warnings

**Arquivo**: `neutron/compliance/sentinel.py:215`

**Problema**:
```python
"timestamp": datetime.utcnow().isoformat(),  # ❌ Deprecated em Python 3.13
```

**Impacto**:
- 13 warnings nos testes
- Vai quebrar em Python 3.14+
- Não afeta funcionalidade AGORA

**Esforço**: 15min (find & replace)

---

### 3. Package Structure Incompleta

**Problema**: 8 arquivos `__init__.py` faltando

**Arquivos**:
```
neutron/__init__.py                  ❌
neutron/api/__init__.py              ❌
neutron/cli/__init__.py              ❌
neutron/compliance/__init__.py       ❌
neutron/orchestration/__init__.py    ❌
neutron/scripts/__init__.py          ❌
neutron/testing/__init__.py          ❌
neutron/tracking/__init__.py         ❌
```

**Impacto**:
- ⚠️ Imports podem falhar em alguns contextos
- ❌ Não publicável no PyPI
- ✅ Funcionou nos testes (dentro do Nix environment)

**Esforço**: 2 horas (criar + povoar com exports corretos)

---

## 🟢 BAIXA PRIORIDADE (Polish)

### 4. Documentação Desatualizada

**Problemas**:
- README badges: "350+ tests" → deveria ser "585+ tests"
- ROADMAP.md: referências temporais desatualizadas
- PROJECT_STATUS.md: não existe
- PHASE2_COMPLETE.md, PHASE3_COMPLETE.md: ausentes

**Impacto**: Confusão para novos desenvolvedores

**Esforço**: 1 dia (update completo)

---

### 5. Módulos Vazios

**Diretórios**:
- `neutron/cli/` - vazio
- `neutron/testing/` - vazio
- `neutron/tracking/` - vazio

**Impacto**:
- CLI não existe (mas `justfile` cobre 80%)
- Test utilities não centralizadas
- Cost tracking mencionado mas não implementado

**Esforço**: 1-2 semanas (implementar tudo)

---

## 📊 Resumo Executivo

| Problema | Prioridade | Esforço | Impacto Produção |
|----------|-----------|---------|------------------|
| **Bug Consent Semântico** | 🔴 CRÍTICO | 35min | BLOQUEADOR |
| **Deprecation Warnings** | 🟡 IMPORTANTE | 15min | Futuro |
| **Package Structure** | 🟡 IMPORTANTE | 2h | PyPI only |
| **Docs Desatualizadas** | 🟢 BAIXA | 1 dia | Onboarding |
| **Módulos Vazios** | 🟢 BAIXA | 1-2 sem | Features extras |

---

## 🎯 Decisão Necessária

**Qual atacar AGORA?**

**A. Fix Bug Consent (35min)** - Resolve problema arquitetural real
**B. Python Warnings (15min)** - Quick win, menos risco
**C. Package Structure (2h)** - Necessário para distribuição
**D. Fazer A+B em sequência (50min)** - Resolve 2 críticos
**E. Deixar tudo documentado e seguir** - Focus em features novas

---

## 🔍 Contexto Adicional

### Status Atual dos Testes

**Solidity**: 69/69 passando ✅ (mas com workaround)
**Python**: Não rodamos ainda os completos

### Próximo Milestone

**v1.0.0 Production**: Precisa resolver problema #1 (bug consent)

**v1.0.0 Beta**: Pode viver com workaround + documentação

---

**Aguardando decisão**: Qual problema atacamos agora?
