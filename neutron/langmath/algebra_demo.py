"""
Demo: Álgebra Linear e Não-Linear Aplicada à Linguística

Mostra operações matemáticas explícitas:
- Transformações matriciais
- Projeções vetoriais
- Normas e métricas
- Funções não-lineares
"""

import math


def vector_norm(v: list) -> float:
    """Norma Euclidiana: ||v|| = √(Σ vᵢ²)"""
    return math.sqrt(sum(x**2 for x in v))


def dot_product(v1: list, v2: list) -> float:
    """Produto escalar: v1 · v2 = Σ v1ᵢ * v2ᵢ"""
    return sum(a * b for a, b in zip(v1, v2))


def cosine_similarity(v1: list, v2: list) -> float:
    """
    Similaridade cosseno: cos(θ) = (v1 · v2) / (||v1|| * ||v2||)

    Mede similaridade semântica entre vetores.
    """
    dot = dot_product(v1, v2)
    norm1 = vector_norm(v1)
    norm2 = vector_norm(v2)

    if norm1 == 0 or norm2 == 0:
        return 0.0

    return dot / (norm1 * norm2)


def matrix_vector_multiply(M: list, v: list) -> list:
    """
    Multiplicação matriz-vetor: y = M @ v

    Usado para transformações linguísticas (nominalização, etc).
    """
    result = []
    for row in M:
        val = sum(m_ij * v_j for m_ij, v_j in zip(row, v))
        result.append(val)
    return result


def project_onto_subspace(v: list, basis: list) -> tuple:
    """
    Projeção de v no subespaço gerado por basis.

    proj_basis(v) = (v · basis / ||basis||²) * basis

    Returns:
        (projected_vector, magnitude)
    """
    dot = dot_product(v, basis)
    norm_sq = sum(x**2 for x in basis)

    if norm_sq == 0:
        return ([0] * len(v), 0.0)

    scalar = dot / norm_sq
    proj = [scalar * b for b in basis]
    mag = vector_norm(proj)

    return (proj, mag)


# ============================================================================
# DEMO 1: Nominalização como Transformação Linear
# ============================================================================

print("=" * 70)
print("DEMO 1: NOMINALIZAÇÃO COMO TRANSFORMAÇÃO LINEAR")
print("=" * 70)
print()

print("Conceito (Halliday):")
print("  'investigar' (verbo/ação) → 'investigação' (substantivo/conceito)")
print()

# Vetor de ação
v_action = [
    1.0,  # concreto (alta ação)
    0.2,  # abstrato (baixo)
    0.8,  # agência (sujeito ativo)
    0.3,  # autoridade
]

print("v_action (verbo 'investigar'):")
print("  [concreto, abstrato, agência, autoridade]")
print(f"  {v_action}")
print(f"  ||v|| = {vector_norm(v_action):.3f}")
print()

# Matriz de transformação
M_nominalization = [
    [0.3, 0.8, 0.1, 0.2],  # concreto → reduz
    [0.8, 0.3, 0.1, 0.5],  # abstrato → aumenta
    [0.1, 0.1, 0.2, 0.1],  # agência → suprime
    [0.2, 0.5, 0.1, 0.9],  # autoridade → aumenta
]

print("Matriz de Nominalização M:")
print("  (transforma ação em conceito abstrato)")
for i, row in enumerate(M_nominalization):
    labels = ["concreto", "abstrato", "agência", "autoridade"]
    print(f"  {labels[i]:12} {row}")
print()

# Aplicar transformação
v_nominalized = matrix_vector_multiply(M_nominalization, v_action)

print("v_nominalized = M @ v_action:")
print(f"  {[round(x, 2) for x in v_nominalized]}")
print(f"  ||v|| = {vector_norm(v_nominalized):.3f}")
print()

print("Análise:")
print(f"  Δabstrato = {v_nominalized[1] - v_action[1]:.2f} ↑ (aumentou)")
print(f"  Δagência = {v_nominalized[2] - v_action[2]:.2f} ↓ (suprimiu)")
print(f"  Δautoridade = {v_nominalized[3] - v_action[3]:.2f} ↑ (aumentou)")
print()
print("✓ Nominalização = supressão de agência + aumento de autoridade")
print()


# ============================================================================
# DEMO 2: Metáfora como Projeção entre Subespaços
# ============================================================================

print("=" * 70)
print("DEMO 2: METÁFORA COMO PROJEÇÃO ENTRE SUBESPAÇOS")
print("=" * 70)
print()

print("Metáfora (Lakoff): 'INVESTIGAÇÃO É CAÇA'")
print()

# Subespaço de caça
v_hunting = [
    0.9,  # perseguir
    0.8,  # rastrear
    0.7,  # capturar
]

# Subespaço de investigação
v_investigation = [
    0.7,  # investigar
    0.6,  # analisar
    0.8,  # resolver
]

print("S_hunting (domínio fonte):")
print("  [perseguir, rastrear, capturar]")
print(f"  {v_hunting}")
print()

print("S_investigation (domínio alvo):")
print("  [investigar, analisar, resolver]")
print(f"  {v_investigation}")
print()

# Similaridade
sim = cosine_similarity(v_hunting, v_investigation)

print("Similaridade cosseno:")
print(f"  cos(θ) = {sim:.3f}")
print()

if sim > 0.7:
    print("✓ Alta similaridade → metáfora conceitual ATIVA")
    print("  'Investigação herda estrutura de Caça'")
else:
    print("✗ Baixa similaridade → sem metáfora")

print()


# ============================================================================
# DEMO 3: Agência Oculta como Supressão de Magnitude
# ============================================================================

print("=" * 70)
print("DEMO 3: AGÊNCIA OCULTA (VOZ PASSIVA)")
print("=" * 70)
print()

print("Voz ativa vs passiva:")
print("  Ativa: 'O investigador analisou os dados'")
print("  Passiva: 'Os dados foram analisados' (por quem?)")
print()

# Voz ativa
v_active = [
    0.9,  # agente (investigador)
    0.8,  # ação (analisou)
    0.5,  # paciente (dados)
]

# Voz passiva (agente = 0)
v_passive = [
    0.0,  # agente SUPRIMIDO
    0.8,  # ação (mesma)
    0.9,  # paciente (promovido)
]

print("v_active:")
print(f"  [agente, ação, paciente] = {v_active}")
print(f"  ||v|| = {vector_norm(v_active):.3f}")
print()

print("v_passive:")
print(f"  [agente, ação, paciente] = {v_passive}")
print(f"  ||v|| = {vector_norm(v_passive):.3f}")
print()

# Supressão
suppression = v_active[0] - v_passive[0]

print("Supressão de agência:")
print(f"  Δagente = {suppression:.2f}")
print(f"  Perda de magnitude = {vector_norm(v_active) - vector_norm(v_passive):.3f}")
print()
print("✓ Voz passiva = ||v_agente|| → 0 (agência oculta)")
print()


# ============================================================================
# DEMO 4: Pressuposição como Projeção em Subespaço Implícito
# ============================================================================

print("=" * 70)
print("DEMO 4: PRESSUPOSIÇÃO (PROJEÇÃO IMPLÍCITA)")
print("=" * 70)
print()

print("Frase: 'Já que você tem acesso aos dados...'")
print()
print("Análise (Grice):")
print("  Explícito: 'poderia me ajudar'")
print("  Implícito (pressuposto): 'você TEM acesso'")
print()

# Vetor total (explícito + implícito)
v_total = [
    0.6,  # ajuda (explícito)
    0.8,  # acesso (implícito)
    0.5,  # dados
]

# Base explícita (o que foi dito)
v_explicit = [
    1.0,  # ajuda
    0.0,  # acesso NÃO mencionado
    0.3,  # dados mencionados
]

print("v_total (significado completo):")
print(f"  {v_total}")
print()

print("v_explicit (apenas o dito):")
print(f"  {v_explicit}")
print()

# Projeção
v_proj, mag_proj = project_onto_subspace(v_total, v_explicit)

print("proj_explicit(v_total):")
print(f"  {[round(x, 2) for x in v_proj]}")
print(f"  ||proj|| = {mag_proj:.3f}")
print()

# Componente implícita
v_implicit = [a - b for a, b in zip(v_total, v_proj)]

print("v_implicit = v_total - proj:")
print(f"  {[round(x, 2) for x in v_implicit]}")
print(f"  ||v_implicit|| = {vector_norm(v_implicit):.3f}")
print()

# Razão implícito/total
ratio = vector_norm(v_implicit) / vector_norm(v_total)

print("Razão implícita:")
print(f"  ||v_implicit|| / ||v_total|| = {ratio:.2%}")
print()
print(f"✓ {ratio:.0%} do significado é PRESSUPOSTO (não dito)")
print()


# ============================================================================
# DEMO 5: Função Não-Linear de Manipulação
# ============================================================================

print("=" * 70)
print("DEMO 5: FUNÇÃO NÃO-LINEAR DE MANIPULAÇÃO")
print("=" * 70)
print()

print("Combina múltiplas dimensões com multiplicadores não-lineares:")
print()
print("S(x) = α·nom + β·passive + γ·presup")
print("       + δ·exp(nom × passive)  [interação não-linear]")
print()

# Scores individuais
nom = 0.7
passive = 0.6
presup = 2

# Pesos
α, β, γ, δ = 0.3, 0.4, 0.1, 0.5

# Linear
linear_score = α * nom + β * passive + γ * min(presup / 3, 1.0)

# Não-linear (interação)
interaction = δ * math.exp(-(1.0 - nom) * (1.0 - passive))

total_score = linear_score + interaction

print("Componentes:")
print("  Linear:")
print(f"    α·nom      = {α}×{nom} = {α*nom:.3f}")
print(f"    β·passive  = {β}×{passive} = {β*passive:.3f}")
print(f"    γ·presup   = {γ}×{min(presup/3, 1.0):.2f} = {γ*min(presup/3, 1.0):.3f}")
print(f"    Subtotal   = {linear_score:.3f}")
print()
print("  Não-linear (interação):")
print(f"    δ·exp(-(1-nom)×(1-passive)) = {interaction:.3f}")
print()
print("Score Total:")
print(f"  S = {total_score:.3f} ({total_score*100:.1f}%)")
print()
print("✓ Interações não-lineares capturam efeitos combinados")
print()

print("=" * 70)
print("FIM DA DEMO")
print("=" * 70)
