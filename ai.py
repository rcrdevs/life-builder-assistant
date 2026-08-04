# -*- coding: utf-8 -*-
"""
Life Builder Assistant -- integracao opcional com a Groq para gerar uma nota de
estrategia personalizada a partir do perfil do usuario.

Design: a IA NUNCA gera as missoes em si (isso continua 100% deterministico em
engine.py, testavel e gratuito). Ela so escreve um paragrafo curto de estrategia
que aparece no dashboard/panorama, com base num resumo compacto do perfil -- uma
unica chamada por ciclo (nao por missao), com max_tokens baixo, para manter o custo
e a latencia previsiveis. Se a chave nao estiver configurada, ou a chamada falhar por
qualquer motivo, o app funciona normalmente sem a nota -- a IA e um "tempero"
opcional, nunca uma dependencia.
"""
import json
import os
import urllib.request
import urllib.error

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.1-8b-instant")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
TIMEOUT_SECONDS = 12
# 260 chegava pra 1 paragrafo generico; agora a nota tem 1 entrada curta por
# area ativa (ate 4 areas) dentro de um JSON, entao precisa de um pouco mais
# de espaco -- ainda uma fracao de centavo por chamada no preco da Groq.
MAX_TOKENS = 420

# DeepSeek gera as questoes de quiz personalizadas por tema (missoes tipo
# "concurso"/estudo com um assunto especifico digitado pelo usuario). Usamos
# DeepSeek em vez da Groq aqui por ter uma camada gratuita mais generosa para
# esse tipo de chamada JSON maior/estruturada; a nota de estrategia continua
# na Groq. Ambas seguem o mesmo principio: recurso opcional, com fallback
# silencioso se a chave nao estiver configurada ou a chamada falhar.
#
# ATENCAO: os aliases legados "deepseek-chat"/"deepseek-reasoner" foram
# DESATIVADOS pela DeepSeek em 24/jul/2026 -- chamadas com esses nomes agora
# retornam erro. O nome atual e "deepseek-v4-flash" (modo non-thinking, que e
# o equivalente ao antigo deepseek-chat). Configuravel via env var caso a
# DeepSeek troque os nomes de novo no futuro.
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")
DEEPSEEK_MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-v4-flash")
DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"
QUIZ_TIMEOUT_SECONDS = 25
QUIZ_MAX_TOKENS = 2200

QUIZ_SYSTEM_PROMPT = (
    "Voce cria questoes de multipla escolha para um app de estudos, em portugues "
    "do Brasil. Gere questoes originais (nunca copiadas de uma prova real), "
    "tecnicamente corretas e especificas do tema pedido -- nada generico. "
    "Responda APENAS com um JSON valido (sem markdown, sem texto fora do JSON): "
    "uma lista de objetos, cada um com as chaves: "
    '"pergunta" (string), "alternativas" (lista de exatamente 4 strings), '
    '"correta" (indice 0-3 da alternativa correta), '
    '"fonte" (sempre a string fixa "Questão-modelo gerada por IA para este tema").'
)


def quiz_ai_available():
    return bool(DEEPSEEK_API_KEY)


def generate_quiz_questions(topic, n=10):
    """Gera `n` questoes de multipla escolha sobre `topic` via DeepSeek.
    Retorna uma tupla (questions, usage): `questions` e uma lista de dicts no
    formato do QUIZ_BANK estatico, ou None se a IA nao estiver configurada /
    a chamada falhar / a resposta nao vier em JSON valido -- nesses casos
    quem chamou deve cair para um fallback. `usage` e o dict de tokens
    devolvido pela API (prompt_tokens/completion_tokens/total_tokens), ou
    None se a chamada nao chegou a acontecer/retornar."""
    if not DEEPSEEK_API_KEY or not topic:
        return None, None

    user_prompt = f"Tema: {topic}\nGere {n} questões de múltipla escolha sobre esse tema, com dificuldade variada."
    body = json.dumps({
        "model": DEEPSEEK_MODEL,
        "messages": [
            {"role": "system", "content": QUIZ_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        "max_tokens": QUIZ_MAX_TOKENS,
        "temperature": 0.7,
        "response_format": {"type": "json_object"},
        # desliga o modo "thinking" do deepseek-v4-flash: queremos a resposta
        # JSON direto, sem tokens de raciocinio extra (mais rapido e mais
        # barato -- e o equivalente ao comportamento do antigo deepseek-chat).
        "thinking": {"type": "disabled"},
    }).encode("utf-8")

    req = urllib.request.Request(
        DEEPSEEK_URL, data=body, method="POST",
        headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"},
    )
    usage = None
    try:
        with urllib.request.urlopen(req, timeout=QUIZ_TIMEOUT_SECONDS) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        usage = data.get("usage")
        raw = data["choices"][0]["message"]["content"].strip()
        parsed = json.loads(raw)
        # aceita tanto uma lista direta quanto {"questoes": [...]} / {"perguntas": [...]}
        if isinstance(parsed, dict):
            for key in ("questoes", "perguntas", "questions", "items"):
                if key in parsed and isinstance(parsed[key], list):
                    parsed = parsed[key]
                    break
        if not isinstance(parsed, list):
            return None, usage

        questions = []
        for q in parsed:
            alternativas = q.get("alternativas")
            correta = q.get("correta")
            pergunta = q.get("pergunta")
            if not pergunta or not isinstance(alternativas, list) or len(alternativas) != 4:
                continue
            if not isinstance(correta, int) or not (0 <= correta <= 3):
                continue
            questions.append({
                "pergunta": pergunta, "alternativas": alternativas, "correta": correta,
                "fonte": q.get("fonte") or "Questão-modelo gerada por IA para este tema",
            })
        return (questions or None), usage
    except (urllib.error.URLError, urllib.error.HTTPError, KeyError, IndexError,
            ValueError, TimeoutError, TypeError):
        return None, usage

# Nota de estrategia: 1 chamada Groq por ciclo (14 dias) por conta -- nunca por
# missao/dia. Para dar a sensacao real de "IA que acompanha a evolucao" sem
# aumentar a frequencia de chamadas (o que quebraria o modelo de custo do
# teste gratis), a mesma chamada agora recebe o historico do ciclo anterior
# (adesao, autoavaliacao vs. progresso medido, desempenho em quiz -- tudo já
# armazenado pelo app) e devolve uma nota curta POR AREA em JSON, em vez de um
# unico paragrafo generico.
STRATEGY_SYSTEM_PROMPT = (
    "Voce e um treinador de desenvolvimento pessoal direto e objetivo, em "
    "portugues do Brasil. Voce recebe um resumo do perfil do usuario, com o "
    "nivel/peso de cada area e, quando disponivel, o historico do ciclo "
    "anterior (adesao as missoes, autoavaliacao do usuario vs. progresso "
    "medido, desempenho em quizzes). Responda APENAS com um JSON valido (sem "
    "markdown, sem texto fora do JSON): um objeto cujas chaves sao exatamente "
    "as areas listadas no perfil (ex.: \"profissional\", \"estudos\", \"saude\", "
    "\"espiritualidade\") e cujos valores sao uma nota curta (no maximo 2 "
    "frases, sem saudacao, sem markdown) com um conselho pratico e especifico "
    "para o proximo ciclo de 14 dias naquela area -- usando o historico "
    "quando ele existir (ex.: elogiar adesao alta, sugerir um ajuste se a "
    "adesao caiu, comentar a diferenca entre autoavaliacao e progresso "
    "medido). Se nao houver historico para uma area, de um conselho baseado "
    "so no nivel/peso/objetivo. Nao inclua areas fora da lista recebida. Nao "
    "invente dados que nao foram informados."
)


def ai_available():
    return bool(GROQ_API_KEY)


def build_profile_summary(user, area_label_fn, area_goals_label_fn, history=None):
    """Resume o perfil do usuario em poucas linhas -- mantem o prompt pequeno e
    barato, evitando mandar o plano de missoes inteiro para a IA.

    `history`: dict opcional area -> {"adherence_pct": float|None,
    "checkpoint": {"self_rating": int, "measured": float, "new_progress": float}|None,
    "quiz_avg_pct": float|None}, montado pelo app.py a partir de
    checkpoint_history/missions/ai_quiz_cache do ciclo anterior. Sem isso
    (ex.: primeiro ciclo do usuario), a nota fica baseada so no perfil."""
    lines = [f"Nome: {user['nome']}"]
    history = history or {}
    for area in user["areas"]:
        goals = user["goals"].get(area) or []
        if not goals:
            continue
        nivel = user["niveis"].get(area, "iniciante")
        peso = user["pesos"].get(area, 3)
        line = (
            f"- {area_label_fn(user, area)}: {area_goals_label_fn(user, area)} "
            f"(nivel {nivel}, peso {peso}/5)"
        )
        h = history.get(area)
        if h:
            extra = []
            if h.get("adherence_pct") is not None:
                extra.append(f"adesão do último ciclo: {h['adherence_pct']:.0f}%")
            cp = h.get("checkpoint")
            if cp:
                extra.append(
                    f"autoavaliação {cp['self_rating']}/10, progresso medido "
                    f"{cp['measured']:.0f}% → {cp['new_progress']:.0f}%"
                )
            if h.get("quiz_avg_pct") is not None:
                extra.append(f"desempenho médio em quiz: {h['quiz_avg_pct']:.0f}%")
            if extra:
                line += " [histórico do ciclo anterior: " + "; ".join(extra) + "]"
        lines.append(line)
    tempo = user["basic_info"].get("tempo_livre_min")
    if tempo:
        lines.append(f"Tempo livre de foco por dia: {tempo} minutos (o resto ate 8h vira missoes leves).")
    if user["extra_info"].get("dieta") == "sim":
        lines.append(f"Dieta ativada: {user['extra_info'].get('dieta_tipo', 'padrao')}.")
    notas = user["extra_info"].get("panorama_notes")
    if notas:
        lines.append(f"Observacao do usuario: {notas}")
    return "\n".join(lines)


def generate_strategy_note(profile_summary, area_keys):
    """Retorna uma tupla (notes, usage). `notes` e um dict {area_key: texto}
    com uma nota curta por area ativa, ou None se a IA nao estiver
    disponivel/configurada, `area_keys` vier vazio, ou a chamada falhar (o
    app segue funcionando normalmente sem essas notas em qualquer um desses
    casos). `usage` e o dict de tokens da API (ou None se a chamada nao
    chegou a acontecer/retornar)."""
    if not GROQ_API_KEY or not profile_summary or not area_keys:
        return None, None

    body = json.dumps({
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": STRATEGY_SYSTEM_PROMPT},
            {"role": "user", "content": profile_summary},
        ],
        "max_tokens": MAX_TOKENS,
        "temperature": 0.6,
        "response_format": {"type": "json_object"},
    }).encode("utf-8")

    req = urllib.request.Request(
        GROQ_URL, data=body, method="POST",
        headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        raw = data["choices"][0]["message"]["content"].strip()
        parsed = json.loads(raw)
        if not isinstance(parsed, dict):
            return None, data.get("usage")
        notes = {
            k: v.strip() for k, v in parsed.items()
            if k in area_keys and isinstance(v, str) and v.strip()
        }
        return (notes or None), data.get("usage")
    except (urllib.error.URLError, urllib.error.HTTPError, KeyError, IndexError,
            ValueError, TimeoutError, TypeError, AttributeError):
        return None, None
