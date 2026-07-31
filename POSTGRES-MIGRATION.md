# Migração SQLite → PostgreSQL

## Por quê

O plano gratuito do Render tem filesystem efêmero: o SQLite local seria
resetado toda vez que o serviço "dormisse" por inatividade (15 min) e
alguém acessasse de novo. Precisava de um banco externo persistente.

**Por que Postgres e não MySQL** (como no KriptaHaus): a Aiven só permite
**um serviço gratuito por tipo**, por conta — e o MySQL grátis já estava
ocupado pelo KriptaHaus. Postgres é um tipo de serviço separado, então
conta como um "slot" gratuito à parte na mesma conta.

## O que mudou no código

- **Camada de conexão** (`app.py`, topo do arquivo): trocado `sqlite3` por
  `psycopg2`, com uma classe `DBWrapper` que imita a API de conveniência do
  `sqlite3.Connection` (`.execute()` devolvendo um cursor com
  `.fetchone()`/`.fetchall()`, `.executescript()`). As dezenas de rotas que
  já usavam `db.execute(...)` no resto do arquivo não precisaram ser
  reescritas — só a conexão mudou.
- **Schema** (`init_db()`): tipos ajustados pro Postgres —
  - `INT AUTO_INCREMENT PRIMARY KEY` → `SERIAL PRIMARY KEY`
  - `DOUBLE` → `DOUBLE PRECISION` (Postgres não tem o tipo `DOUBLE` sozinho)
  - IDs continuam `VARCHAR(36)` (UUIDs) — funciona igual no Postgres
- **`_ensure_columns`** (auto-migração leve): usava `SHOW COLUMNS FROM`
  (MySQL) — trocado por uma consulta em `information_schema.columns`
  (padrão SQL, funciona em Postgres). A chave do nome da coluna também
  mudou (`Field` → `column_name`).
- **3 queries de upsert, reescritas para a sintaxe do Postgres:**
  - `INSERT IGNORE INTO ...` (MySQL) → `INSERT INTO ... ON CONFLICT (...)
    DO NOTHING` (2 ocorrências, em `goal_progress`)
  - `REPLACE INTO ...` (MySQL) → `INSERT INTO ... ON CONFLICT (mission_id)
    DO UPDATE SET ...` (em `ai_quiz_cache`)
  - `... ON DUPLICATE KEY UPDATE horas=VALUES(horas)` (MySQL) → `...
    ON CONFLICT (user_id, date) DO UPDATE SET horas=EXCLUDED.horas`
    (em `sleep_logs`) — **essa é quase idêntica à sintaxe SQLite original**
    (`ON CONFLICT(...) DO UPDATE SET x=excluded.x`), porque o SQLite copiou
    esse padrão de upsert do próprio Postgres. Foi a única das três
    conversões que "voltou" a ficar parecida com o código de antes.

## Variáveis de ambiente

`DB_HOST`, `DB_PORT` (padrão `5432`, não `3306`), `DB_USER`, `DB_PASSWORD`,
`DB_NAME`, `DB_SSL`. Ver `.env.example`.

## O que eu não consegui testar

Sem acesso a rede neste ambiente para instalar `psycopg2` ou conectar a um
Postgres de verdade — a migração foi feita por revisão manual + varredura
sistemática por qualquer sintaxe específica de MySQL/SQLite restante no
arquivo inteiro (nenhuma sobrou, confirmado por grep). Sintaxe Python
validada (`ast.parse`, sem erros), mas **não o comportamento em runtime**.
Teste localmente contra o Aiven antes de considerar pronto para produção.
