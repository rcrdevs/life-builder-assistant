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
GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
TIMEOUT_SECONDS = 12

# ATENCAO -- nao remova o User-Agent das chamadas abaixo.
# A Groq fica atras da Cloudflare, que BLOQUEIA o User-Agent padrao do urllib
# ("Python-urllib/3.x") com HTTP 403 "error code: 1010". Sem esse header
# nenhuma chamada a Groq funciona -- e como o app engole falhas de IA em
# silencio (de proposito, pra nunca travar o usuario), o sintoma era a nota de
# estrategia simplesmente nunca aparecer, sem erro visivel em lugar nenhum.
# Verificado na marra: mesma requisicao, mesma chave -- sem UA da 403, com UA
# responde 200.
HTTP_HEADERS_BASE = {
    "Content-Type": "application/json",
    "User-Agent": "LifeBuilder/1.0 (+https://github.com/rcrdevs/life-builder-assistant)",
}


def _auth_headers(api_key):
    return dict(HTTP_HEADERS_BASE, Authorization=f"Bearer {api_key}")


def _post_json(url, api_key, payload, timeout):
    """POST JSON e devolve o dict da resposta, ou None se falhar por qualquer
    motivo (rede, HTTP, JSON invalido). Nunca levanta: toda funcionalidade de
    IA aqui e opcional e cai em fallback silencioso."""
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode("utf-8"), method="POST",
        headers=_auth_headers(api_key),
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        # 402 (saldo esgotado) e 401 (chave invalida) sao os casos que mais
        # aparecem na pratica -- logar ajuda a diferenciar "sem chave" de
        # "chave existe mas o provedor recusou", que antes eram indistinguiveis.
        try:
            detalhe = e.read().decode("utf-8")[:200]
        except Exception:
            detalhe = ""
        print(f"[ai] {url} respondeu HTTP {e.code}: {detalhe}")
        return None
    except (urllib.error.URLError, ValueError, TimeoutError) as e:
        print(f"[ai] falha ao chamar {url}: {e!r}")
        return None
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

# Regras 1 e 2 existem por um motivo concreto: pedindo so "questoes especificas
# do tema", um tema como "TI da Caixa Economica Federal" fazia o modelo inventar
# trivia institucional ("qual banco de dados a Caixa usa?"), que nao e
# verificavel, nao cai em prova e soa como questao aleatoria. O que o usuario
# quer sao as MATERIAS do edital daquele cargo.
QUIZ_SYSTEM_PROMPT = (
    "Voce elabora questoes de multipla escolha para um app de estudos, em "
    "portugues do Brasil.\n"
    "REGRAS:\n"
    "1. As questoes devem cobrar CONHECIMENTO TECNICO/ACADEMICO que cai na prova "
    "do tema -- conceitos, definicoes, legislacao, formulas, boas praticas. "
    "NUNCA pergunte sobre fatos internos de uma instituicao (qual sistema, "
    "fornecedor ou ferramenta uma empresa usa): isso nao e verificavel e nao "
    "cai em prova.\n"
    "2. Se o tema citar uma instituicao, banca ou cargo, use isso APENAS para "
    "escolher as materias do edital. NAO cite o nome da instituicao no enunciado "
    "das questoes -- pergunte sobre o conceito em si. Ex.: para 'TI da Caixa', "
    "pergunte 'O que garante a propriedade de atomicidade em uma transacao de "
    "banco de dados?', e NAO 'Qual a funcao do banco de dados da Caixa?'.\n"
    "3. Varie os assuntos: nao repita a mesma materia em duas questoes seguidas.\n"
    "4. Cada questao precisa ter uma unica alternativa correta, objetivamente "
    "verificavel, e 3 alternativas erradas plausiveis.\n"
    "5. Questoes originais -- nunca copiadas literalmente de uma prova real.\n"
    "Responda APENAS com um JSON valido (sem markdown, sem texto fora do JSON): "
    '{"questoes": [{"pergunta": string, "alternativas": [4 strings], '
    '"correta": indice 0-3, "fonte": "materia/assunto da questao"}]}'
)


def quiz_ai_available():
    """Quiz por IA funciona com QUALQUER um dos dois provedores configurados --
    ver generate_quiz_questions para a ordem de tentativa."""
    return bool(DEEPSEEK_API_KEY or GROQ_API_KEY)


def _parse_quiz_response(data):
    """Extrai e valida a lista de questoes da resposta da API. Descarta
    qualquer questao malformada em vez de confiar cegamente no modelo."""
    try:
        raw = data["choices"][0]["message"]["content"].strip()
        parsed = json.loads(raw)
    except (KeyError, IndexError, ValueError, TypeError):
        return None

    # aceita lista direta ou {"questoes": [...]} / {"perguntas": [...]}
    if isinstance(parsed, dict):
        for key in ("questoes", "perguntas", "questions", "items"):
            if isinstance(parsed.get(key), list):
                parsed = parsed[key]
                break
    if not isinstance(parsed, list):
        return None

    questions = []
    for q in parsed:
        if not isinstance(q, dict):
            continue
        alternativas, correta, pergunta = q.get("alternativas"), q.get("correta"), q.get("pergunta")
        if not pergunta or not isinstance(alternativas, list) or len(alternativas) != 4:
            continue
        if not isinstance(correta, int) or not (0 <= correta <= 3):
            continue
        questions.append({
            "pergunta": pergunta, "alternativas": alternativas, "correta": correta,
            "fonte": q.get("fonte") or "Questão gerada por IA para este tema",
        })
    return questions or None


def generate_quiz_questions(topic, n=10, extra_instrucao=None):
    """Gera `n` questoes de multipla escolha sobre `topic`.

    Tenta a DeepSeek primeiro (camada gratuita mais generosa pra JSON grande) e
    cai pra Groq se ela falhar. Esse fallback existe porque falha de provedor
    aconteceu de verdade em producao: a conta DeepSeek ficou sem saldo (HTTP 402)
    e, como o app engole erro de IA em silencio, TODO quiz passou a cair no banco
    estatico generico -- o usuario digitava "TI da Caixa" e recebia questoes
    aleatorias de portugues e direito constitucional, sem nenhum aviso.

    Retorna (questions, usage, provedor). `questions` e None se nenhum provedor
    respondeu -- ai quem chamou deve usar o banco estatico.
    """
    if not topic:
        return None, None, None

    user_prompt = (
        f"Tema: {topic}\n"
        f"Gere {n} questões de múltipla escolha sobre esse tema, com dificuldade variada."
    )
    if extra_instrucao:
        user_prompt += f"\n{extra_instrucao}"
    messages = [
        {"role": "system", "content": QUIZ_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]

    tentativas = []
    if DEEPSEEK_API_KEY:
        tentativas.append(("deepseek", DEEPSEEK_URL, DEEPSEEK_API_KEY, {
            "model": DEEPSEEK_MODEL, "messages": messages,
            "max_tokens": QUIZ_MAX_TOKENS, "temperature": 0.6,
            "response_format": {"type": "json_object"},
            # sem tokens de raciocinio extra: queremos o JSON direto
            "thinking": {"type": "disabled"},
        }))
    if GROQ_API_KEY:
        tentativas.append(("groq", GROQ_URL, GROQ_API_KEY, {
            "model": GROQ_MODEL, "messages": messages,
            "max_tokens": QUIZ_MAX_TOKENS, "temperature": 0.6,
            "response_format": {"type": "json_object"},
        }))

    for provedor, url, chave, payload in tentativas:
        data = _post_json(url, chave, payload, QUIZ_TIMEOUT_SECONDS)
        if data is None:
            continue
        questions = _parse_quiz_response(data)
        if questions:
            return questions, data.get("usage"), provedor
        print(f"[ai] {provedor} respondeu, mas sem questoes validas -- tentando o proximo provedor")

    return None, None, None


def quiz_model_for(provedor):
    """Nome do modelo usado por provedor -- pro registro de consumo de tokens."""
    return DEEPSEEK_MODEL if provedor == "deepseek" else GROQ_MODEL

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
        # direcionamento escolhido pelo usuario na conversa com o Con (ver
        # GOAL_DIRECTIONS em data.py) -- ex.: qual tradicao espiritual, que
        # tipo de treino. Da enfase ao que foi escolhido sem excluir o resto.
        direcoes = [
            d for g in goals
            for d in [(user["extra_info"].get("goal_directions") or {}).get(f"{area}:{g}")]
            if d
        ]
        if direcoes:
            line += " [direcionamento: " + "; ".join(direcoes) + "]"
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

    data = _post_json(GROQ_URL, GROQ_API_KEY, {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": STRATEGY_SYSTEM_PROMPT},
            {"role": "user", "content": profile_summary},
        ],
        "max_tokens": MAX_TOKENS,
        "temperature": 0.6,
        "response_format": {"type": "json_object"},
    }, TIMEOUT_SECONDS)
    if data is None:
        return None, None

    try:
        parsed = json.loads(data["choices"][0]["message"]["content"].strip())
        if not isinstance(parsed, dict):
            return None, data.get("usage")
        notes = {
            k: v.strip() for k, v in parsed.items()
            if k in area_keys and isinstance(v, str) and v.strip()
        }
        return (notes or None), data.get("usage")
    except (KeyError, IndexError, ValueError, TypeError, AttributeError):
        return None, data.get("usage")
