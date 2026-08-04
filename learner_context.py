# -*- coding: utf-8 -*-
"""
Life Builder Assistant -- ponto de extensao para uma futura integracao com um
gerador de cursos personalizados (outro projeto do mesmo autor).

Este modulo NAO e chamado por nenhuma rota hoje. E so a montagem do contexto
que esse outro projeto precisaria pra personalizar um curso pra um objetivo
especifico do usuario: qual objetivo, qual nivel/prioridade, qual detalhe o
usuario digitou (ex.: "Inglês", "Concurso INSS 2026"), e como ele tem se
saido (desempenho em quiz, quando existir).

Quando o contrato entre os dois projetos estiver definido, `get_goal_learning_
context` pode ser exposta por uma rota autenticada (ex.:
`/api/learner_context/<area>/<goal>`) sem precisar mudar nada aqui -- so
plugar. Ate la, fica so como funcao interna, testavel isoladamente.

Le apenas tabelas que ja existem (`missions`, `goal_progress`); nao cria
tabela nova, nao faz chamada de IA -- custo zero.
"""
from data import AREAS, GOALS, GOALS_NEEDING_DETAIL


def get_goal_learning_context(db, user, area, goal):
    """Monta o contexto de aprendizado de um (area, goal) especifico do
    usuario, no formato que um gerador de cursos externo precisaria pra
    personalizar dificuldade/topico.

    `user`: dict/RealDictRow ja carregado (ver app.get_user()), com pelo
    menos id/niveis/pesos/goal_details/custom_area_labels/custom_goal_labels.
    `db`: conexao ja aberta (ver app.get_db()).

    Retorna um dict simples (serializavel em JSON) com: rotulos de area/
    objetivo, o detalhe digitado pelo usuario, nivel/peso atuais, progresso
    medido do objetivo, e desempenho em quiz quando existir para esse
    (area, goal)."""
    key = f"{area}:{goal}"
    detalhe = (user.get("goal_details") or {}).get(key)
    if not detalhe:
        info = GOALS_NEEDING_DETAIL.get((area, goal), {})
        detalhe = info.get("fallback")

    area_label = (user.get("custom_area_labels") or {}).get(area) or AREAS.get(area, area)
    goal_label = (user.get("custom_goal_labels") or {}).get(key) or GOALS.get(area, {}).get(goal, goal)

    progress_row = db.execute(
        "SELECT progress_pct FROM goal_progress WHERE user_id=? AND area=? AND goal=?",
        (user["id"], area, goal),
    ).fetchone()

    quiz_row = db.execute(
        "SELECT AVG(completion_pct) avg_pct, COUNT(*) attempts FROM missions "
        "WHERE user_id=? AND area=? AND goal=? AND action LIKE 'quiz%%' "
        "AND completion_pct IS NOT NULL",
        (user["id"], area, goal),
    ).fetchone()

    return {
        "area": area,
        "area_label": area_label,
        "goal": goal,
        "goal_label": goal_label,
        "detail": detalhe,
        "nivel": (user.get("niveis") or {}).get(area, "iniciante"),
        "peso": (user.get("pesos") or {}).get(area),
        "progress_pct": progress_row["progress_pct"] if progress_row else None,
        "quiz_performance": {
            "avg_pct": quiz_row["avg_pct"],
            "attempts": quiz_row["attempts"],
        } if quiz_row and quiz_row["attempts"] else None,
    }
