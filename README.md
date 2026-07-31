# Life Builder Assistant — Protótipo v0.6

Um "RPG da vida real" com conta de usuário: você pode escolher **mais de um
objetivo por área**, detalhar objetivos específicos (qual concurso, qual idioma,
qual instrumento...), resolver simulados dentro do próprio app, e receber
recomendações com links reais de compra/vídeo/evento. Ao fim de cada ciclo de 14
dias, o app pergunta como você *sente* que foi seu progresso e recalibra o ciclo
seguinte. Opcionalmente, a Groq gera uma estratégia personalizada por IA.

## Como rodar

### Opção 1 — Docker (recomendado para self-host)

```bash
cd life_builder
cp .env.example .env
# edite o .env: defina pelo menos SECRET_KEY (o arquivo explica como gerar uma).
# GROQ_API_KEY e DEEPSEEK_API_KEY são opcionais — sem elas o app funciona
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

### 1. Seleção múltipla de objetivos (Passo II)
Cada área agora usa checkboxes em vez de um único radio — dá para escolher, por
exemplo, "Passar em concurso" e "Conseguir uma promoção" dentro de Profissional
ao mesmo tempo. Cada combinação (área, objetivo) ganha sua própria barra de
progresso, seu conjunto de missões e suas próprias recomendações.

### 2. Objetivos personalizáveis com detalhe específico
Objetivos como concurso público, vaga de emprego, idioma, bolsa, intercâmbio,
maratona e as aptidões de Arte agora perguntam um detalhe extra assim que
selecionados (ex.: "Qual concurso público?"). Esse texto substitui `{detalhe}`
nas descrições de missão que o usam — por exemplo, "Resolver 15 questões de
matéria objetiva do Concurso INSS 2026" em vez de um genérico "do edital".

### 3. Simulado in-app (quiz)
Missões de resolução de questões de concurso (`action: "quiz"`) agora têm um
botão "Resolver questões →" que abre um simulado dentro do próprio app: 5
questões de múltipla escolha, correção imediata com gabarito e a fonte de cada
questão, e o resultado (% de acerto) já é registrado automaticamente como a
conclusão da missão.

**Nota de honestidade sobre o conteúdo do quiz**: as questões em
`data.QUIZ_BANK` são questões-modelo que eu escrevi no estilo típico de
bancas de concurso (Português, Direito Constitucional, Raciocínio Lógico,
Administrativo, Informática) — não são questões verbatim de um edital real
específico. Não haveria como verificar/atribuir com precisão um "Edital X, Ano
Y" real para o concurso que cada usuário for digitar sem uma pesquisa dedicada
por caso, então preferi ser honesto sobre a origem em vez de inventar uma
citação falsa. A arquitetura (`engine.pick_quiz_questions`/`grade_quiz`,
`data.QUIZ_BANK`) já está pronta para receber bancos de questões reais e
verificadas no futuro, inclusive por outra área/objetivo além de concurso.

### 4. Recomendações com links reais
Livros, vídeos e eventos agora têm links funcionais:
- Livros: para a maioria, um link de busca real na Amazon Brasil (sempre
  funcional, mostra o preço atual na própria loja). Para 3 livros específicos
  (verificados via busca), um link direto ao produto certo.
- Vídeos: link de busca real no YouTube para a maioria; para "Hábitos
  Atômicos" (mental/habito), um vídeo específico verificado com thumbnail real.
- Eventos: link de busca real no Sympla.

Assumo aqui uma limitação parecida com a do quiz: verificar manualmente preço e
link exato de ~40 livros/vídeos individuais está fora do escopo razoável deste
protótipo — por isso a maioria usa links de busca (100% reais e funcionais, só
não fixados em um produto/vídeo específico) em vez de dados fabricados. Também
corrigi uma atribuição errada que eu tinha inventado antes ("Como se preparar
para concursos, de Carlos Henrique Vieira" não existe — o livro real é de
Rogério Neiva).

### 5. Bustos removidos
Você pediu um modelo 3D de verdade; se não desse, para tirar. Não tenho como
gerar ou obter malhas 3D reais dos bustos de Aristóteles/Da Vinci/etc. neste
ambiente (sem acesso a repositórios de modelos 3D, e eu não fabricaria um
"modelo 3D genérico" fingindo ser uma pessoa específica). Como a versão em foto
2D girando também não atendeu, removi a funcionalidade por completo em vez de
manter uma versão que você já disse não gostar.

## Onboarding (recapitulando, com as mudanças desta versão)

1. Áreas — multi-seleção + "Outro" (diálogo modal).
2. Objetivos — agora multi-seleção por área (checkboxes) + "Outro" (diálogo
   modal) + campo de detalhe para objetivos personalizáveis.
   - Se nenhuma área de saúde for escolhida, o passo Paideia aparece antes.
3. Medidas, pesos e dieta — inalterado.
4. Panorama — agora mostra uma linha por objetivo (não por área), incluindo o
   detalhe personalizado quando houver.

## Arquitetura (arquivos)

- `data.py` — inclui `GOALS_NEEDING_DETAIL` (quais objetivos pedem detalhe),
  `QUIZ_BANK` (banco de questões-modelo), e os helpers de link real
  (`amazon_link`, `youtube_search_link`, `youtube_video`, `sympla_search_link`)
  usados para montar `RECOMMENDATIONS`.
- `engine.py` — `generate_plan` agora recebe `goal_details` e substitui
  `{detalhe}` nas descrições; `pick_quiz_questions`/`grade_quiz` para o
  simulado.
- `app.py` — `user["goals"]` agora é `area -> [lista de objetivos]` (era um
  único objetivo por área); `flat_goal_pairs()` achata isso onde precisa de
  pares `(area, objetivo)`. Rotas novas: `/quiz/<mission_id>` (GET mostra as
  questões, POST corrige e registra).
- `templates/quiz.html`, `templates/quiz_result.html` — telas do simulado.

## Limitações conhecidas / próximos passos sugeridos

- Quiz: só existe para `(profissional, concurso)` por enquanto, com questões-
  modelo (não verbatim de edital real) — ver nota de honestidade acima.
  Expandir para outros objetivos (idioma, vestibular) é o próximo passo
  natural, assim como trocar por um banco de questões real/licenciado se
  disponível.
- Recomendações: a maioria usa links de busca (reais, mas não fixados num
  produto específico) em vez de preço/link exato verificado a mão — ver nota
  acima.
- Sem bustos: removidos por não haver como entregar 3D real (ver nota acima).
- Demais limitações já documentadas nas versões anteriores (correspondência
  treino↔missão por palavra-chave, variedade do pool de missões secundárias)
  continuam valendo.
