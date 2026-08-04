# -*- coding: utf-8 -*-
"""
Life Builder Assistant — banco de conteúdo do "jogo".
Tudo aqui é dado estático/curado. A lógica de geração de plano fica em engine.py.
"""

from urllib.parse import quote as _urlquote


def amazon_link(query):
    """Link de busca real e funcional na Amazon Brasil para um livro/produto."""
    return f"https://www.amazon.com.br/s?k={_urlquote(query)}"


def _google_site_search_link(query, site):
    """Busca no Google restrita a um site especifico (site:dominio.com) --
    usado quando a busca interna do proprio site nao tem uma URL confiavel
    (ver mercadolivre_link/sympla_search_link: verificado ao vivo que o path
    de busca "direto" delas nao funciona mais -- Mercado Livre pede login
    antes de mostrar resultado, e a busca da Sympla roda só em JS no cliente,
    sem refletir o termo na URL. Busca via Google sempre funciona e ainda
    leva a resultados reais dentro do site certo."""
    return f"https://www.google.com/search?q={_urlquote(query)}+site:{site}"


def mercadolivre_link(query):
    """Busca no Mercado Livre Brasil via Google (site:mercadolivre.com.br) --
    o path de busca direto (lista.mercadolivre.com.br/<slug>) passou a exigir
    login antes de mostrar resultado (verificado ao vivo), então deixou de
    ser um link funcional sem conta."""
    return _google_site_search_link(query, "mercadolivre.com.br")


def estante_virtual_link(query):
    """Link de busca real e funcional na Estante Virtual (sebo/usados) —
    parâmetros confirmados ao vivo (type=q é obrigatório para ativar a busca)."""
    return f"https://www.estantevirtual.com.br/busca?type=q&q={_urlquote(query)}"


def youtube_search_link(query):
    """Link de busca real e funcional no YouTube."""
    return f"https://www.youtube.com/results?search_query={_urlquote(query)}"


def youtube_video(video_id, titulo):
    """Vídeo específico verificado, com thumbnail real (sem precisar de API)."""
    return {
        "titulo": titulo,
        "url": f"https://www.youtube.com/watch?v={video_id}",
        "thumbnail": f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg",
    }


def sympla_search_link(query):
    """Busca de eventos no Sympla via Google (site:sympla.com.br). A busca da
    Sympla roda inteiramente em JS no navegador (widget Algolia) -- mesmo
    digitando e apertando enter na busca real do site, o termo nunca aparece
    na URL (fica só "/#pesquisar"), então não existe um link direto
    confiável para "resultados de X no Sympla". Busca via Google contorna
    isso e ainda assim leva a eventos reais dentro do Sympla."""
    return _google_site_search_link(query, "sympla.com.br")


def livro(titulo, autor, link=None, preco_nota="Ver preço atual na loja"):
    """Um livro recomendado, com opções de aquisição em 3 lojas reais (busca
    funcional em cada uma). Se `link` for passado, é um link direto verificado
    para um produto específico (usado como a opção "Amazon"); as demais opções
    (Mercado Livre, Estante Virtual) sempre usam busca por título+autor, já que
    não há como verificar manualmente um link exato de produto em cada loja."""
    query = f"{titulo} {autor}"
    opcoes = [
        {"loja": "Amazon", "url": link or amazon_link(query), "preco_nota": preco_nota},
        {"loja": "Mercado Livre", "url": mercadolivre_link(query), "preco_nota": "Ver preço atual (novo ou usado)"},
        {"loja": "Estante Virtual (sebo)", "url": estante_virtual_link(query), "preco_nota": "Ver preço atual (usado)"},
    ]
    return {
        "titulo": titulo, "autor": autor,
        "link": opcoes[0]["url"], "preco_nota": preco_nota,
        "opcoes": opcoes,
    }


def video_busca(titulo_busca):
    return {"titulo": titulo_busca, "url": youtube_search_link(titulo_busca), "thumbnail": None}


def evento(desc, busca):
    return {"desc": desc, "link": sympla_search_link(busca)}


# ---------------------------------------------------------------------------
# ÁREAS — 10 categorias, multi-seleção no onboarding
# ---------------------------------------------------------------------------
AREAS = {
    "profissional": "Profissional",
    "estudos": "Estudos",
    "saude": "Saúde",
    "espiritualidade": "Espiritualidade",
}

AREA_ICONS = {
    "profissional": "▲",
    "estudos": "◆",
    "saude": "⬡",
    "espiritualidade": "✶",
    "rotina": "∴",
}

ROTINA_LABEL = "Rotina Diária"

GOALS = {
    "profissional": {
        "concurso": "Passar em um concurso público",
        "vaga": "Conseguir uma vaga de emprego específica",
        "promocao": "Conseguir uma promoção",
    },
    "estudos": {
        "idioma": "Aprender um novo idioma",
        "bolsa": "Conseguir bolsa em faculdade renomada",
        "intercambio": "Fazer um intercâmbio",
    },
    "saude": {
        "perder_peso": "Perder peso",
        "ganhar_massa": "Ganhar massa muscular",
        "maratona": "Correr uma maratona / prova de resistência",
        "manter_forma": "Manter a forma / saúde geral",
        "paideia_basico": "Paideia — nível básico (postura, mobilidade, bem-estar)",
        "paideia_moderado": "Paideia — nível moderado (condicionamento geral)",
        "paideia_avancado": "Paideia — nível avançado (ganho de massa muscular)",
    },
    "espiritualidade": {
        "meditacao": "Estabelecer uma prática regular de meditação",
        "proposito": "Encontrar mais senso de propósito",
        "gratidao": "Cultivar uma prática de gratidão",
    },
}

# ---------------------------------------------------------------------------
# OBJETIVOS QUE PEDEM UM DETALHE PERSONALIZADO — ex.: qual concurso, qual
# idioma, qual instrumento. O texto digitado substitui "{detalhe}" nas
# descrições de missão que o contêm (ver MISSION_TEMPLATES).
# ---------------------------------------------------------------------------
GOALS_NEEDING_DETAIL = {
    ("profissional", "concurso"): {
        "prompt": "Qual concurso público?",
        "placeholder": "Ex: Concurso INSS 2026, Banco do Brasil, TRT...",
        "fallback": "edital escolhido",
    },
    ("profissional", "vaga"): {
        "prompt": "Qual cargo ou empresa você está mirando?",
        "placeholder": "Ex: Analista de Dados na Nubank",
        "fallback": "área desejada",
    },
    ("estudos", "idioma"): {
        "prompt": "Qual idioma?",
        "placeholder": "Ex: Inglês, Espanhol, Japonês...",
        "fallback": "idioma escolhido",
    },
    ("estudos", "bolsa"): {
        "prompt": "Qual bolsa, faculdade ou programa?",
        "placeholder": "Ex: Bolsa USP, Ciência sem Fronteiras...",
        "fallback": "programa escolhido",
    },
    ("estudos", "intercambio"): {
        "prompt": "Para onde (país/cidade) e em que idioma?",
        "placeholder": "Ex: Canadá, inglês",
        "fallback": "destino escolhido",
    },
    ("saude", "maratona"): {
        "prompt": "Qual prova você está treinando para correr?",
        "placeholder": "Ex: Maratona de São Paulo 2026",
        "fallback": "a prova",
    },
}

ROTINA_MISSIONS = [
    {"desc": "Beber pelo menos 2 litros de água ao longo do dia", "stat": "resistencia", "points": 1, "period": "manha"},
    {"desc": "Planejar as 3 prioridades do dia em 5 minutos", "stat": "disciplina", "points": 1, "period": "manha"},
    {"desc": "Tomar um café da manhã com proteína, sem pressa", "stat": "resistencia", "points": 1, "period": "manha"},
    {"desc": "Fazer uma pausa de 10 minutos longe de telas", "stat": "foco", "points": 1, "period": "tarde"},
    {"desc": "Alongar o corpo por 5 minutos entre tarefas", "stat": "resistencia", "points": 1, "period": "tarde"},
    {"desc": "Revisar o progresso das prioridades do dia", "stat": "foco", "points": 1, "period": "tarde"},
    {"desc": "Escrever 3 linhas no diário sobre o dia", "stat": "criatividade", "points": 1, "period": "noite"},
    {"desc": "Desligar as telas 30 minutos antes de dormir", "stat": "disciplina", "points": 1, "period": "noite"},
    {"desc": "Preparar tudo o que precisa para amanhã antes de dormir", "stat": "disciplina", "points": 1, "period": "noite"},
]

MISSION_TEMPLATES = {
    ("profissional", "concurso"): [
        {"desc": "Resolver 15 questões de matéria objetiva do {detalhe}", "stat": "inteligencia", "points": 2, "nivel": "todos", "period": "manha", "action": "quiz:15"},
        {"desc": "Revisar 1 tópico da matéria mais fraca com resumo próprio", "stat": "disciplina", "points": 2, "nivel": "todos", "period": "tarde"},
        {"desc": "Fazer um simulado cronometrado de 20 questões do {detalhe}", "stat": "foco", "points": 3, "nivel": "intermediario", "period": "tarde", "action": "quiz:20"},
        {"desc": "Ler a lei seca de um artigo do edital", "stat": "inteligencia", "points": 1, "nivel": "iniciante", "period": "noite"},
        {"desc": "Revisar os erros do último simulado", "stat": "inteligencia", "points": 2, "nivel": "todos", "period": "noite"},
        {"desc": "Fazer cartões de revisão (flashcards) de um tópico difícil", "stat": "disciplina", "points": 1, "nivel": "todos", "period": "manha"},
    ],
    ("profissional", "vaga"): [
        {"desc": "Atualizar uma seção do currículo/portfólio", "stat": "disciplina", "points": 1, "nivel": "todos", "period": "manha"},
        {"desc": "Aplicar para 2 vagas de {detalhe}", "stat": "disciplina", "points": 2, "nivel": "todos", "period": "tarde"},
        {"desc": "Praticar uma resposta de entrevista comportamental (método STAR)", "stat": "foco", "points": 2, "nivel": "todos", "period": "tarde"},
        {"desc": "Estudar a empresa/área de {detalhe} e mapear 3 perguntas para a entrevista", "stat": "inteligencia", "points": 2, "nivel": "intermediario", "period": "noite"},
        {"desc": "Pedir para alguém revisar seu currículo/LinkedIn", "stat": "disciplina", "points": 1, "nivel": "todos", "period": "manha"},
    ],
    ("profissional", "promocao"): [
        {"desc": "Documentar uma entrega relevante da semana", "stat": "disciplina", "points": 1, "nivel": "todos", "period": "manha"},
        {"desc": "Pedir feedback direto a um gestor ou par sobre uma entrega", "stat": "foco", "points": 2, "nivel": "todos", "period": "tarde"},
        {"desc": "Estudar uma habilidade exigida no próximo nível do cargo", "stat": "inteligencia", "points": 2, "nivel": "todos", "period": "noite"},
        {"desc": "Assumir voluntariamente uma tarefa fora da zona de conforto", "stat": "disciplina", "points": 3, "nivel": "avancado", "period": "tarde"},
    ],
    ("estudos", "idioma"): [
        {"desc": "20 minutos de app de {detalhe} (Duolingo/Anki/etc.)", "stat": "disciplina", "points": 1, "nivel": "todos", "period": "manha"},
        {"desc": "Assistir a um vídeo/podcast em {detalhe} com legenda", "stat": "inteligencia", "points": 2, "nivel": "todos", "period": "tarde"},
        {"desc": "Praticar conversação em {detalhe} por 15 minutos (tandem ou tutor)", "stat": "foco", "points": 3, "nivel": "intermediario", "period": "noite"},
        {"desc": "Escrever um parágrafo curto em {detalhe}", "stat": "criatividade", "points": 2, "nivel": "todos", "period": "noite"},
        {"desc": "Revisar 10 palavras novas de vocabulário em {detalhe}", "stat": "inteligencia", "points": 1, "nivel": "iniciante", "period": "manha"},
        {"desc": "Fazer um quiz de gramática e vocabulário de {detalhe}", "stat": "inteligencia", "points": 2, "nivel": "todos", "period": "tarde", "action": "quiz:5"},
    ],
    ("estudos", "bolsa"): [
        {"desc": "Estudar 1 tópico de prova padronizada para {detalhe}", "stat": "inteligencia", "points": 2, "nivel": "todos", "period": "manha"},
        {"desc": "Escrever/revisar um parágrafo da carta de motivação para {detalhe}", "stat": "criatividade", "points": 2, "nivel": "todos", "period": "tarde"},
        {"desc": "Pesquisar requisitos específicos de {detalhe}", "stat": "inteligencia", "points": 1, "nivel": "iniciante", "period": "noite"},
        {"desc": "Fazer um simulado de prova cronometrado", "stat": "foco", "points": 3, "nivel": "avancado", "period": "tarde"},
    ],
    ("estudos", "intercambio"): [
        {"desc": "Pesquisar requisitos e prazos do programa para {detalhe}", "stat": "inteligencia", "points": 1, "nivel": "todos", "period": "manha"},
        {"desc": "Praticar o idioma do destino ({detalhe})", "stat": "disciplina", "points": 2, "nivel": "todos", "period": "tarde"},
        {"desc": "Organizar a documentação necessária (visto, passaporte etc.)", "stat": "disciplina", "points": 2, "nivel": "intermediario", "period": "noite"},
        {"desc": "Conversar com alguém que já fez intercâmbio para {detalhe}", "stat": "foco", "points": 2, "nivel": "todos", "period": "tarde"},
    ],
    ("saude", "perder_peso"): [
        {"desc": "Caminhada ou cardio leve de 30 minutos", "stat": "resistencia", "points": 2, "nivel": "todos", "period": "manha"},
        {"desc": "Registrar as refeições do dia (diário alimentar)", "stat": "disciplina", "points": 1, "nivel": "todos", "period": "tarde"},
        {"desc": "Treino de força de 40 minutos", "stat": "forca", "points": 3, "nivel": "intermediario", "period": "tarde"},
        {"desc": "Preparar uma refeição saudável em vez de pedir delivery", "stat": "disciplina", "points": 2, "nivel": "todos", "period": "noite"},
        {"desc": "Subir escadas em vez de usar elevador hoje", "stat": "resistencia", "points": 1, "nivel": "iniciante", "period": "tarde"},
    ],
    ("saude", "ganhar_massa"): [
        {"desc": "Treino de hipertrofia focado em um grupo muscular", "stat": "forca", "points": 3, "nivel": "todos", "period": "tarde"},
        {"desc": "Garantir a meta de proteína do dia", "stat": "disciplina", "points": 1, "nivel": "todos", "period": "manha"},
        {"desc": "Registrar cargas/repetições no diário de treino", "stat": "disciplina", "points": 1, "nivel": "todos", "period": "tarde"},
        {"desc": "Sessão de mobilidade/alongamento pós-treino", "stat": "resistencia", "points": 1, "nivel": "todos", "period": "noite"},
    ],
    ("saude", "maratona"): [
        {"desc": "Corrida de ritmo leve (preparação para {detalhe})", "stat": "resistencia", "points": 3, "nivel": "todos", "period": "manha"},
        {"desc": "Treino intervalado (tiros curtos)", "stat": "resistencia", "points": 3, "nivel": "intermediario", "period": "tarde"},
        {"desc": "Fortalecimento de core e pernas (prevenção de lesão)", "stat": "forca", "points": 2, "nivel": "todos", "period": "tarde"},
        {"desc": "Long run da semana, de olho em {detalhe}", "stat": "resistencia", "points": 4, "nivel": "avancado", "period": "manha"},
    ],
    ("saude", "manter_forma"): [
        {"desc": "Atividade física de 30 minutos à sua escolha", "stat": "resistencia", "points": 2, "nivel": "todos", "period": "manha"},
        {"desc": "Beber água suficiente e dormir 7h+ hoje", "stat": "disciplina", "points": 1, "nivel": "todos", "period": "noite"},
        {"desc": "Treino de mobilidade ou alongamento", "stat": "forca", "points": 1, "nivel": "todos", "period": "tarde"},
    ],
    ("saude", "paideia_basico"): [
        {"desc": "10 minutos de alongamento e mobilidade geral", "stat": "resistencia", "points": 2, "nivel": "todos", "period": "manha"},
        {"desc": "Caminhada leve de 20 minutos", "stat": "resistencia", "points": 2, "nivel": "todos", "period": "tarde"},
        {"desc": "Exercícios de postura (10 min, sentado ou em pé)", "stat": "forca", "points": 1, "nivel": "todos", "period": "noite"},
    ],
    ("saude", "paideia_moderado"): [
        {"desc": "Treino de condicionamento geral de 30 minutos", "stat": "resistencia", "points": 3, "nivel": "todos", "period": "manha"},
        {"desc": "Circuito funcional de corpo inteiro (20 min)", "stat": "forca", "points": 2, "nivel": "intermediario", "period": "tarde"},
        {"desc": "Mobilidade e alongamento pós-treino", "stat": "resistencia", "points": 1, "nivel": "todos", "period": "noite"},
    ],
    ("saude", "paideia_avancado"): [
        {"desc": "Treino de hipertrofia de 50 minutos", "stat": "forca", "points": 3, "nivel": "todos", "period": "tarde"},
        {"desc": "Garantir a meta de proteína do dia", "stat": "disciplina", "points": 1, "nivel": "todos", "period": "manha"},
        {"desc": "Registrar cargas/repetições no diário de treino", "stat": "disciplina", "points": 1, "nivel": "todos", "period": "tarde"},
    ],
    ("espiritualidade", "meditacao"): [
        {"desc": "10 minutos de meditação guiada", "stat": "disciplina", "points": 2, "nivel": "todos", "period": "manha"},
        {"desc": "5 minutos de respiração consciente antes de dormir", "stat": "foco", "points": 1, "nivel": "todos", "period": "noite"},
        {"desc": "Meditação silenciosa de 15-20 minutos", "stat": "disciplina", "points": 3, "nivel": "avancado", "period": "manha"},
    ],
    ("espiritualidade", "proposito"): [
        {"desc": "Escrever sobre o que deu sentido ao seu dia", "stat": "criatividade", "points": 2, "nivel": "todos", "period": "noite"},
        {"desc": "Ler um texto inspirador ou filosófico por 15 minutos", "stat": "inteligencia", "points": 2, "nivel": "todos", "period": "manha"},
        {"desc": "Refletir sobre um valor pessoal e como vivê-lo hoje", "stat": "disciplina", "points": 1, "nivel": "todos", "period": "manha"},
    ],
    ("espiritualidade", "gratidao"): [
        {"desc": "Escrever 3 coisas pelas quais é grato hoje", "stat": "criatividade", "points": 1, "nivel": "todos", "period": "noite"},
        {"desc": "Agradecer pessoalmente a alguém específico", "stat": "foco", "points": 2, "nivel": "todos", "period": "tarde"},
        {"desc": "Revisar a semana e notar 3 momentos positivos", "stat": "disciplina", "points": 1, "nivel": "todos", "period": "noite"},
    ],
}

# ---------------------------------------------------------------------------
# BANCO DE QUESTÕES (simulado in-app) — chave: (area, goal) -> lista de questões.
#
# IMPORTANTE (honestidade de conteúdo): estas são questões-MODELO que eu escrevi
# no estilo típico de bancas de concurso (Cebraspe/FGV/FCC), cobrindo os temas
# mais comuns (Português, Direito Constitucional, Raciocínio Lógico,
# Conhecimentos Gerais, Informática). NÃO são questões verbatim de um edital
# real específico — eu não tenho como verificar/atribuir com precisão a um
# "Edital X, Ano Y" real para o concurso que cada usuário for digitar. Por isso
# a "fonte" de cada questão é rotulada como modelo, não como uma prova real.
# Fica documentado também no dashboard, para não passar a impressão de que são
# questões de uma prova real específica.
# ---------------------------------------------------------------------------
QUIZ_BANK = {
    ("profissional", "concurso"): [
        {
            "pergunta": "Assinale a alternativa em que a concordância verbal está de acordo com a norma-padrão:",
            "alternativas": [
                "Fazem dois anos que ele prestou o concurso.",
                "Existem vários candidatos aptos para a vaga.",
                "Deve haver muitos candidatos na fila.",
                "Houveram poucas vagas nesse edital.",
            ],
            "correta": 1,
            "fonte": "Questão modelo (Português — concordância verbal)",
        },
        {
            "pergunta": "Segundo a Constituição Federal de 1988, são Poderes da União, independentes e harmônicos entre si:",
            "alternativas": [
                "o Executivo, o Legislativo e o Ministério Público",
                "o Executivo, o Legislativo e o Judiciário",
                "o Legislativo, o Judiciário e o Tribunal de Contas",
                "o Executivo, o Judiciário e a Defensoria Pública",
            ],
            "correta": 1,
            "fonte": "Questão modelo (Direito Constitucional — Art. 2º, CF/88)",
        },
        {
            "pergunta": "Se hoje é quarta-feira, que dia da semana será daqui a 100 dias?",
            "alternativas": ["Segunda-feira", "Quinta-feira", "Sexta-feira", "Domingo"],
            "correta": 1,
            "fonte": "Questão modelo (Raciocínio Lógico — aritmética modular)",
        },
        {
            "pergunta": "Um dos princípios expressos da Administração Pública no Art. 37 da CF/88 é:",
            "alternativas": ["Subsidiariedade", "Eficiência", "Presunção de inocência", "Livre concorrência"],
            "correta": 1,
            "fonte": "Questão modelo (Direito Administrativo — LIMPE)",
        },
        {
            "pergunta": "Na frase 'Ele foi o candidato que mais estudou', o termo destacado exerce a função de:",
            "alternativas": ["Sujeito", "Pronome relativo", "Conjunção coordenativa", "Objeto direto"],
            "correta": 1,
            "fonte": "Questão modelo (Português — classes de palavras)",
        },
        {
            "pergunta": "Em uma prova com 60 questões, um candidato acertou 75% delas. Quantas questões ele errou?",
            "alternativas": ["12", "15", "18", "20"],
            "correta": 1,
            "fonte": "Questão modelo (Raciocínio Lógico — porcentagem)",
        },
        {
            "pergunta": "O remédio constitucional destinado a proteger o direito de locomoção é:",
            "alternativas": ["Mandado de segurança", "Habeas corpus", "Habeas data", "Ação popular"],
            "correta": 1,
            "fonte": "Questão modelo (Direito Constitucional — remédios constitucionais)",
        },
        {
            "pergunta": "Qual das opções abaixo é um atalho comum para 'copiar' na maioria dos sistemas operacionais?",
            "alternativas": ["Ctrl+V", "Ctrl+C", "Ctrl+X", "Ctrl+Z"],
            "correta": 1,
            "fonte": "Questão modelo (Informática básica)",
        },
    ],
}

RECOMMENDATIONS = {
    ("profissional", "concurso"): {
        "livros": [
            livro("Como se Preparar para Concursos Públicos com Alto Rendimento", "Rogério Neiva",
                  link="https://www.amazon.com.br/Como-Preparar-Concursos-P%C3%BAblicos-Rendimento/dp/8530932935"),
            livro("Português Descomplicado", "William Douglas e Renato Aquino",
                  link=amazon_link("Português Descomplicado William Douglas Renato Aquino")),
        ],
        "conteudo": [video_busca("Resolução comentada de provas de concurso público"),
                     video_busca("Como estudar legislação seca para concurso")],
        "evento": evento("Simulado presencial de concurso ou grupo de estudos", "simulado concurso público"),
    },
    ("profissional", "vaga"): {
        "livros": [livro("Never Split the Difference", "Chris Voss"),
                   livro("Não Se Apega, Não", "Petter Pergola")],
        "conteudo": [video_busca("Como se preparar para entrevista de emprego método STAR"),
                     video_busca("Mock interview entrevista de emprego")],
        "evento": evento("Meetup de recrutamento ou feira de carreiras", "feira de carreiras tech"),
    },
    ("profissional", "promocao"): {
        "livros": [livro("Radical Candor", "Kim Scott"),
                   livro("The First 90 Days", "Michael Watkins")],
        "conteudo": [video_busca("Como pedir promoção no trabalho"),
                     video_busca("Liderança e gestão de equipes")],
        "evento": evento("Workshop de liderança", "workshop liderança"),
    },
    ("estudos", "idioma"): {
        "livros": [livro("Fluent Forever", "Gabriel Wyner")],
        "conteudo": [video_busca("Como aprender um idioma sozinho método eficiente"),
                     video_busca("Podcast para praticar listening idioma")],
        "evento": evento("Encontro de conversação (language exchange)", "language exchange encontro"),
    },
    ("estudos", "bolsa"): {
        "livros": [livro("Redação Nota 1000 no ENEM", "Adriana Andrade e Thiago Guilherme")],
        "conteudo": [video_busca("Como escrever carta de motivação para bolsa de estudos"),
                     video_busca("Aulas gratuitas Khan Academy vestibular")],
        "evento": evento("Feira de universidades ou orientação vocacional", "feira de universidades"),
    },
    ("estudos", "intercambio"): {
        "livros": [livro("Guia do Intercâmbio", "Estudar Fora")],
        "conteudo": [video_busca("Relato real de intercâmbio dicas"),
                     video_busca("Como conseguir visto de estudante")],
        "evento": evento("Feira de intercâmbio", "feira de intercâmbio"),
    },
    ("saude", "perder_peso"): {
        "livros": [livro("Emagreça Comendo", "Sophie Deram")],
        "conteudo": [video_busca("Treino HIIT para iniciantes em casa"),
                     video_busca("Como funciona déficit calórico explicação")],
        "evento": evento("Corrida de rua 5km ou grupo de caminhada", "corrida de rua 5km"),
    },
    ("saude", "ganhar_massa"): {
        "livros": [livro("Treinamento de Força para Todos", "Vitor Sorrentino")],
        "conteudo": [video_busca("Treino de hipertrofia natural para iniciantes"),
                     video_busca("Quanto de proteína comer por dia hipertrofia")],
        "evento": evento("Campeonato local de levantamento de peso amador", "campeonato levantamento de peso amador"),
    },
    ("saude", "maratona"): {
        "livros": [livro("Nascidos para Correr", "Christopher McDougall")],
        "conteudo": [video_busca("Plano de treino para primeira maratona iniciante"),
                     video_busca("Como evitar lesões correndo")],
        "evento": evento("Prova de rua de 10km ou meia-maratona", "prova de rua 10km meia maratona"),
    },
    ("saude", "manter_forma"): {
        "livros": [livro("Como Não Morrer", "Michael Greger")],
        "conteudo": [video_busca("Aula de yoga para iniciantes completa"),
                     video_busca("Mobilidade e alongamento diário")],
        "evento": evento("Corrida de rua leve ou aula experimental", "aula experimental yoga pilates"),
    },
    ("saude", "paideia_basico"): {
        "livros": [livro("A Paideia", "Werner Jaeger")],
        "conteudo": [video_busca("Mobilidade e alongamento para iniciantes"),
                     video_busca("Postura correta no dia a dia")],
        "evento": evento("Aula experimental de yoga, pilates ou alongamento", "aula experimental yoga pilates alongamento"),
    },
    ("saude", "paideia_moderado"): {
        "livros": [livro("Corpo e Alma", "George Leonard")],
        "conteudo": [video_busca("Treino funcional para nível intermediário"),
                     video_busca("Circuito funcional corpo inteiro em casa")],
        "evento": evento("Aula experimental de crossfit ou funcional", "aula experimental crossfit funcional"),
    },
    ("saude", "paideia_avancado"): {
        "livros": [livro("Treinamento de Força para Todos", "Vitor Sorrentino")],
        "conteudo": [video_busca("Treino de hipertrofia natural para iniciantes"),
                     video_busca("Técnica correta agachamento e supino")],
        "evento": evento("Campeonato local de levantamento de peso amador", "campeonato levantamento de peso amador"),
    },
    ("espiritualidade", "meditacao"): {
        "livros": [livro("A Arte da Meditação", "Matthieu Ricard")],
        "conteudo": [video_busca("Meditação guiada iniciantes 10 minutos"),
                     video_busca("Como manter constância na meditação")],
        "evento": evento("Retiro de meditação de um dia", "retiro de meditação"),
    },
    ("espiritualidade", "proposito"): {
        "livros": [livro("Em Busca de Sentido", "Viktor Frankl")],
        "conteudo": [video_busca("Filosofia estoica aplicada ao dia a dia"),
                     video_busca("Como encontrar propósito de vida")],
        "evento": evento("Círculo de discussão filosófica", "círculo de discussão filosófica"),
    },
    ("espiritualidade", "gratidao"): {
        "livros": [livro("O Poder da Gratidão", "Deepak Chopra")],
        "conteudo": [video_busca("Como praticar gratidão diariamente"),
                     video_busca("Diário de gratidão benefícios")],
        "evento": evento("Roda de conversa e reflexão semanal", "roda de conversa reflexão"),
    },
}

NIVEL_LABELS = {"iniciante": "Iniciante", "intermediario": "Intermediário", "avancado": "Avançado"}
NIVEL_BONUS = {"iniciante": 0, "intermediario": 3, "avancado": 6}

PERIOD_LABELS = {"manha": "Manhã", "tarde": "Tarde", "noite": "Noite"}
PERIOD_ORDER = {"manha": 0, "tarde": 1, "noite": 2}

PAIDEIA_INTRO = (
    "Na Grecia Antiga, Paideia era o ideal de formacao completa do ser humano - corpo, "
    "mente e carater desenvolvidos juntos, nao um em detrimento do outro. Voce nao escolheu "
    "nenhum objetivo fisico, entao propomos incluir uma trilha minima de corpo no seu Life "
    "Build, no nivel que fizer sentido para voce agora."
)

PAIDEIA_LEVELS = {
    "paideia_basico": {
        "label": "Basico",
        "desc": "Manter a boa forma: postura, mobilidade, alongamentos e caminhadas leves.",
    },
    "paideia_moderado": {
        "label": "Moderado",
        "desc": "Algum desenvolvimento fisico real: condicionamento geral e treinos funcionais.",
    },
    "paideia_avancado": {
        "label": "Avancado",
        "desc": "Ganho de massa muscular: treino de forca/hipertrofia estruturado.",
    },
}


def generic_mission_templates(label):
    return [
        {"desc": "Dedique 20-30 minutos a: " + label, "stat": "disciplina", "points": 2, "nivel": "todos", "period": "manha"},
        {"desc": "Estude ou pesquise algo novo sobre: " + label, "stat": "inteligencia", "points": 1, "nivel": "todos", "period": "tarde"},
        {"desc": "Registre o progresso de hoje em: " + label, "stat": "disciplina", "points": 1, "nivel": "todos", "period": "noite"},
    ]


def generic_recommendation(label):
    return {
        "livros": [livro(f"Livros sobre {label}", "", link=amazon_link(label), preco_nota="Ver opções na loja")],
        "conteudo": [video_busca(f"{label} para iniciantes"), video_busca(f"como aprender {label}")],
        "evento": evento(f"evento ou encontro local relacionado a {label}", label),
    }

# ---------------------------------------------------------------------------
# DIETA — refeições com porções e macros aproximados, por tipo de dieta.
# Uso ilustrativo/geral (não substitui orientação de nutricionista). Ativado
# apenas se o usuário optar por incluir sugestões de dieta no onboarding.
# ---------------------------------------------------------------------------
DIET_MEALS = {
    "padrao": {
        "cafe": [
            {"nome": "Ovos com aveia e fruta", "ingredientes": [
                "3 ovos mexidos (150g)", "3 colheres de sopa de aveia (30g)",
                "1 banana média (100g)", "1 xícara de café ou chá sem açúcar"],
             "kcal": 430, "proteina_g": 26, "carboidrato_g": 45, "gordura_g": 16},
            {"nome": "Pão integral com ovo e queijo", "ingredientes": [
                "2 fatias de pão integral (60g)", "2 ovos (100g)",
                "1 fatia de queijo branco (20g)", "1 copo de suco natural (200ml)"],
             "kcal": 410, "proteina_g": 24, "carboidrato_g": 42, "gordura_g": 15},
        ],
        "almoco": [
            {"nome": "Frango, arroz, feijão e salada", "ingredientes": [
                "150g de peito de frango grelhado", "4 colheres de sopa de arroz (100g)",
                "1 concha de feijão (80g)", "salada de folhas e tomate à vontade",
                "1 colher de chá de azeite"],
             "kcal": 560, "proteina_g": 45, "carboidrato_g": 55, "gordura_g": 14},
            {"nome": "Carne magra com batata-doce e legumes", "ingredientes": [
                "150g de patinho ou coxão mole grelhado", "150g de batata-doce cozida",
                "legumes salteados (cenoura, abobrinha) à vontade", "1 colher de chá de azeite"],
             "kcal": 520, "proteina_g": 42, "carboidrato_g": 48, "gordura_g": 15},
        ],
        "jantar": [
            {"nome": "Peixe grelhado com legumes", "ingredientes": [
                "150g de filé de peixe grelhado", "batata ou mandioquinha cozida (100g)",
                "legumes no vapor à vontade", "1 colher de chá de azeite"],
             "kcal": 420, "proteina_g": 36, "carboidrato_g": 35, "gordura_g": 13},
            {"nome": "Omelete com salada", "ingredientes": [
                "3 ovos (150g)", "1 fatia de queijo branco (20g)",
                "salada verde à vontade", "1 fatia de pão integral (30g)"],
             "kcal": 390, "proteina_g": 28, "carboidrato_g": 22, "gordura_g": 20},
        ],
        "lanche": [
            {"nome": "Iogurte com granola e fruta", "ingredientes": [
                "1 pote de iogurte natural (170g)", "2 colheres de sopa de granola (20g)",
                "1 fruta picada (100g)"],
             "kcal": 260, "proteina_g": 12, "carboidrato_g": 38, "gordura_g": 7},
            {"nome": "Sanduíche natural", "ingredientes": [
                "2 fatias de pão integral (60g)", "80g de peito de peru ou frango desfiado",
                "folhas verdes e tomate à vontade"],
             "kcal": 280, "proteina_g": 20, "carboidrato_g": 32, "gordura_g": 6},
        ],
    },
    "vegetariano": {
        "cafe": [
            {"nome": "Omelete com queijo e torrada", "ingredientes": [
                "3 ovos (150g)", "1 fatia de queijo branco (20g)",
                "2 fatias de pão integral torradas (60g)", "1 fruta (100g)"],
             "kcal": 420, "proteina_g": 25, "carboidrato_g": 44, "gordura_g": 15},
            {"nome": "Vitamina de banana com aveia", "ingredientes": [
                "1 copo de leite (200ml)", "1 banana (100g)",
                "3 colheres de sopa de aveia (30g)", "1 colher de sopa de pasta de amendoim (15g)"],
             "kcal": 440, "proteina_g": 18, "carboidrato_g": 55, "gordura_g": 16},
        ],
        "almoco": [
            {"nome": "Grão-de-bico, arroz integral e legumes", "ingredientes": [
                "1 concha de grão-de-bico cozido (120g)", "4 colheres de sopa de arroz integral (100g)",
                "legumes salteados à vontade", "1 colher de chá de azeite"],
             "kcal": 520, "proteina_g": 20, "carboidrato_g": 75, "gordura_g": 13},
            {"nome": "Tofu grelhado com quinoa e salada", "ingredientes": [
                "150g de tofu grelhado", "4 colheres de sopa de quinoa cozida (100g)",
                "salada de folhas à vontade", "1 colher de chá de azeite"],
             "kcal": 480, "proteina_g": 26, "carboidrato_g": 50, "gordura_g": 16},
        ],
        "jantar": [
            {"nome": "Omelete de legumes com salada", "ingredientes": [
                "3 ovos (150g)", "legumes picados (abobrinha, cenoura) à vontade",
                "salada verde à vontade", "1 fatia de pão integral (30g)"],
             "kcal": 380, "proteina_g": 24, "carboidrato_g": 25, "gordura_g": 19},
            {"nome": "Sopa de lentilha com legumes", "ingredientes": [
                "1 prato de sopa de lentilha (300ml)", "legumes variados à vontade",
                "1 fatia de pão integral (30g)"],
             "kcal": 360, "proteina_g": 18, "carboidrato_g": 50, "gordura_g": 8},
        ],
        "lanche": [
            {"nome": "Iogurte com castanhas", "ingredientes": [
                "1 pote de iogurte natural (170g)", "1 punhado de castanhas (20g)"],
             "kcal": 260, "proteina_g": 11, "carboidrato_g": 18, "gordura_g": 15},
            {"nome": "Queijo com fruta", "ingredientes": [
                "2 fatias de queijo branco (40g)", "1 fruta (100g)"],
             "kcal": 200, "proteina_g": 12, "carboidrato_g": 20, "gordura_g": 8},
        ],
    },
    "vegano": {
        "cafe": [
            {"nome": "Vitamina de banana com aveia e pasta de amendoim", "ingredientes": [
                "1 copo de leite vegetal (200ml)", "1 banana (100g)",
                "3 colheres de sopa de aveia (30g)", "1 colher de sopa de pasta de amendoim (15g)"],
             "kcal": 430, "proteina_g": 14, "carboidrato_g": 58, "gordura_g": 16},
            {"nome": "Torrada com pasta de grão-de-bico (homus)", "ingredientes": [
                "2 fatias de pão integral (60g)", "3 colheres de sopa de homus (60g)",
                "1 fruta (100g)"],
             "kcal": 380, "proteina_g": 13, "carboidrato_g": 55, "gordura_g": 12},
        ],
        "almoco": [
            {"nome": "Tofu com arroz integral e legumes", "ingredientes": [
                "150g de tofu grelhado", "4 colheres de sopa de arroz integral (100g)",
                "legumes salteados à vontade", "1 colher de chá de azeite"],
             "kcal": 480, "proteina_g": 24, "carboidrato_g": 60, "gordura_g": 14},
            {"nome": "Grão-de-bico e quinoa com salada", "ingredientes": [
                "1 concha de grão-de-bico cozido (120g)", "4 colheres de sopa de quinoa (100g)",
                "salada de folhas à vontade", "1 colher de chá de azeite"],
             "kcal": 500, "proteina_g": 20, "carboidrato_g": 70, "gordura_g": 13},
        ],
        "jantar": [
            {"nome": "Lentilha refogada com legumes", "ingredientes": [
                "1 concha de lentilha cozida (120g)", "legumes salteados à vontade",
                "4 colheres de sopa de arroz (100g)"],
             "kcal": 420, "proteina_g": 18, "carboidrato_g": 65, "gordura_g": 8},
            {"nome": "Sopa de abóbora com grão-de-bico", "ingredientes": [
                "1 prato de sopa de abóbora (300ml)", "3 colheres de sopa de grão-de-bico (60g)",
                "1 fatia de pão integral (30g)"],
             "kcal": 350, "proteina_g": 14, "carboidrato_g": 52, "gordura_g": 8},
        ],
        "lanche": [
            {"nome": "Fruta com castanhas", "ingredientes": [
                "1 fruta média (100g)", "1 punhado de castanhas (20g)"],
             "kcal": 220, "proteina_g": 5, "carboidrato_g": 22, "gordura_g": 13},
            {"nome": "Iogurte vegetal com granola", "ingredientes": [
                "1 pote de iogurte de soja (170g)", "2 colheres de sopa de granola (20g)"],
             "kcal": 230, "proteina_g": 8, "carboidrato_g": 32, "gordura_g": 7},
        ],
    },
    "low_carb": {
        "cafe": [
            {"nome": "Ovos com abacate", "ingredientes": [
                "3 ovos mexidos (150g)", "meio abacate (100g)",
                "1 xícara de café sem açúcar"],
             "kcal": 420, "proteina_g": 22, "carboidrato_g": 10, "gordura_g": 34},
            {"nome": "Omelete com queijo e bacon", "ingredientes": [
                "3 ovos (150g)", "1 fatia de queijo (20g)", "2 fatias de bacon (20g)"],
             "kcal": 400, "proteina_g": 26, "carboidrato_g": 3, "gordura_g": 32},
        ],
        "almoco": [
            {"nome": "Frango grelhado com legumes e salada", "ingredientes": [
                "180g de peito de frango grelhado", "legumes salteados à vontade",
                "salada de folhas com azeite à vontade"],
             "kcal": 460, "proteina_g": 48, "carboidrato_g": 15, "gordura_g": 22},
            {"nome": "Carne com purê de couve-flor", "ingredientes": [
                "180g de carne magra grelhada", "150g de purê de couve-flor",
                "salada verde à vontade", "1 colher de chá de azeite"],
             "kcal": 480, "proteina_g": 45, "carboidrato_g": 12, "gordura_g": 24},
        ],
        "jantar": [
            {"nome": "Salmão grelhado com aspargos", "ingredientes": [
                "150g de salmão grelhado", "aspargos ou brócolis no vapor à vontade",
                "1 colher de chá de azeite"],
             "kcal": 420, "proteina_g": 38, "carboidrato_g": 8, "gordura_g": 26},
            {"nome": "Omelete de queijo e espinafre", "ingredientes": [
                "3 ovos (150g)", "1 fatia de queijo (20g)", "espinafre refogado à vontade"],
             "kcal": 360, "proteina_g": 26, "carboidrato_g": 5, "gordura_g": 26},
        ],
        "lanche": [
            {"nome": "Castanhas e queijo", "ingredientes": [
                "1 punhado de castanhas ou nozes (25g)", "1 fatia de queijo (20g)"],
             "kcal": 240, "proteina_g": 10, "carboidrato_g": 5, "gordura_g": 20},
            {"nome": "Ovo cozido com abacate", "ingredientes": [
                "2 ovos cozidos (100g)", "1/4 de abacate (50g)"],
             "kcal": 230, "proteina_g": 14, "carboidrato_g": 4, "gordura_g": 18},
        ],
    },
}

DIET_MEAL_PERIOD = {"cafe": "manha", "almoco": "tarde", "lanche": "tarde", "jantar": "noite"}
DIET_MEAL_LABEL = {"cafe": "Café da manhã", "almoco": "Almoço", "lanche": "Lanche", "jantar": "Jantar"}
DIET_TYPE_LABELS = {
    "padrao": "Padrão (sem restrição)", "vegetariano": "Vegetariana",
    "vegano": "Vegana", "low_carb": "Low carb",
}

# ---------------------------------------------------------------------------
# TREINOS — exercícios com séries/repetições ou duração, por objetivo de saúde.
# Uso ilustrativo/geral (não substitui orientação de educador físico).
# ---------------------------------------------------------------------------
WORKOUT_PLANS = {
    "paideia_basico": [
        {"nome": "Mobilidade e postura A", "exercicios": [
            "Rotação de tronco - 2x15", "Gato-camelo (mobilidade de coluna) - 2x12",
            "Alongamento de posterior de coxa - 3x30s", "Caminhada leve - 15 minutos"]},
        {"nome": "Mobilidade e postura B", "exercicios": [
            "Alongamento de peitoral em porta/parede - 3x30s", "Rotação de ombros - 2x15",
            "Prancha isométrica - 3x20s", "Caminhada leve - 20 minutos"]},
    ],
    "paideia_moderado": [
        {"nome": "Condicionamento geral A", "exercicios": [
            "Agachamento livre - 3x15", "Flexão de braço (joelho se necessário) - 3x10",
            "Prancha - 3x30s", "Polichinelos - 3x30s"]},
        {"nome": "Condicionamento geral B", "exercicios": [
            "Afundo alternado - 3x12 por perna", "Remada com elástico ou toalha - 3x12",
            "Abdominal remador - 3x15", "Corrida estacionária - 3x30s"]},
    ],
    "paideia_avancado": [
        {"nome": "Hipertrofia - Superiores", "exercicios": [
            "Supino reto (barra ou halteres) - 4x10", "Puxada frente ou remada curvada - 4x10",
            "Desenvolvimento de ombro - 3x12", "Rosca direta - 3x12", "Tríceps corda ou testa - 3x12"]},
        {"nome": "Hipertrofia - Inferiores", "exercicios": [
            "Agachamento livre ou leg press - 4x10", "Levantamento terra romeno - 4x10",
            "Cadeira extensora - 3x12", "Mesa flexora - 3x12", "Panturrilha em pé - 4x15"]},
    ],
    "perder_peso": [
        {"nome": "Treino metabólico A", "exercicios": [
            "Agachamento livre - 4x15", "Polichinelos - 4x40s", "Prancha - 3x30s",
            "Burpee (adaptar intensidade) - 3x10"]},
        {"nome": "Cardio + força B", "exercicios": [
            "Caminhada rápida ou trote - 20 minutos", "Afundo alternado - 3x12 por perna",
            "Remada com elástico - 3x15", "Abdominal - 3x15"]},
    ],
    "ganhar_massa": [
        {"nome": "Hipertrofia - Push (peito/ombro/tríceps)", "exercicios": [
            "Supino reto - 4x8-10", "Desenvolvimento de ombro - 4x10",
            "Elevação lateral - 3x12", "Tríceps corda - 3x12"]},
        {"nome": "Hipertrofia - Pull (costas/bíceps)", "exercicios": [
            "Puxada frente - 4x8-10", "Remada curvada - 4x10",
            "Rosca direta - 3x12", "Rosca alternada - 3x12"]},
        {"nome": "Hipertrofia - Pernas", "exercicios": [
            "Agachamento livre - 4x8-10", "Levantamento terra romeno - 4x10",
            "Cadeira extensora - 3x12", "Panturrilha em pé - 4x15"]},
    ],
    "maratona": [
        {"nome": "Corrida de ritmo leve", "exercicios": [
            "Aquecimento caminhando - 5 minutos", "Corrida em ritmo confortável - 30-40 minutos",
            "Alongamento de posterior e panturrilha - 5 minutos"]},
        {"nome": "Treino intervalado", "exercicios": [
            "Aquecimento - 5 minutos", "6-8x tiros de 400m em ritmo forte com 2 min de trote leve entre eles",
            "Desaquecimento caminhando - 5 minutos"]},
        {"nome": "Fortalecimento para corredores", "exercicios": [
            "Agachamento livre - 3x15", "Afundo alternado - 3x12 por perna",
            "Prancha - 3x30s", "Panturrilha em pé - 3x20"]},
    ],
    "manter_forma": [
        {"nome": "Circuito geral leve", "exercicios": [
            "Agachamento livre - 3x12", "Flexão de braço (adaptar) - 3x10",
            "Prancha - 3x25s", "Caminhada - 20 minutos"]},
    ],
}


def diet_menu_options():
    """Agrupa TODAS as refeições curadas (das 4 dietas) por tipo de refeição
    (café/almoço/lanche/jantar), cada uma já com ingredientes e macros reais.
    Usado para a UI de substituição no plano completo: como as 4 dietas cobrem
    o mesmo tipo de refeição com combinações diferentes (proteína animal,
    vegetariana, vegana, low carb), a lista dá 6-8 alternativas reais e
    consistentes por refeição — sem precisar inventar dados novos de
    ingrediente-a-ingrediente."""
    result = {}
    for meal_type in ("cafe", "almoco", "lanche", "jantar"):
        options = []
        seen = set()
        for diet_key, diet_label in DIET_TYPE_LABELS.items():
            for meal in DIET_MEALS.get(diet_key, {}).get(meal_type, []):
                if meal["nome"] in seen:
                    continue
                seen.add(meal["nome"])
                options.append({
                    "dieta": diet_key, "dieta_label": diet_label,
                    "nome": meal["nome"], "ingredientes": meal["ingredientes"],
                    "kcal": meal["kcal"], "proteina_g": meal["proteina_g"],
                    "carboidrato_g": meal["carboidrato_g"], "gordura_g": meal["gordura_g"],
                })
        result[meal_type] = options
    return result


def diet_missions_for(diet_type):
    """Gera as missões de dieta do dia (café/almoço/lanche/jantar) para um tipo de
    dieta, ciclando pelas opções disponíveis. Cada missão carrega o detalhe completo
    (ingredientes + macros) para exibição no plano completo."""
    import itertools as _it
    meals = DIET_MEALS.get(diet_type, DIET_MEALS["padrao"])
    result = []
    for meal_type in ("cafe", "almoco", "lanche", "jantar"):
        options = meals.get(meal_type, [])
        if not options:
            continue
        result.append({"meal_type": meal_type, "options_cycle": _it.cycle(options)})
    return result


def format_meal_detail(meal):
    linhas = ["Ingredientes:"]
    for ing in meal["ingredientes"]:
        linhas.append(f"  • {ing}")
    linhas.append(
        f"Aprox. {meal['kcal']} kcal · {meal['proteina_g']}g proteína · "
        f"{meal['carboidrato_g']}g carboidrato · {meal['gordura_g']}g gordura"
    )
    return "\n".join(linhas)


def format_workout_detail(workout):
    linhas = [f"Treino: {workout['nome']}"]
    for ex in workout["exercicios"]:
        linhas.append(f"  • {ex}")
    return "\n".join(linhas)
