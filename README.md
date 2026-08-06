# Life Builder Assistant — Protótipo v0.7

Um "RPG da vida real" com conta de usuário, focado em 4 áreas — **Profissional,
Estudos, Saúde e Espiritualidade** — onde você pode escolher **mais de um
objetivo por área**, detalhar objetivos específicos (qual concurso, qual idioma...),
resolver simulados dentro do próprio app, e receber recomendações com links reais
de compra/vídeo/evento. Ao fim de cada ciclo de 14 dias, o app pergunta como você
*sente* que foi seu progresso e recalibra o ciclo seguinte. Opcionalmente, a IA
gera uma nota de estratégia por área a cada ciclo, já considerando o histórico
(adesão, autoavaliação, desempenho em quiz) do ciclo anterior.

## Como rodar

### Opção 1 — Docker (recomendado para self-host)

```bash
cd life_builder
cp .env.example .env
# edite o .env: defina pelo menos SECRET_KEY (o arquivo explica como gerar uma).
# OPENROUTER_API_KEY / GROQ_API_KEY são opcionais — sem elas o app funciona
# normalmente, só sem a nota de estratégia por IA e sem quiz personalizado por tema.
docker compose up -d --build
```

Acesse **http://localhost:5000**. O banco é PostgreSQL (configure `DB_HOST`,
`DB_USER`, `DB_PASSWORD`, `DB_NAME` no `.env` -- funciona com Aiven ou
qualquer Postgres acessível). Para atualizar depois de um `git pull`:
`docker compose up -d --build`.

### Opção 2 — Python direto

```bash
cd life_builder
pip install -r requirements.txt
python app.py
```

Acesse **http://localhost:5000**. O banco é PostgreSQL -- configure as
variáveis de conexão no `.env` (veja `.env.example`). As tabelas são
criadas/migradas automaticamente na primeira conexão.

## O que mudou nesta versão

### 1. Escopo reduzido a 4 áreas
O produto passou de 10 áreas rasas para 4 áreas com identidade mais clara:
**Profissional, Estudos, Saúde e Espiritualidade**. Finanças, Mente & Foco,
Relacionamentos, Arte, Social e Sono & Descanso foram **removidas do código**
(não só escondidas) — `data.py` não tem mais entradas de `AREAS`, `GOALS`,
`MISSION_TEMPLATES` nem `RECOMMENDATIONS` para elas. O registro diário de sono
(feito pelo assistente flutuante, tabela `sleep_logs`) é independente dessa
área e continua funcionando normalmente.

**Limitação conhecida**: contas de teste antigas que tenham salvo uma dessas
áreas removidas não são migradas — `area_label`/`goal_label` caem num
fallback (mostram a chave crua) em vez de quebrar a página, mas o ideal é
recriar a build nessas contas.

### 2. IA estruturada por área, sem aumentar o custo por chamada
A nota de estratégia (`ai.generate_strategy_note`) continua sendo **1
chamada por ciclo de 14 dias por conta** — não por missão, não por dia — pra
manter o teste grátis (`FREE_TRIAL_AI_TOKENS`, ver `ai_billing.py`) viável.
O que mudou é o conteúdo dessa chamada: agora ela recebe o histórico do ciclo
anterior (adesão às missões, autoavaliação do checkpoint vs. progresso
medido, desempenho em quiz — tudo já salvo em `missions`/`checkpoint_history`,
montado por `app._build_ai_history`) e devolve uma nota curta **por área
ativa** em JSON, em vez de um parágrafo único e genérico. O dashboard mostra
essa nota junto de cada área.

O quiz por IA foi estendido para `estudos/idioma` reaproveitando 100% da infraestrutura
existente (`ai.generate_quiz_questions`, cache em `ai_quiz_cache`) — só
adicionou `action: "quiz:5"` numa mission template. Saúde e Espiritualidade
não ganharam quiz de propósito: não fazem sentido em múltipla escolha, e
forçar isso seria custo de IA sem valor real.

### 3. Ponto de extensão para gerador de cursos (não integrado ainda)
`learner_context.py` é um módulo novo, não chamado por nenhuma rota hoje. Ele
monta o contexto de aprendizado de um objetivo específico do usuário (nível,
detalhe digitado, progresso, desempenho em quiz) no formato que uma futura
integração com um gerador de cursos personalizados (outro projeto do mesmo
autor) precisaria. Fica pronto pra ser exposto por uma rota autenticada
quando o contrato entre os dois projetos existir — até lá, zero custo, zero
tabela nova.

## Onboarding (recapitulando)

1. Áreas — multi-seleção entre as 4 áreas + "Outro" (diálogo modal).
2. Objetivos — multi-seleção por área (checkboxes) + "Outro" (diálogo modal)
   + campo de detalhe para objetivos personalizáveis.
   - Se nenhuma área de saúde for escolhida, o passo Paideia aparece antes.
3. Medidas, pesos e dieta — inalterado.
4. Panorama — mostra uma linha por objetivo (não por área), incluindo o
   detalhe personalizado quando houver.

## Arquitetura (arquivos)

- `data.py` — `AREAS`/`GOALS`/`MISSION_TEMPLATES`/`RECOMMENDATIONS` cobrem só
  as 4 áreas ativas; `GOALS_NEEDING_DETAIL` (quais objetivos pedem detalhe);
  `QUIZ_BANK` (banco de questões-modelo, fallback estático quando a IA não
  está disponível).
- `engine.py` — `generate_plan` recebe `goal_details` e substitui `{detalhe}`
  nas descrições; `pick_quiz_questions`/`grade_quiz` para o simulado. Sem
  chamada de IA — tudo determinístico.
- `ai.py` — `build_profile_summary` (agora aceita `history` opcional) e
  `generate_strategy_note` (agora devolve um dict `{area: nota}`, pedindo
  saída em JSON) para a nota de estratégia; `generate_quiz_questions` para o
  quiz. Ambos percorrem `providers()` -- ver "Provedores de IA" abaixo.
- `app.py` — `_build_ai_history` monta o histórico do ciclo anterior por
  área; `_update_ai_strategy` chama a IA e salva o dict em
  `extra_info["ai_strategy"]`. Rotas de quiz: `/quiz/<mission_id>` (GET
  mostra as questões, POST corrige e registra).
- `learner_context.py` — ponto de extensão (não roteado) para a futura
  integração com o gerador de cursos.
- `templates/quiz.html`, `templates/quiz_result.html` — telas do simulado.

## Provedores de IA

Quiz por tema, prova semanal e nota de estratégia usam uma **lista de
provedores tentados em ordem** (`ai.providers()`), todos falando o mesmo
dialeto (Chat Completions no formato OpenAI). Trocar de provedor é só variável
de ambiente — não há código específico de fornecedor.

1. **OpenRouter** (`OPENROUTER_API_KEY`) — primário. Uma chave dá acesso a
   praticamente qualquer modelo, e ele **não loga prompt por padrão**, o que
   importa aqui: o resumo enviado inclui dado pessoal (lesão, religião,
   anotações livres). Sem markup na inferência; a taxa é na compra de crédito.
2. **Groq** (`GROQ_API_KEY`) — fallback gratuito.

Sem nenhum configurado, o app roda normal: missões, pontos e progressão são
determinísticos e nunca dependem de IA.

**Por que o encadeamento existe**: falha de provedor aconteceu de verdade em
produção. Uma conta ficou sem saldo (HTTP 402) e, como o app engole erro de IA
em silêncio de propósito, todo quiz passou a cair no banco estático genérico —
o usuário digitava "TI da Caixa" e recebia questões aleatórias de português,
sem nenhum aviso. Hoje há três defesas: o encadeamento, o aviso visível na tela
do quiz quando as questões são genéricas, e o painel `/admin`, que testa ao
vivo se cada provedor responde.

**Nota histórica**: a DeepSeek foi removida — ela não tem cota gratuita
recorrente (só crédito pré-pago), e o crédito promocional acabou.

## Limitações conhecidas / próximos passos sugeridos

- Quiz por IA: existe para `(profissional, concurso)` e `(estudos, idioma)`.
  Questões do `QUIZ_BANK` estático (fallback sem IA) só cobrem concurso, com
  questões-modelo (não verbatim de edital real) — a fonte de cada questão
  deixa isso explícito na tela.
- Contas antigas com áreas removidas (Finanças/Mental/Relacionamentos/Arte/
  Social/Sono) não são migradas automaticamente — ver nota acima.
- Recomendações: a maioria usa links de busca (reais, mas não fixados num
  produto específico) em vez de preço/link exato verificado a mão.
- Nota de estratégia por IA: o histórico usado hoje é só do ciclo
  imediatamente anterior (não a série completa) — olhar mais ciclos pra trás
  é o próximo passo natural se isso se mostrar valioso na prática.
- `learner_context.py` ainda não está exposto por nenhuma rota — falta
  definir o contrato com o outro projeto (gerador de cursos) antes disso.
