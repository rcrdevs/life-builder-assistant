# -*- coding: utf-8 -*-
"""
Life Builder Assistant -- motor de regras.
Sem chamadas de IA aqui: tudo eh heuristica transparente, facil de explicar ao usuario.
"""
import itertools
from datetime import date, timedelta

from data import (
    MISSION_TEMPLATES, ROTINA_MISSIONS, PERIOD_ORDER, generic_mission_templates,
    WORKOUT_PLANS, DIET_MEALS, DIET_MEAL_PERIOD, DIET_MEAL_LABEL,
    format_meal_detail, format_workout_detail, GOALS_NEEDING_DETAIL, QUIZ_BANK,
)

PLAN_DAYS = 14
NIVEL_ORDER = ["iniciante", "intermediario", "avancado"]

# quanto 1 ponto "cheio" (100% de conclusao) vale em pontos percentuais de progresso
# do objetivo. Ajustavel: numero menor = objetivos demoram mais ciclos para chegar a 100%.
PROGRESS_POINT_SCALE = 1.2

DEFAULT_PESO = 3  # peso padrao (1-5) de uma area quando o usuario nao define outro

# peso (1-5) atribuido automaticamente a partir da prioridade escolhida no
# Passo I (objetivo principal/secundaria/plano de fundo) -- ver step_areas()
# em app.py. Isso substitui o slider de peso manual do Passo III.
AREA_TIER_WEIGHTS = {"principal": 5, "secundario": DEFAULT_PESO, "fundo": 1}
AREA_TIER_LABELS = {"principal": "Principal", "secundario": "Secundária", "fundo": "Plano de fundo"}

# "jornada de trabalho" diaria de autodesenvolvimento: sempre soma 8h entre
# missoes primarias (tempo livre real do usuario) e secundarias (leves, podem
# acontecer em paralelo com a rotina -- trajeto, tarefas domesticas etc.)
TOTAL_DAY_MINUTES = 480
AVG_PRIMARY_MIN = 30     # duracao media assumida de uma missao primaria (min)
AVG_SECONDARY_MIN = 15   # duracao media assumida de uma missao secundaria (min)



def compute_mission_points(base_points, completion_pct):
    """
    Formula pedagogica: abandonar uma missao (0%) custa caro (representa o tempo
    perdido / a quebra do habito), fazer pouco (10%) custa um pouco menos, 20% eh o
    ponto de equilibrio (nem ganha nem perde -- foi feito o minimo para nao regredir),
    e a partir dali o ganho cresce linearmente ate o total em 100%.
    """
    pct = max(0, min(100, completion_pct))
    if pct <= 20:
        return round(-0.5 * base_points + (pct / 20) * 0.5 * base_points, 2)
    return round(((pct - 20) / 80) * base_points, 2)


def bump_nivel(nivel):
    """Sobe um degrau de nivel de experiencia (usado apos um checkpoint muito bom)."""
    try:
        idx = NIVEL_ORDER.index(nivel)
    except ValueError:
        return nivel
    return NIVEL_ORDER[min(idx + 1, len(NIVEL_ORDER) - 1)]


def _format_description(desc, area, goal, goal_details):
    if "{detalhe}" not in desc:
        return desc
    info = GOALS_NEEDING_DETAIL.get((area, goal), {})
    detalhe = (goal_details or {}).get(f"{area}:{goal}") or info.get("fallback", "escolhido")
    return desc.replace("{detalhe}", detalhe)


def _templates_for(area, goal, nivel, custom_label=None):
    templates = MISSION_TEMPLATES.get((area, goal))
    if not templates:
        label = custom_label or goal
        templates = generic_mission_templates(label)
    elegiveis = [t for t in templates if t["nivel"] in ("todos", nivel)]
    return elegiveis or templates


def _maybe_workout_detail(area, goal, description):
    if area != "saude" or goal not in WORKOUT_PLANS:
        return None
    desc_lower = description.lower()
    is_workout = desc_lower.startswith(("treino", "circuito", "corrida de", "long run", "fortalecimento"))
    if not is_workout:
        return None
    variants = WORKOUT_PLANS[goal]
    variant = variants[hash(description) % len(variants)]
    return format_workout_detail(variant)


def generate_plan(area_goal_pairs, niveis, pesos, tempo_livre_min, cycle,
                   custom_labels=None, diet_type=None, goal_details=None,
                   dias=PLAN_DAYS, start_date=None):
    """
    area_goal_pairs: lista de tuplas (area, goal_key) -- os objetivos escolhidos
        (a "dieta", se ativada, NAO entra aqui; e tratada à parte via diet_type).
    pesos: dict area -> peso 1-5 (importancia relativa, usado para distribuir as
        missoes primarias/secundarias entre as areas escolhidas).
    tempo_livre_min: minutos/dia de tempo livre real do usuario -> vira o total de
        missoes PRIMARIAS do dia. O restante ate 8h (480 min) vira missoes
        SECUNDARIAS (leves, podem ocorrer em paralelo com a rotina).
    diet_type: chave de DIET_MEALS ('padrao'/'vegetariano'/'vegano'/'low_carb') ou
        None. Se definido, adiciona 4 missoes fixas de dieta por dia (fora do
        orcamento de 8h, pois comer nao eh "tempo alocado" da mesma forma).
    Retorna lista de dicts prontos para inserir na tabela missions:
        {area, goal, description, base_points, date, period, cycle, tier,
         duration_min, detail}
    """
    if start_date is None:
        start_date = date.today()
    custom_labels = custom_labels or {}
    pesos = pesos or {}

    primary_minutes = max(0, min(tempo_livre_min, TOTAL_DAY_MINUTES))
    secondary_minutes = max(0, TOTAL_DAY_MINUTES - primary_minutes)

    areas_presentes = sorted({a for a, g in area_goal_pairs})
    weight_total = sum(pesos.get(a, DEFAULT_PESO) for a in areas_presentes) or 1

    # quantos objetivos (goals) cada area tem (normalmente 1; raramente 2, ex. saude
    # com objetivo principal + Paideia nao se aplica pois Paideia É o objetivo --
    # mas a estrutura suporta multiplos goals por area se isso mudar no futuro)
    goals_por_area = {}
    for a, g in area_goal_pairs:
        goals_por_area.setdefault(a, []).append(g)

    pair_plans = []
    for area, goal in area_goal_pairs:
        area_frac = pesos.get(area, DEFAULT_PESO) / weight_total
        goal_share = 1 / len(goals_por_area[area])
        pair_primary_min = primary_minutes * area_frac * goal_share
        pair_secondary_min = secondary_minutes * area_frac * goal_share

        nivel = niveis.get(area, "iniciante")
        label = custom_labels.get(f"{area}:{goal}")
        templates = _templates_for(area, goal, nivel, custom_label=label)
        primary_pool = [t for t in templates if t.get("points", 1) >= 2] or templates
        secondary_pool = [t for t in templates if t.get("points", 1) == 1] or templates

        pair_plans.append({
            "area": area, "goal": goal,
            "primary_min": pair_primary_min, "secondary_min": pair_secondary_min,
            "primary_cycle": itertools.cycle(primary_pool),
            "secondary_cycle": itertools.cycle(secondary_pool),
        })

    rotina_cycle = itertools.cycle(ROTINA_MISSIONS)

    plan = []
    for day_offset in range(dias):
        current_date = start_date + timedelta(days=day_offset)
        day_missions = []

        # rotina universal (fora do orcamento de 8h)
        n_rotina = 2 if primary_minutes >= 60 else 1
        for _ in range(n_rotina):
            rot = next(rotina_cycle)
            day_missions.append({
                "area": "rotina", "goal": "rotina", "tier": "rotina",
                "description": rot["desc"], "base_points": rot["points"],
                "period": rot["period"], "duration_min": 10, "detail": None, "action": None,
            })

        # dieta (fora do orcamento de 8h), se ativada
        if diet_type:
            meals = DIET_MEALS.get(diet_type, DIET_MEALS["padrao"])
            for meal_type in ("cafe", "almoco", "lanche", "jantar"):
                options = meals.get(meal_type)
                if not options:
                    continue
                meal = options[day_offset % len(options)]
                day_missions.append({
                    "area": "saude", "goal": "dieta", "tier": "dieta",
                    "description": f"{DIET_MEAL_LABEL[meal_type]}: {meal['nome']}",
                    "base_points": 2, "period": DIET_MEAL_PERIOD[meal_type],
                    "duration_min": 20, "detail": format_meal_detail(meal), "action": None,
                })

        # missoes primarias e secundarias (somam exatamente 8h/dia, distribuidas
        # pelo peso de cada area)
        for pp in pair_plans:
            n_primary = max(1, round(pp["primary_min"] / AVG_PRIMARY_MIN)) if pp["primary_min"] > 0 else 0
            duration_primary = pp["primary_min"] / n_primary if n_primary else 0
            for _ in range(n_primary):
                t = next(pp["primary_cycle"])
                detail = _maybe_workout_detail(pp["area"], pp["goal"], t["desc"])
                action = t.get("action")
                day_missions.append({
                    "area": pp["area"], "goal": pp["goal"], "tier": "primaria",
                    "description": _format_description(t["desc"], pp["area"], pp["goal"], goal_details),
                    "base_points": t["points"],
                    "period": t["period"], "duration_min": round(duration_primary, 1),
                    "detail": detail, "action": action,
                })

            n_secondary = max(1, round(pp["secondary_min"] / AVG_SECONDARY_MIN)) if pp["secondary_min"] > 0 else 0
            duration_secondary = pp["secondary_min"] / n_secondary if n_secondary else 0
            for _ in range(n_secondary):
                t = next(pp["secondary_cycle"])
                detail = _maybe_workout_detail(pp["area"], pp["goal"], t["desc"])
                action = t.get("action")
                day_missions.append({
                    "area": pp["area"], "goal": pp["goal"], "tier": "secundaria",
                    "description": _format_description(t["desc"], pp["area"], pp["goal"], goal_details),
                    "base_points": t["points"],
                    "period": t["period"], "duration_min": round(duration_secondary, 1),
                    "detail": detail, "action": action,
                })

        day_missions.sort(key=lambda m: PERIOD_ORDER.get(m["period"], 1))
        for m in day_missions:
            m["date"] = current_date.isoformat()
            m["cycle"] = cycle
        plan.extend(day_missions)

    return plan


def quiz_available(area, goal):
    return bool(QUIZ_BANK.get((area, goal)))


def pick_quiz_questions(area, goal, n=5, seed=None):
    """Seleciona ate n questoes do banco para essa (area, goal). Se seed for dado
    (ex.: o id da missao), a selecao/ordem fica estavel para a mesma missao."""
    import random
    pool = list(QUIZ_BANK.get((area, goal), []))
    if not pool:
        return []
    rng = random.Random(seed)
    rng.shuffle(pool)
    return pool[:n]


def grade_quiz(questions, answers):
    """answers: lista de indices (int) escolhidos pelo usuario, na mesma ordem de
    `questions`. Retorna (acertos, total, pct, detalhe_por_questao)."""
    acertos = 0
    detalhe = []
    for i, q in enumerate(questions):
        escolhida = answers[i] if i < len(answers) else None
        correta = escolhida == q["correta"]
        if correta:
            acertos += 1
        detalhe.append({
            "pergunta": q["pergunta"], "alternativas": q["alternativas"],
            "correta_idx": q["correta"], "escolhida_idx": escolhida,
            "acertou": correta, "fonte": q["fonte"],
        })
    total = len(questions)
    pct = round((acertos / total) * 100, 1) if total else 0
    return acertos, total, pct, detalhe


# Niveis de XP (deterministico, sem IA) -- XP = vitality_points_accum, os
# pontos de rotina ja acumulados desde sempre pela conta. Limiares crescem
# progressivamente; ajustavel aqui sem tocar em nenhum outro lugar do app,
# ja que quem exibe (dashboard) so chama xp_level(total_xp).
XP_LEVELS = [0, 15, 40, 80, 140, 220, 320, 450, 600, 800, 1050]


def xp_level(total_xp):
    """Nivel (1-indexado) correspondente ao XP acumulado total."""
    level = 1
    for i, threshold in enumerate(XP_LEVELS):
        if total_xp >= threshold:
            level = i + 1
    return level


def xp_level_progress(total_xp):
    """Retorna (nivel, xp_no_nivel, xp_necessario_pro_proximo_nivel|None) --
    usado pra desenhar uma barra de progresso "faltam X XP pro nivel Y"."""
    level = xp_level(total_xp)
    idx = level - 1
    floor = XP_LEVELS[idx] if idx < len(XP_LEVELS) else XP_LEVELS[-1]
    if level < len(XP_LEVELS):
        ceiling = XP_LEVELS[level]
        return level, total_xp - floor, ceiling - floor
    return level, total_xp - floor, None


def blend_checkpoint_progress(measured_pct, self_rating_0_10):
    """
    Combina o progresso medido (pelas missoes realmente registradas) com a
    autoavaliacao do usuario (0-10 por tema). Se o usuario se avalia melhor do que o
    medido, o resultado sobe (acelera a barra rumo a conclusao); se pior, desce para
    uma posicao mais realista. O peso maior fica com o dado medido (70/30) para que a
    autoavaliacao calibre sem substituir por completo o que de fato foi feito.
    """
    self_rating_pct = max(0, min(10, self_rating_0_10)) * 10
    blended = 0.7 * measured_pct + 0.3 * self_rating_pct
    return max(0, min(100, round(blended, 1)))
