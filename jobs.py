# -*- coding: utf-8 -*-
"""
Life Builder Assistant -- fila de background jobs, guardada no proprio
Postgres (sem Redis/RabbitMQ/infraestrutura nova).

Por que Postgres em vez de Redis+RQ: o unico motivo pra ter uma fila hoje e
tirar as chamadas de IA (Groq/DeepSeek, timeout de 12-25s) do caminho da
requisicao HTTP -- nao ha volume que justifique contratar/pagar/operar um
Redis novo so pra isso. `SELECT ... FOR UPDATE SKIP LOCKED` da o mesmo
"claim atomico de 1 job por worker, sem duplicar trabalho" que uma fila de
verdade daria, usando a mesma conexao que o resto do app ja usa.

Este modulo e so a mecanica da fila (enqueue/claim/mark_done/mark_failed) --
nao sabe o que cada tipo de job faz. Os handlers (o que roda quando um job de
tipo "ai_strategy" e claimado, por exemplo) vivem em app.py, junto da logica
de negocio que ja existia antes da fila."""
import json
from datetime import datetime, timedelta

# se um job falhar, tenta de novo ate esse numero de vezes antes de desistir
# (status vira 'failed' definitivamente). Cada retry espera um pouco mais
# (backoff simples), pra nao martelar um provedor de IA fora do ar.
DEFAULT_MAX_ATTEMPTS = 3
RETRY_BACKOFF_SECONDS = 30


def enqueue(db, job_type, payload, run_after=None, max_attempts=DEFAULT_MAX_ATTEMPTS, dedupe_key=None):
    """`dedupe_key`: se ja existir um job pendente/rodando com essa mesma
    chave, devolve o id dele em vez de criar outro -- usado pra evitar
    disparar N chamadas de IA se o usuario recarregar a pagina de espera
    varias vezes enquanto o mesmo job ainda nao terminou (ver quiz_generate
    em app.py)."""
    if dedupe_key:
        existing = db.execute(
            "SELECT id FROM jobs WHERE dedupe_key=? AND status IN ('pending','running') "
            "ORDER BY id DESC LIMIT 1",
            (dedupe_key,),
        ).fetchone()
        if existing:
            db.commit()
            return existing["id"]

    now = datetime.now().isoformat()
    cur = db.execute(
        "INSERT INTO jobs (job_type, payload, status, max_attempts, run_after, dedupe_key, created_at, updated_at) "
        "VALUES (?, ?, 'pending', ?, ?, ?, ?, ?) RETURNING id",
        (job_type, json.dumps(payload), max_attempts, run_after, dedupe_key, now, now),
    )
    job_id = cur.fetchone()["id"]
    db.commit()
    return job_id


def claim_next_job(db):
    """Pega (e marca como 'running') o proximo job pendente e pronto pra
    rodar, pulando qualquer job que outro worker ja esteja processando nesse
    exato momento (SKIP LOCKED). Retorna None se nao houver nenhum -- quem
    chama deve dar um commit/rollback e esperar um pouco antes de tentar de
    novo."""
    now = datetime.now().isoformat()
    row = db.execute(
        "SELECT * FROM jobs WHERE status='pending' AND (run_after IS NULL OR run_after <= ?) "
        "ORDER BY id LIMIT 1 FOR UPDATE SKIP LOCKED",
        (now,),
    ).fetchone()
    if row is None:
        db.commit()
        return None
    db.execute(
        "UPDATE jobs SET status='running', attempts=attempts+1, updated_at=? WHERE id=?",
        (now, row["id"]),
    )
    db.commit()
    row = dict(row)
    row["status"] = "running"
    row["attempts"] = (row["attempts"] or 0) + 1
    return row


def mark_done(db, job_id, result=None):
    db.execute(
        "UPDATE jobs SET status='done', result=?, updated_at=? WHERE id=?",
        (json.dumps(result) if result is not None else None, datetime.now().isoformat(), job_id),
    )
    db.commit()


def mark_failed(db, job, error):
    """Se ainda sobrarem tentativas, volta pra 'pending' com um atraso
    (backoff) pra tentar de novo; senao, marca 'failed' definitivamente. Job
    de IA falho e sempre um "ok, sem essa nota/quiz desta vez" no resto do
    app -- nunca trava nada esperando."""
    attempts = job.get("attempts") or 1
    max_attempts = job.get("max_attempts") or DEFAULT_MAX_ATTEMPTS
    now = datetime.now()
    if attempts >= max_attempts:
        db.execute(
            "UPDATE jobs SET status='failed', error=?, updated_at=? WHERE id=?",
            (str(error)[:2000], now.isoformat(), job["id"]),
        )
    else:
        run_after = (now + timedelta(seconds=RETRY_BACKOFF_SECONDS * attempts)).isoformat()
        db.execute(
            "UPDATE jobs SET status='pending', error=?, run_after=?, updated_at=? WHERE id=?",
            (str(error)[:2000], run_after, now.isoformat(), job["id"]),
        )
    db.commit()


def get_status(db, job_id):
    row = db.execute("SELECT status, result FROM jobs WHERE id=?", (job_id,)).fetchone()
    if row is None:
        return None
    return {
        "status": row["status"],
        "result": json.loads(row["result"]) if row["result"] else None,
    }
