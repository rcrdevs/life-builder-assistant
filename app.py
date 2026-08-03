# -*- coding: utf-8 -*-
"""
Life Builder Assistant -- prototipo web (Flask + PostgreSQL).
Rode com: python app.py   e acesse http://localhost:5000
"""
import json
import os
import re
import unicodedata
import uuid
from datetime import date, datetime, timedelta
from functools import wraps

from dotenv import load_dotenv
load_dotenv()  # sem efeito se .env nao existir (ex: Docker, onde as variaveis ja vem do ambiente)

import psycopg2
import psycopg2.extras
from flask import Flask, g, redirect, render_template, request, session, url_for, jsonify
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.security import generate_password_hash, check_password_hash

from data import (
    AREAS, GOALS, NIVEL_LABELS, RECOMMENDATIONS,
    AREA_ICONS, ROTINA_LABEL, PERIOD_LABELS, PAIDEIA_INTRO, PAIDEIA_LEVELS,
    DIET_TYPE_LABELS, GOALS_NEEDING_DETAIL, generic_recommendation, diet_menu_options,
)
from engine import (
    generate_plan, PLAN_DAYS, compute_mission_points,
    blend_checkpoint_progress, bump_nivel, PROGRESS_POINT_SCALE, DEFAULT_PESO,
    AREA_TIER_WEIGHTS, AREA_TIER_LABELS,
    TOTAL_DAY_MINUTES, quiz_available, pick_quiz_questions, grade_quiz,
)
import ai

try:
    from google.oauth2 import id_token as google_id_token
    from google.auth.transport import requests as google_auth_requests
    GOOGLE_AUTH_LIB_AVAILABLE = True
except ImportError:
    # a lib "google-auth" e opcional -- sem ela (ou sem GOOGLE_CLIENT_ID
    # configurado), o app roda 100% normal, so sem o botao "Entrar com
    # Google" (ver GOOGLE_CLIENT_ID logo abaixo e .env.example).
    GOOGLE_AUTH_LIB_AVAILABLE = False

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "life-builder-prototype-secret-key")  # troque em producao (ver .env.example)
# Render (como Heroku/etc.) termina o HTTPS num proxy e repassa a requisicao
# por HTTP internamente -- sem isso, o Flask as vezes acha que a conexao
# nao e segura e o cookie de sessao se comporta de forma inconsistente.
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Esse app pode ser aberto direto OU embutido num iframe de outro dominio
# (e o caso da "Oficina", que embute varios projetos numa pagina so). Cookie
# de sessao com SameSite=Lax (o padrao do Flask) e bloqueado pelo navegador
# dentro de iframe cross-origin -- sem isso, o modo convidado cria a conta
# mas o cookie nunca volta pro servidor, e a pagina fica recarregando em
# loop. SameSite=None exige Secure=True (cookie so trafega em HTTPS), entao
# so ligamos isso em producao (rodando em HTTP local, Secure quebraria o
# cookie). "RENDER" e uma variavel que o proprio Render sempre define
# sozinho (nao depende de configurar nada no dashboard).
_IS_PROD = os.environ.get("RENDER") == "true" or os.environ.get("FLASK_DEBUG", "1") != "1"
app.config["SESSION_COOKIE_SAMESITE"] = "None" if _IS_PROD else "Lax"
app.config["SESSION_COOKIE_SECURE"] = _IS_PROD

GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "").strip()
GOOGLE_LOGIN_ENABLED = bool(GOOGLE_CLIENT_ID) and GOOGLE_AUTH_LIB_AVAILABLE


@app.context_processor
def inject_session_flags():
    return {
        "is_guest": bool(session.get("is_guest")),
        "google_client_id": GOOGLE_CLIENT_ID if GOOGLE_LOGIN_ENABLED else "",
        "show_assistant": bool(session.get("user_id")),
    }

DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_PORT = int(os.environ.get("DB_PORT", 5432))
DB_USER = os.environ.get("DB_USER", "postgres")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "")
DB_NAME = os.environ.get("DB_NAME", "life_builder")
DB_SSL = os.environ.get("DB_SSL", "1") == "1"  # a Aiven (e a maioria dos free tiers) exige SSL

ALL_AREA_LABELS = {**AREAS, "rotina": ROTINA_LABEL}
VITALITY_SCALE = 0.8

TIER_LABELS = {"primaria": "Primária", "secundaria": "Secundária", "rotina": "Rotina", "dieta": "Dieta"}


# ---------------------------------------------------------------------------
# Banco de dados
# ---------------------------------------------------------------------------
class DBWrapper:
    """Imita a API de conveniencia do sqlite3.Connection (.execute() devolvendo
    um cursor com .fetchone()/.fetchall(), .executescript()) por cima do
    psycopg2 -- assim as dezenas de rotas que ja usam `db.execute(...)` no
    resto do arquivo nao precisam ser reescritas uma a uma. So a camada de
    conexao muda; o resto do codigo continua igual."""

    def __init__(self, conn):
        self._conn = conn

    def execute(self, query, params=()):
        cur = self._conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(query.replace("?", "%s"), params)
        return cur

    def executescript(self, script):
        cur = self._conn.cursor()
        for statement in script.split(";"):
            statement = statement.strip()
            if statement:
                cur.execute(statement)
        self._conn.commit()

    def commit(self):
        self._conn.commit()

    def close(self):
        self._conn.close()


def _connect():
    conn = psycopg2.connect(
        host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASSWORD, dbname=DB_NAME,
        sslmode="require" if DB_SSL else "prefer",
    )
    return DBWrapper(conn)


def get_db():
    if "db" not in g:
        g.db = _connect()
    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def _ensure_columns(db, table, coldefs):
    """Auto-migracao leve: adiciona colunas que faltam em uma tabela existente.
    Evita o app quebrar com coluna ausente quando o schema evolui entre versoes.
    Usa "IF NOT EXISTS" porque o gunicorn sobe varios workers (ver Dockerfile)
    e cada um roda essa migracao na inicializacao -- sem isso, dois workers
    tentando adicionar a mesma coluna ao mesmo tempo derrubavam um deles."""
    for col, decl in coldefs.items():
        db.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {col} {decl}")


def init_db():
    db = _connect()
    db.executescript("""
    CREATE TABLE IF NOT EXISTS accounts (
        id VARCHAR(36) PRIMARY KEY,
        email VARCHAR(255) UNIQUE,
        password_hash VARCHAR(255),
        google_sub VARCHAR(64),
        is_guest INT DEFAULT 0,
        created_at VARCHAR(32)
    );
    CREATE TABLE IF NOT EXISTS users (
        id VARCHAR(36) PRIMARY KEY,
        account_id VARCHAR(36),
        build_name VARCHAR(255) DEFAULT 'Minha build',
        email VARCHAR(255),
        password_hash VARCHAR(255),
        nome VARCHAR(255),
        areas TEXT,
        custom_area_labels TEXT,
        goals TEXT,
        custom_goal_labels TEXT,
        goal_details TEXT,
        niveis TEXT,
        pesos TEXT,
        basic_info TEXT,
        extra_info TEXT,
        onboarding_complete INT DEFAULT 0,
        current_cycle INT DEFAULT 1,
        cycle_start_date VARCHAR(32),
        last_rollover_date VARCHAR(32),
        vitality_points_accum DOUBLE PRECISION DEFAULT 0,
        vitality_pct DOUBLE PRECISION DEFAULT 0,
        created_at VARCHAR(32)
    );
    CREATE TABLE IF NOT EXISTS goal_progress (
        id SERIAL PRIMARY KEY,
        user_id VARCHAR(36),
        area VARCHAR(64),
        goal VARCHAR(64),
        progress_pct DOUBLE PRECISION DEFAULT 0,
        UNIQUE(user_id, area, goal)
    );
    CREATE TABLE IF NOT EXISTS missions (
        id SERIAL PRIMARY KEY,
        user_id VARCHAR(36),
        area VARCHAR(64),
        goal VARCHAR(64),
        description TEXT,
        base_points DOUBLE PRECISION,
        date VARCHAR(10),
        period VARCHAR(32),
        cycle INT,
        tier VARCHAR(32),
        duration_min DOUBLE PRECISION,
        detail TEXT,
        action VARCHAR(32),
        completion_pct DOUBLE PRECISION,
        points_earned DOUBLE PRECISION,
        logged_at VARCHAR(32)
    );
    CREATE TABLE IF NOT EXISTS sleep_logs (
        id SERIAL PRIMARY KEY,
        user_id VARCHAR(36),
        date VARCHAR(10),
        horas DOUBLE PRECISION,
        UNIQUE(user_id, date)
    );
    CREATE TABLE IF NOT EXISTS checkpoint_history (
        id SERIAL PRIMARY KEY,
        user_id VARCHAR(36),
        cycle INT,
        area VARCHAR(64),
        goal VARCHAR(64),
        self_rating INT,
        measured_progress DOUBLE PRECISION,
        new_progress DOUBLE PRECISION,
        created_at VARCHAR(32)
    );
    CREATE TABLE IF NOT EXISTS ai_quiz_cache (
        mission_id INT PRIMARY KEY,
        topic TEXT,
        source VARCHAR(32),
        questions TEXT,
        created_at VARCHAR(32)
    );
    """)
    # auto-migracao: cobre bancos criados por versoes anteriores do app
    _ensure_columns(db, "users", {
        "pesos": "TEXT",
        "goal_details": "TEXT",
        "vitality_points_accum": "DOUBLE PRECISION DEFAULT 0",
        "vitality_pct": "DOUBLE PRECISION DEFAULT 0",
        "account_id": "VARCHAR(36)",
        "build_name": "VARCHAR(255) DEFAULT 'Minha build'",
        "last_active_at": "VARCHAR(32)",
    })
    _ensure_columns(db, "missions", {
        "tier": "VARCHAR(32)", "duration_min": "DOUBLE PRECISION", "detail": "TEXT", "action": "VARCHAR(32)",
    })
    _ensure_columns(db, "accounts", {
        "google_sub": "VARCHAR(64)",
        "is_guest": "INT DEFAULT 0",
    })

    # migracao unica: bancos de versoes anteriores tinham 1 build = 1 conta de
    # login (email/senha direto na tabela users). Agora contas ficam em
    # `accounts` e podem ter varias builds em `users`. Para cada build antiga
    # que ainda nao tem account_id, cria a conta correspondente e faz o link.
    legacy = db.execute(
        "SELECT id, email, password_hash FROM users WHERE account_id IS NULL AND email IS NOT NULL"
    ).fetchall()
    for row in legacy:
        acc_id = str(uuid.uuid4())
        db.execute(
            "INSERT INTO accounts (id, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
            (acc_id, row["email"], row["password_hash"], date.today().isoformat()),
        )
        db.execute(
            "UPDATE users SET account_id=?, build_name='Minha build' WHERE id=?",
            (acc_id, row["id"]),
        )
    db.commit()
    db.close()


# ---------------------------------------------------------------------------
# Autenticacao
# ---------------------------------------------------------------------------
def create_guest_account():
    db = get_db()
    account_id = str(uuid.uuid4())
    db.execute(
        "INSERT INTO accounts (id, email, password_hash, is_guest, created_at) VALUES (?, NULL, NULL, 1, ?)",
        (account_id, date.today().isoformat()),
    )
    db.commit()
    return account_id


def guest_allowed(view):
    """Como login_required, so que em vez de mandar pro /login quando nao ha
    sessao, cria uma conta-convidado transparente na hora -- assim a pessoa
    consegue usar o app inteiro (onboarding + dashboard) sem criar conta.
    So quando ela realmente registra (ou entra com Google) essa conta
    convidado vira uma conta de verdade, ver register()/auth_google()."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("account_id"):
            session["account_id"] = create_guest_account()
            session["is_guest"] = True
        return view(*args, **kwargs)
    return wrapped


def real_account_required(view):
    """Para telas que exigem conta de verdade (gerenciar varias builds nao
    faz sentido pra uma sessao de teste que pode sumir a qualquer momento)."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("account_id") or session.get("is_guest"):
            return redirect(url_for("register"))
        return view(*args, **kwargs)
    return wrapped


def _attach_session_to_account(account_id):
    """Chamado depois de um login bem-sucedido (senha ou Google) numa conta
    de verdade. Se a sessao atual era de um convidado que ja tinha gerado
    uma build (onboarding_complete), essa build "muda de dono" pra conta que
    acabou de logar em vez de ser perdida; senao, a conta-convidado vazia e
    descartada."""
    db = get_db()
    guest_account_id = session.get("account_id") if session.get("is_guest") else None
    guest_build_id = session.get("user_id") if guest_account_id else None
    claimed = False

    if guest_account_id and guest_account_id != account_id:
        build = None
        if guest_build_id:
            build = db.execute(
                "SELECT * FROM users WHERE id=? AND account_id=?", (guest_build_id, guest_account_id)
            ).fetchone()
        if build and build["onboarding_complete"]:
            db.execute(
                "UPDATE users SET account_id=?, build_name=?, last_active_at=? WHERE id=?",
                (account_id, "Build (modo teste)", datetime.now().isoformat(), guest_build_id),
            )
            claimed = True
        elif build:
            for table in ("missions", "goal_progress", "sleep_logs", "checkpoint_history"):
                db.execute(f"DELETE FROM {table} WHERE user_id=?", (guest_build_id,))
            db.execute("DELETE FROM users WHERE id=?", (guest_build_id,))
        db.execute("DELETE FROM accounts WHERE id=?", (guest_account_id,))

    db.commit()
    session.clear()
    session["account_id"] = account_id
    if claimed:
        session["user_id"] = guest_build_id
    return claimed


def list_builds(account_id):
    db = get_db()
    return db.execute(
        "SELECT * FROM users WHERE account_id=? ORDER BY (last_active_at IS NULL), last_active_at DESC, created_at DESC",
        (account_id,),
    ).fetchall()


def ensure_active_build():
    """Garante que session['user_id'] aponte para uma build valida e pertencente
    a conta logada. Se nao houver build ativa (ou ela nao pertencer mais a esta
    conta), tenta escolher a mais recente; se a conta nao tiver nenhuma build
    ainda, cria a primeira automaticamente (fluxo mais suave no primeiro acesso)."""
    account_id = session.get("account_id")
    if not account_id:
        return None
    db = get_db()
    active_id = session.get("user_id")
    if active_id:
        row = db.execute(
            "SELECT id FROM users WHERE id=? AND account_id=?", (active_id, account_id)
        ).fetchone()
        if row:
            return active_id
    builds = list_builds(account_id)
    if builds:
        session["user_id"] = builds[0]["id"]
        return builds[0]["id"]
    new_id = create_build(account_id, build_name="Minha build")
    session["user_id"] = new_id
    return new_id


def create_build(account_id, build_name="Nova build", nome=""):
    db = get_db()
    build_id = str(uuid.uuid4())
    db.execute(
        "INSERT INTO users (id, account_id, build_name, nome, created_at, last_active_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (build_id, account_id, build_name, nome, date.today().isoformat(), datetime.now().isoformat()),
    )
    db.commit()
    return build_id


def get_user():
    ensure_active_build()
    if not session.get("user_id"):
        return None
    db = get_db()
    row = db.execute("SELECT * FROM users WHERE id = ?", (session["user_id"],)).fetchone()
    if row is None:
        return None
    user = dict(row)
    for field in ("areas", "goals", "niveis", "pesos", "basic_info", "extra_info",
                  "custom_area_labels", "custom_goal_labels", "goal_details"):
        user[field] = json.loads(user[field] or ("[]" if field == "areas" else "{}"))
    return user


def save_user_fields(user_id, **fields):
    json_fields = {"areas", "goals", "niveis", "pesos", "basic_info", "extra_info",
                   "custom_area_labels", "custom_goal_labels", "goal_details"}
    db = get_db()
    sets, values = [], []
    for key, value in fields.items():
        if key in json_fields:
            value = json.dumps(value)
        sets.append(f"{key}=?")
        values.append(value)
    values.append(user_id)
    db.execute(f"UPDATE users SET {', '.join(sets)} WHERE id=?", values)
    db.commit()


def slugify(text):
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-zA-Z0-9]+", "_", text).strip("_").lower()
    return text[:30] or "personalizado"


def area_label(user, area):
    return ALL_AREA_LABELS.get(area) or user["custom_area_labels"].get(area) or area


def goal_label(user, area, goal):
    if goal == "dieta":
        return "Dieta"
    if area in GOALS and goal in GOALS[area]:
        return GOALS[area][goal]
    custom = user["custom_goal_labels"].get(f"{area}:{goal}")
    if custom:
        return custom
    return user["custom_area_labels"].get(area) or goal


def area_goals_label(user, area):
    """Rótulos de TODOS os objetivos escolhidos numa área, unidos por ' + '."""
    goals = user["goals"].get(area) or []
    return " + ".join(goal_label(user, area, g) for g in goals) or "(sem objetivo definido)"


def flat_goal_pairs(user):
    """[(area, goal), ...] -- achata o dict area -> [goals] em uma lista de pares."""
    pairs = []
    for area, goals in user["goals"].items():
        for g in (goals or []):
            pairs.append((area, g))
    return pairs


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    nome = request.form.get("nome", "").strip()
    if not email or not password:
        return render_template("register.html", erro="Preencha e-mail e senha.")

    db = get_db()
    existing = db.execute("SELECT id FROM accounts WHERE email=?", (email,)).fetchone()
    if existing:
        return render_template("register.html", erro="Esse e-mail já tem uma conta. Tente entrar.")

    if session.get("is_guest") and session.get("account_id"):
        # upgrade: a conta-convidado atual vira a conta de verdade, no mesmo
        # id -- a build (e todo o progresso) que ja existir continua igual,
        # nao precisa de nenhuma migracao de dados.
        account_id = session["account_id"]
        db.execute(
            "UPDATE accounts SET email=?, password_hash=?, is_guest=0 WHERE id=?",
            (email, generate_password_hash(password), account_id),
        )
        db.commit()
        session["is_guest"] = False
        return redirect(url_for("index"))

    account_id = str(uuid.uuid4())
    db.execute(
        "INSERT INTO accounts (id, email, password_hash, is_guest, created_at) VALUES (?, ?, ?, 0, ?)",
        (account_id, email, generate_password_hash(password), date.today().isoformat()),
    )
    db.commit()
    session.clear()
    session["account_id"] = account_id
    build_id = create_build(account_id, build_name="Minha build", nome=nome)
    session["user_id"] = build_id
    return redirect(url_for("index"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return redirect(url_for("index"))
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    db = get_db()
    row = db.execute("SELECT * FROM accounts WHERE email=? AND is_guest=0", (email,)).fetchone()
    if row is None or not row["password_hash"] or not check_password_hash(row["password_hash"], password):
        return render_template("welcome.html", erro="E-mail ou senha incorretos.")
    _attach_session_to_account(row["id"])
    return redirect(url_for("index"))


@app.route("/auth/google", methods=["POST"])
def auth_google():
    if not GOOGLE_LOGIN_ENABLED:
        return jsonify({"error": "login com Google não está configurado neste servidor"}), 400

    payload = request.get_json(silent=True) or {}
    credential = payload.get("credential")
    if not credential:
        return jsonify({"error": "credencial ausente"}), 400

    try:
        info = google_id_token.verify_oauth2_token(
            credential, google_auth_requests.Request(), GOOGLE_CLIENT_ID
        )
    except Exception:
        return jsonify({"error": "não foi possível validar o login do Google"}), 400

    email = (info.get("email") or "").strip().lower()
    if not email:
        return jsonify({"error": "essa conta do Google não tem e-mail disponível"}), 400
    if info.get("email_verified") is False:
        return jsonify({"error": "e-mail do Google ainda não verificado"}), 400
    google_sub = info.get("sub")
    nome = info.get("given_name") or info.get("name") or ""

    db = get_db()
    row = db.execute("SELECT * FROM accounts WHERE email=? AND is_guest=0", (email,)).fetchone()

    if row:
        if not row["google_sub"]:
            db.execute("UPDATE accounts SET google_sub=? WHERE id=?", (google_sub, row["id"]))
            db.commit()
        _attach_session_to_account(row["id"])
        return jsonify({"ok": True, "redirect": url_for("index")})

    if session.get("is_guest") and session.get("account_id"):
        account_id = session["account_id"]
        db.execute(
            "UPDATE accounts SET email=?, google_sub=?, is_guest=0 WHERE id=?",
            (email, google_sub, account_id),
        )
        db.commit()
        session["is_guest"] = False
        return jsonify({"ok": True, "redirect": url_for("index")})

    account_id = str(uuid.uuid4())
    db.execute(
        "INSERT INTO accounts (id, email, password_hash, google_sub, is_guest, created_at) "
        "VALUES (?, ?, NULL, ?, 0, ?)",
        (account_id, email, google_sub, date.today().isoformat()),
    )
    db.commit()
    session.clear()
    session["account_id"] = account_id
    build_id = create_build(account_id, build_name="Minha build", nome=nome)
    session["user_id"] = build_id
    return jsonify({"ok": True, "redirect": url_for("index")})


@app.route("/logout")
def logout():
    if session.get("is_guest") and session.get("account_id"):
        # sessao de teste que nunca virou conta -- nao faz sentido deixar
        # esse lixo acumulando no banco, entao apaga tudo ao sair.
        db = get_db()
        account_id = session["account_id"]
        build_id = session.get("user_id")
        if build_id:
            for table in ("missions", "goal_progress", "sleep_logs", "checkpoint_history"):
                db.execute(f"DELETE FROM {table} WHERE user_id=?", (build_id,))
            db.execute("DELETE FROM users WHERE id=?", (build_id,))
        db.execute("DELETE FROM accounts WHERE id=?", (account_id,))
        db.commit()
    session.clear()
    return redirect(url_for("index"))


# ---------------------------------------------------------------------------
# Minhas builds — uma conta pode ter varias builds (personagens/jogadas
# independentes). A build ativa fica em session["user_id"]; excluir uma build
# apaga todos os dados ligados a ela (missoes, progresso, sono, checkpoints).
# ---------------------------------------------------------------------------
@app.route("/builds")
@real_account_required
def builds_page():
    account_id = session["account_id"]
    ensure_active_build()
    rows = list_builds(account_id)
    builds = []
    for r in rows:
        b = dict(r)
        b["areas"] = json.loads(b["areas"] or "[]")
        builds.append(b)
    return render_template("builds.html", builds=builds, active_id=session.get("user_id"),
                            area_labels=ALL_AREA_LABELS)


@app.route("/builds/new", methods=["POST"])
@real_account_required
def builds_new():
    account_id = session["account_id"]
    nome = request.form.get("nome", "").strip()
    build_name = request.form.get("build_name", "").strip() or f"Build {len(list_builds(account_id)) + 1}"
    build_id = create_build(account_id, build_name=build_name, nome=nome)
    session["user_id"] = build_id
    return redirect(url_for("index"))


@app.route("/builds/<build_id>/select", methods=["POST"])
@real_account_required
def builds_select(build_id):
    db = get_db()
    row = db.execute(
        "SELECT id FROM users WHERE id=? AND account_id=?", (build_id, session["account_id"])
    ).fetchone()
    if row:
        session["user_id"] = build_id
        db.execute("UPDATE users SET last_active_at=? WHERE id=?", (datetime.now().isoformat(), build_id))
        db.commit()
    return redirect(url_for("index"))


@app.route("/builds/<build_id>/delete", methods=["POST"])
@real_account_required
def builds_delete(build_id):
    db = get_db()
    row = db.execute(
        "SELECT id FROM users WHERE id=? AND account_id=?", (build_id, session["account_id"])
    ).fetchone()
    if row:
        for table in ("missions", "goal_progress", "sleep_logs", "checkpoint_history"):
            db.execute(f"DELETE FROM {table} WHERE user_id=?", (build_id,))
        db.execute("DELETE FROM users WHERE id=?", (build_id,))
        db.commit()
        if session.get("user_id") == build_id:
            session.pop("user_id", None)
    return redirect(url_for("builds_page"))


# ---------------------------------------------------------------------------
# Roteamento do onboarding (com navegacao para tras) -- 4 passos numerados
# ---------------------------------------------------------------------------
def next_onboarding_step(user):
    if not user["areas"]:
        return url_for("step_areas")
    needs_paideia = "saude" not in user["areas"] and not user["extra_info"].get("paideia_nivel")
    if needs_paideia:
        return url_for("step_paideia")
    pending_goals = [a for a in user["areas"]
                     if a not in user["custom_area_labels"] and not user["goals"].get(a)]
    if pending_goals:
        return url_for("step_goals")
    if not user["basic_info"].get("tempo_livre_min"):
        return url_for("step_info")
    return url_for("step_panorama")


@app.route("/")
def index():
    user = get_user()
    if user is None:
        return render_template("welcome.html")
    if user["onboarding_complete"]:
        return redirect(url_for("dashboard"))
    return redirect(next_onboarding_step(user))


@app.route("/guest/start")
def guest_start():
    if not session.get("account_id"):
        session["account_id"] = create_guest_account()
        session["is_guest"] = True
    return redirect(url_for("index"))


# --- Passo I: areas -----------------------------------------------------
@app.route("/onboarding/areas", methods=["GET", "POST"])
@guest_allowed
def step_areas():
    user = get_user()
    if request.method == "GET":
        return render_template("step1_areas.html", areas=AREAS, area_icons=AREA_ICONS, user=user, current_step=1)

    nome = request.form.get("nome", "").strip() or user["nome"] or ""
    areas = request.form.getlist("areas")
    custom_area_labels = dict(user["custom_area_labels"])
    goals = dict(user["goals"])
    custom_goal_labels = dict(user["custom_goal_labels"])

    # prioridade escolhida no card de cada area (principal/secundaria/plano
    # de fundo) -- guardada antes de resolver a chave final do "outro", que
    # so existe depois do slugify logo abaixo.
    raw_tiers = {a: request.form.get(f"tier_{a}", "secundario") for a in areas}
    outro_tier = request.form.get("tier_outro", "secundario")

    outro_text = request.form.get("area_outro_text", "").strip()
    if "outro" in areas or outro_text:
        areas = [a for a in areas if a != "outro"]
        raw_tiers.pop("outro", None)
        if outro_text:
            key = "custom_" + slugify(outro_text)
            base_key, i = key, 2
            while key in areas or key in custom_area_labels:
                key = f"{base_key}_{i}"
                i += 1
            areas.append(key)
            custom_area_labels[key] = outro_text
            goals[key] = ["principal"]
            custom_goal_labels[f"{key}:principal"] = outro_text
            raw_tiers[key] = outro_tier

    if not areas:
        return render_template("step1_areas.html", areas=AREAS, area_icons=AREA_ICONS, user=user, current_step=1,
                                erro="Escolha ao menos uma area (ou descreva a sua em 'Outro') para continuar.")

    # so pode existir 1 area "principal" -- se por algum motivo (form
    # manipulado, corrida entre abas) vier mais de uma, mantem a primeira e
    # rebaixa as demais pra secundaria, pra nao quebrar o calculo de peso.
    area_tiers = dict(user["extra_info"].get("area_tiers", {}))
    seen_principal = False
    for area in areas:
        tier = raw_tiers.get(area) or "secundario"
        if tier not in AREA_TIER_WEIGHTS:
            tier = "secundario"
        if tier == "principal":
            if seen_principal:
                tier = "secundario"
            else:
                seen_principal = True
        area_tiers[area] = tier
    area_tiers = {a: t for a, t in area_tiers.items() if a in areas}

    pesos = dict(user["pesos"])
    for area in areas:
        pesos[area] = AREA_TIER_WEIGHTS[area_tiers[area]]

    extra_info = dict(user["extra_info"])
    extra_info["area_tiers"] = area_tiers

    save_user_fields(user["id"], nome=nome, areas=areas, custom_area_labels=custom_area_labels,
                      goals=goals, custom_goal_labels=custom_goal_labels, pesos=pesos, extra_info=extra_info)
    user = get_user()
    return redirect(next_onboarding_step(user))


# --- Passo condicional: Paideia (se nenhum objetivo fisico foi escolhido) ---
@app.route("/onboarding/paideia", methods=["GET", "POST"])
@guest_allowed
def step_paideia():
    user = get_user()
    if "saude" in user["areas"]:
        return redirect(url_for("step_goals"))

    if request.method == "GET":
        return render_template("step_paideia.html", intro=PAIDEIA_INTRO, levels=PAIDEIA_LEVELS, user=user)

    nivel_fisico = request.form.get("nivel_fisico", "paideia_basico")

    areas = list(user["areas"])
    if "saude" not in areas:
        areas.append("saude")
    goals = dict(user["goals"])
    goals["saude"] = [nivel_fisico]

    extra_info = dict(user["extra_info"])
    extra_info["paideia_nivel"] = nivel_fisico
    area_tiers = dict(extra_info.get("area_tiers", {}))
    area_tiers.setdefault("saude", "secundario")
    extra_info["area_tiers"] = area_tiers

    pesos = dict(user["pesos"])
    pesos.setdefault("saude", AREA_TIER_WEIGHTS[area_tiers["saude"]])

    save_user_fields(user["id"], areas=areas, goals=goals, extra_info=extra_info, pesos=pesos)
    user = get_user()
    return redirect(next_onboarding_step(user))


# --- Passo II: objetivos por area (multi-selecao) -------------------------
@app.route("/onboarding/goals", methods=["GET", "POST"])
@guest_allowed
def step_goals():
    user = get_user()
    if not user["areas"]:
        return redirect(url_for("step_areas"))

    pending_areas = [a for a in user["areas"]
                     if a not in user["custom_area_labels"] and not user["goals"].get(a)]

    if request.method == "GET":
        goal_options = {a: GOALS.get(a, {}) for a in pending_areas}
        resolved = {a: area_goals_label(user, a) for a in user["areas"]
                    if user["goals"].get(a) and a not in pending_areas}
        return render_template("step2_goals.html", area_labels=AREAS, goal_options=goal_options,
                                resolved=resolved, user=user, current_step=2,
                                needs_detail=GOALS_NEEDING_DETAIL)

    goals = dict(user["goals"])
    custom_goal_labels = dict(user["custom_goal_labels"])
    goal_details = dict(user["goal_details"])

    for area in pending_areas:
        chosen = request.form.getlist(f"goal_{area}")
        if not chosen:
            continue
        final_goals = []
        for goal_key in chosen:
            if goal_key == "outro":
                texto = request.form.get(f"goal_{area}_outro_text", "").strip()
                if texto:
                    final_goals.append("outro")
                    custom_goal_labels[f"{area}:outro"] = texto
            else:
                final_goals.append(goal_key)
                if (area, goal_key) in GOALS_NEEDING_DETAIL:
                    detalhe = request.form.get(f"detail_{area}_{goal_key}", "").strip()
                    if detalhe:
                        goal_details[f"{area}:{goal_key}"] = detalhe
        if final_goals:
            goals[area] = final_goals

    save_user_fields(user["id"], goals=goals, custom_goal_labels=custom_goal_labels, goal_details=goal_details)
    user = get_user()
    return redirect(next_onboarding_step(user))


# --- Passo III: informacoes basicas, pesos por area e dieta --------------
@app.route("/onboarding/info", methods=["GET", "POST"])
@guest_allowed
def step_info():
    user = get_user()
    pending_goals = [a for a in user["areas"]
                     if a not in user["custom_area_labels"] and not user["goals"].get(a)]
    if pending_goals:
        return redirect(url_for("step_goals"))

    if request.method == "GET":
        return render_template(
            "step4_info.html", user=user, area_labels=AREAS, nivel_labels=NIVEL_LABELS,
            diet_type_labels=DIET_TYPE_LABELS, default_peso=DEFAULT_PESO,
            area_tier_labels=AREA_TIER_LABELS,
            total_day_minutes=TOTAL_DAY_MINUTES, current_step=3,
        )

    basic_info = dict(user["basic_info"])
    basic_info["cidade"] = request.form.get("cidade", "").strip()
    basic_info["tempo_livre_min"] = int(request.form.get("tempo_livre_min", 60))
    if "saude" in user["areas"]:
        dieta = request.form.get("dieta", "nao")
        if dieta == "sim":
            peso = request.form.get("peso_kg")
            altura = request.form.get("altura_cm")
            basic_info["peso_kg"] = float(peso) if peso else None
            basic_info["altura_cm"] = float(altura) if altura else None
        else:
            # sem sugestao de dieta, peso/altura nao sao pedidos -- limpa
            # qualquer valor antigo pra nao usar dado desatualizado depois.
            basic_info["peso_kg"] = None
            basic_info["altura_cm"] = None

        extra_info = dict(user["extra_info"])
        extra_info["dieta"] = dieta
        extra_info["dieta_tipo"] = request.form.get("dieta_tipo", "padrao") if dieta == "sim" else None
        save_user_fields(user["id"], extra_info=extra_info)

    niveis = dict(user["niveis"])
    pesos = dict(user["pesos"])
    for area in user["areas"]:
        niveis[area] = request.form.get(f"nivel_{area}", niveis.get(area, "iniciante"))
        pesos.setdefault(area, DEFAULT_PESO)  # fallback p/ areas sem tier definido (ex: paideia)

    save_user_fields(user["id"], basic_info=basic_info, niveis=niveis, pesos=pesos)
    user = get_user()
    return redirect(next_onboarding_step(user))


# --- Passo IV: panorama / revisao final -----------------------------------
@app.route("/onboarding/panorama", methods=["GET", "POST"])
@guest_allowed
def step_panorama():
    user = get_user()
    if not user["basic_info"].get("tempo_livre_min"):
        return redirect(url_for("step_info"))

    if request.method == "GET":
        panorama_areas = []
        area_tiers = user["extra_info"].get("area_tiers", {})
        for area in user["areas"]:
            goals_here = user["goals"].get(area) or []
            tier_label = AREA_TIER_LABELS.get(area_tiers.get(area), "Secundária")
            if not goals_here:
                panorama_areas.append({
                    "area": area, "area_label": area_label(user, area),
                    "icon": AREA_ICONS.get(area, "*" if area in user["custom_area_labels"] else "o"),
                    "goal_label": "(sem objetivo definido)",
                    "nivel": NIVEL_LABELS.get(user["niveis"].get(area), "-"),
                    "peso": user["pesos"].get(area, DEFAULT_PESO),
                    "tier_label": tier_label,
                })
            for goal in goals_here:
                detalhe = user["goal_details"].get(f"{area}:{goal}")
                label = goal_label(user, area, goal)
                if detalhe:
                    label += f" — {detalhe}"
                panorama_areas.append({
                    "area": area, "area_label": area_label(user, area),
                    "icon": AREA_ICONS.get(area, "*" if area in user["custom_area_labels"] else "o"),
                    "goal_label": label,
                    "nivel": NIVEL_LABELS.get(user["niveis"].get(area), "-"),
                    "peso": user["pesos"].get(area, DEFAULT_PESO),
                    "tier_label": tier_label,
                })
        return render_template("step5_panorama.html", user=user, panorama_areas=panorama_areas,
                                area_labels=AREAS, diet_type_labels=DIET_TYPE_LABELS, current_step=4)

    extra_info = dict(user["extra_info"])
    extra_info["panorama_notes"] = request.form.get("notas", "").strip()
    save_user_fields(user["id"], extra_info=extra_info)

    if not user["onboarding_complete"]:
        _finalize_build(user)

    return redirect(url_for("dashboard"))


def _diet_type_for(user):
    if user["extra_info"].get("dieta") == "sim":
        return user["extra_info"].get("dieta_tipo") or "padrao"
    return None


def _insert_missions(db, user_id, plan):
    for m in plan:
        db.execute(
            "INSERT INTO missions (user_id, area, goal, description, base_points, date, period, cycle, "
            "tier, duration_min, detail, action) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (user_id, m["area"], m["goal"], m["description"], m["base_points"], m["date"], m["period"],
             m["cycle"], m["tier"], m["duration_min"], m.get("detail"), m.get("action")),
        )


def _update_ai_strategy(user):
    """Gera (se a Groq estiver configurada) uma nota curta de estrategia
    personalizada e salva em extra_info. Falha silenciosamente -- a build
    funciona 100% sem isso.

    Contas-convidado (modo teste) NUNCA disparam chamada de IA: a chave da
    Groq/DeepSeek e unica e compartilhada por todo o app (ver ai.py), entao
    isso e o que evita que trafego anonimo de teste consuma a cota gratuita
    de quem tem conta de verdade. Ver mensagem equivalente no dashboard."""
    if session.get("is_guest"):
        return
    if not ai.ai_available():
        return
    summary = ai.build_profile_summary(user, area_label, area_goals_label)
    note = ai.generate_strategy_note(summary)
    if note:
        db = get_db()
        extra_info = dict(user["extra_info"])
        extra_info["ai_strategy"] = note
        db.execute("UPDATE users SET extra_info=? WHERE id=?", (json.dumps(extra_info), user["id"]))
        db.commit()


def _finalize_build(user):
    db = get_db()
    area_goal_pairs = flat_goal_pairs(user)
    today = date.today()

    plan = generate_plan(
        area_goal_pairs, user["niveis"], user["pesos"], user["basic_info"]["tempo_livre_min"],
        cycle=1, custom_labels=user["custom_goal_labels"], diet_type=_diet_type_for(user),
        goal_details=user["goal_details"], dias=PLAN_DAYS, start_date=today,
    )
    _insert_missions(db, user["id"], plan)

    for area, gk in area_goal_pairs:
        db.execute(
            "INSERT INTO goal_progress (user_id, area, goal, progress_pct) VALUES (?, ?, ?, 0) "
            "ON CONFLICT (user_id, area, goal) DO NOTHING",
            (user["id"], area, gk),
        )

    db.execute(
        "UPDATE users SET onboarding_complete=1, current_cycle=1, cycle_start_date=?, last_rollover_date=? WHERE id=?",
        (today.isoformat(), today.isoformat(), user["id"]),
    )
    db.commit()
    _update_ai_strategy(get_user() or user)


def ensure_goal_progress_rows(user):
    """Garante que toda meta atual do usuario tenha uma linha em goal_progress --
    cobre o caso de o usuario editar a build (adicionar area/objetivo) depois que
    o onboarding ja foi finalizado, quando _finalize_build nao roda de novo."""
    db = get_db()
    for area, gk in flat_goal_pairs(user):
        db.execute(
            "INSERT INTO goal_progress (user_id, area, goal, progress_pct) VALUES (?, ?, ?, 0) "
            "ON CONFLICT (user_id, area, goal) DO NOTHING",
            (user["id"], area, gk),
        )
    db.commit()


# ---------------------------------------------------------------------------
# Rollover diario: fecha dias passados e aplica pontos a barra de progresso
# ---------------------------------------------------------------------------
def rollover_pending_days(user):
    db = get_db()
    cycle_start = date.fromisoformat(user["cycle_start_date"])
    cycle_end = cycle_start + timedelta(days=PLAN_DAYS - 1)
    last = date.fromisoformat(user["last_rollover_date"] or user["cycle_start_date"])
    today = date.today()

    day = last + timedelta(days=1)
    last_processed = last
    while day < today and day <= cycle_end:
        rows = db.execute(
            "SELECT * FROM missions WHERE user_id=? AND date=?", (user["id"], day.isoformat())
        ).fetchall()

        totals = {}
        rotina_total = 0.0
        for m in rows:
            pct = m["completion_pct"] if m["completion_pct"] is not None else 0
            points = compute_mission_points(m["base_points"], pct)
            if m["completion_pct"] is None:
                db.execute(
                    "UPDATE missions SET completion_pct=0, points_earned=?, logged_at=? WHERE id=?",
                    (points, day.isoformat(), m["id"]),
                )
            if m["area"] == "rotina":
                rotina_total += points
            elif m["goal"] != "dieta":
                key = (m["area"], m["goal"])
                totals[key] = totals.get(key, 0) + points

        for (area, gk), pts in totals.items():
            delta = pts * PROGRESS_POINT_SCALE
            db.execute(
                "UPDATE goal_progress SET progress_pct = MAX(0, MIN(100, progress_pct + ?)) "
                "WHERE user_id=? AND area=? AND goal=?",
                (delta, user["id"], area, gk),
            )

        if rotina_total:
            db.execute(
                "UPDATE users SET vitality_points_accum = vitality_points_accum + ? WHERE id=?",
                (rotina_total, user["id"]),
            )

        last_processed = day
        day += timedelta(days=1)

    if last_processed != last:
        vit_row = db.execute("SELECT vitality_points_accum FROM users WHERE id=?", (user["id"],)).fetchone()
        vitality_pct = max(0, min(100, vit_row["vitality_points_accum"] * VITALITY_SCALE))
        db.execute(
            "UPDATE users SET last_rollover_date=?, vitality_pct=? WHERE id=?",
            (last_processed.isoformat(), vitality_pct, user["id"]),
        )
        db.commit()


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------
@app.route("/dashboard")
@guest_allowed
def dashboard():
    user = get_user()
    if not user["onboarding_complete"]:
        return redirect(next_onboarding_step(user))

    ensure_goal_progress_rows(user)
    rollover_pending_days(user)
    user = get_user()

    db = get_db()
    cycle_start = date.fromisoformat(user["cycle_start_date"])
    cycle_end = cycle_start + timedelta(days=PLAN_DAYS - 1)
    today = date.today()

    if today > cycle_end:
        has_next_cycle = db.execute(
            "SELECT COUNT(*) c FROM missions WHERE user_id=? AND date=?", (user["id"], today.isoformat())
        ).fetchone()["c"]
        if not has_next_cycle:
            return redirect(url_for("checkpoint"))

    today_iso = today.isoformat()
    missions_today = db.execute(
        "SELECT * FROM missions WHERE user_id=? AND date=? ORDER BY id", (user["id"], today_iso)
    ).fetchall()

    total_missions = db.execute(
        "SELECT COUNT(*) c FROM missions WHERE user_id=? AND cycle=?", (user["id"], user["current_cycle"])
    ).fetchone()["c"]
    logged_missions = db.execute(
        "SELECT COUNT(*) c FROM missions WHERE user_id=? AND cycle=? AND completion_pct IS NOT NULL",
        (user["id"], user["current_cycle"]),
    ).fetchone()["c"]

    goal_progress_rows = db.execute(
        "SELECT * FROM goal_progress WHERE user_id=? ORDER BY area", (user["id"],)
    ).fetchall()
    current_pairs = set(flat_goal_pairs(user))
    goal_progress_rows = [r for r in goal_progress_rows if (r["area"], r["goal"]) in current_pairs]

    recs = []
    for area, gk in flat_goal_pairs(user):
        rec = RECOMMENDATIONS.get((area, gk))
        if not rec:
            label = user["custom_goal_labels"].get(f"{area}:{gk}") or user["custom_area_labels"].get(area) or gk
            rec = generic_recommendation(label)
        recs.append({
            "area_label": area_label(user, area),
            "goal_label": goal_label(user, area, gk),
            **rec,
        })

    sleep_today = db.execute(
        "SELECT * FROM sleep_logs WHERE user_id=? AND date=?", (user["id"], today_iso)
    ).fetchone()
    show_sleep_prompt = sleep_today is None

    logged_today = [m for m in missions_today if m["completion_pct"] is not None]
    all_logged_today = len(missions_today) > 0 and len(logged_today) == len(missions_today)

    fast = False
    times = [datetime.fromisoformat(m["logged_at"]) for m in logged_today if m["logged_at"] and "T" in m["logged_at"]]
    if len(times) >= 3:
        span = (max(times) - min(times)).total_seconds()
        if span < 5 * 60:
            fast = True
    show_rest_message = all_logged_today or fast

    avg_goal_progress = (
        sum(r["progress_pct"] for r in goal_progress_rows) / len(goal_progress_rows)
        if goal_progress_rows else 0
    )
    overall_progress = 0.8 * avg_goal_progress + 0.2 * (user["vitality_pct"] or 0)

    # agrupa as missoes de hoje por categoria (area) para exibicao em secoes
    missions_by_area = {}
    for m in missions_today:
        missions_by_area.setdefault(m["area"], []).append(m)

    return render_template(
        "dashboard.html",
        user=user,
        missions_today=missions_today,
        missions_by_area=missions_by_area,
        total_missions=total_missions,
        logged_missions=logged_missions,
        goal_progress_rows=goal_progress_rows,
        vitality_pct=round(user["vitality_pct"] or 0, 1),
        overall_progress=overall_progress,
        recs=recs,
        area_labels=ALL_AREA_LABELS,
        goal_labels=GOALS,
        period_labels=PERIOD_LABELS,
        tier_labels=TIER_LABELS,
        plan_days=PLAN_DAYS,
        cycle_end=cycle_end.isoformat(),
        show_sleep_prompt=show_sleep_prompt,
        show_rest_message=show_rest_message,
        area_label_fn=area_label,
        goal_label_fn=goal_label,
        ai_strategy=user["extra_info"].get("ai_strategy"),
        ai_configured=ai.ai_available(),
    )


@app.route("/plano")
@guest_allowed
def plano():
    user = get_user()
    if not user["onboarding_complete"]:
        return redirect(next_onboarding_step(user))

    db = get_db()
    rows = db.execute(
        "SELECT * FROM missions WHERE user_id=? AND cycle=? ORDER BY date, id",
        (user["id"], user["current_cycle"]),
    ).fetchall()

    days = {}
    for row in rows:
        days.setdefault(row["date"], []).append(row)

    total = len(rows)
    logged = sum(1 for r in rows if r["completion_pct"] is not None)
    progress_pct = round((logged / total) * 100) if total else 0
    today = date.today().isoformat()

    diet_type = user["extra_info"].get("dieta_tipo") if user["extra_info"].get("dieta") == "sim" else None
    diet_data = None
    if diet_type:
        menu = diet_menu_options()
        # refeicao "padrao" de hoje para cada horario, para pre-selecionar a UI
        cycle_start = date.fromisoformat(user["cycle_start_date"]) if user["cycle_start_date"] else date.today()
        day_offset = (date.today() - cycle_start).days
        default_selection = {}
        for meal_type, options in menu.items():
            base_options = [o for o in options if o["dieta"] == diet_type]
            if base_options:
                idx = day_offset % len(base_options)
                default_selection[meal_type] = base_options[idx]["nome"]
        diet_data = {
            "tipo": diet_type, "tipo_label": DIET_TYPE_LABELS.get(diet_type, diet_type),
            "menu": menu, "default_selection": default_selection,
        }

    return render_template(
        "plano.html", user=user, days=days, total=total, logged=logged,
        progress_pct=progress_pct, area_labels=ALL_AREA_LABELS, goal_labels=GOALS,
        period_labels=PERIOD_LABELS, tier_labels=TIER_LABELS, today=today,
        area_label_fn=area_label, goal_label_fn=goal_label, diet_data=diet_data,
    )


# ---------------------------------------------------------------------------
# Checkpoint de fim de ciclo (autoavaliacao 0-10 por tema)
# ---------------------------------------------------------------------------
@app.route("/checkpoint", methods=["GET", "POST"])
@guest_allowed
def checkpoint():
    user = get_user()
    db = get_db()
    cycle_start = date.fromisoformat(user["cycle_start_date"])
    cycle_end = cycle_start + timedelta(days=PLAN_DAYS - 1)
    today = date.today()

    if today <= cycle_end:
        return redirect(url_for("dashboard"))

    ensure_goal_progress_rows(user)
    goal_progress_rows = db.execute(
        "SELECT * FROM goal_progress WHERE user_id=?", (user["id"],)
    ).fetchall()

    if request.method == "GET":
        themes = [{
            "area": r["area"], "goal": r["goal"],
            "label": f"{area_label(user, r['area'])} - {goal_label(user, r['area'], r['goal'])}",
            "measured": round(r["progress_pct"], 1),
        } for r in goal_progress_rows]
        return render_template("checkpoint.html", user=user, themes=themes, cycle=user["current_cycle"])

    new_niveis = dict(user["niveis"])
    for r in goal_progress_rows:
        area, gk = r["area"], r["goal"]
        field = f"rating_{area}_{gk}"
        self_rating = int(request.form.get(field, 5))
        measured = r["progress_pct"]
        new_pct = blend_checkpoint_progress(measured, self_rating)

        db.execute(
            "UPDATE goal_progress SET progress_pct=? WHERE user_id=? AND area=? AND goal=?",
            (new_pct, user["id"], area, gk),
        )
        db.execute(
            "INSERT INTO checkpoint_history (user_id, cycle, area, goal, self_rating, measured_progress, "
            "new_progress, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (user["id"], user["current_cycle"], area, gk, self_rating, measured, new_pct, today.isoformat()),
        )

        if self_rating >= 8 and new_pct >= 66:
            new_niveis[area] = bump_nivel(new_niveis.get(area, "iniciante"))

    db.commit()

    next_cycle = user["current_cycle"] + 1
    area_goal_pairs = flat_goal_pairs(user)
    plan = generate_plan(
        area_goal_pairs, new_niveis, user["pesos"], user["basic_info"]["tempo_livre_min"],
        cycle=next_cycle, custom_labels=user["custom_goal_labels"], diet_type=_diet_type_for(user),
        goal_details=user["goal_details"], dias=PLAN_DAYS, start_date=today,
    )
    _insert_missions(db, user["id"], plan)

    db.execute(
        "UPDATE users SET niveis=?, current_cycle=?, cycle_start_date=?, last_rollover_date=? WHERE id=?",
        (json.dumps(new_niveis), next_cycle, today.isoformat(), today.isoformat(), user["id"]),
    )
    db.commit()
    _update_ai_strategy(get_user() or user)

    return redirect(url_for("dashboard"))


# ---------------------------------------------------------------------------
# Quiz in-app (missoes com action="quiz[:N]", ex.: simulado de concurso)
# ---------------------------------------------------------------------------
def _quiz_topic_for(user, mission):
    """Resolve o assunto especifico que o usuario digitou para essa missao
    (ex.: o edital/materia de concurso, o idioma, etc.), com um rotulo de
    area/objetivo como contexto extra para a IA."""
    key = f"{mission['area']}:{mission['goal']}"
    detalhe = (user.get("goal_details") or {}).get(key)
    if not detalhe:
        info = GOALS_NEEDING_DETAIL.get((mission["area"], mission["goal"]), {})
        detalhe = info.get("fallback")
    area_lbl = area_label(user, mission["area"])
    goal_lbl = goal_label(user, mission["area"], mission["goal"])
    if detalhe:
        return f"{detalhe} (contexto: {area_lbl} / {goal_lbl})"
    return f"{area_lbl} / {goal_lbl}"


def _get_or_generate_quiz(mission, user, n):
    db = get_db()
    cached = db.execute(
        "SELECT questions FROM ai_quiz_cache WHERE mission_id=?", (mission["id"],)
    ).fetchone()
    if cached:
        questions = json.loads(cached["questions"])
        if len(questions) >= min(n, 3):  # cache valido e utilizavel
            return questions[:n], "cache"

    topic = _quiz_topic_for(user, mission)
    # mesma regra da nota de estrategia: convidado (modo teste) nunca chama a
    # IA, so usuarios com conta -- ver _update_ai_strategy() pro motivo.
    ai_allowed = ai.quiz_ai_available() and not session.get("is_guest")
    questions = ai.generate_quiz_questions(topic, n=n) if ai_allowed else None
    source = "ia"
    if not questions:
        # fallback: banco estatico generico (so cobre alguns temas fixos, ex.
        # concurso publico "classico" -- pode nao bater 100% com o tema digitado)
        questions = pick_quiz_questions(mission["area"], mission["goal"], n=n, seed=mission["id"])
        source = "banco_estatico" if questions else "indisponivel"

    if questions:
        db.execute(
            "INSERT INTO ai_quiz_cache (mission_id, topic, source, questions, created_at) "
            "VALUES (?, ?, ?, ?, ?) "
            "ON CONFLICT (mission_id) DO UPDATE SET "
            "topic=EXCLUDED.topic, source=EXCLUDED.source, questions=EXCLUDED.questions, created_at=EXCLUDED.created_at",
            (mission["id"], topic, source, json.dumps(questions), datetime.now().isoformat()),
        )
        db.commit()
    return questions, source


@app.route("/quiz/<int:mission_id>", methods=["GET", "POST"])
@guest_allowed
def quiz(mission_id):
    db = get_db()
    user = get_user()
    user_id = session["user_id"]
    mission = db.execute(
        "SELECT * FROM missions WHERE id=? AND user_id=?", (mission_id, user_id)
    ).fetchone()
    if mission is None:
        return redirect(url_for("dashboard"))
    if mission["completion_pct"] is not None:
        return redirect(url_for("dashboard"))
    if not (mission["action"] or "").startswith("quiz"):
        return redirect(url_for("dashboard"))

    action_parts = (mission["action"] or "quiz:5").split(":")
    n = int(action_parts[1]) if len(action_parts) > 1 and action_parts[1].isdigit() else 5

    questions, source = _get_or_generate_quiz(mission, user, n)

    if not questions:
        return render_template("quiz.html", mission=mission, questions=[], source=source)

    if request.method == "GET":
        return render_template("quiz.html", mission=mission, questions=questions, source=source)

    answers = []
    for i in range(len(questions)):
        val = request.form.get(f"q{i}")
        answers.append(int(val) if val is not None else -1)

    acertos, total, pct, detalhe = grade_quiz(questions, answers)
    points = compute_mission_points(mission["base_points"], pct)
    db.execute(
        "UPDATE missions SET completion_pct=?, points_earned=?, logged_at=? WHERE id=?",
        (pct, points, datetime.now().isoformat(), mission_id),
    )
    db.commit()

    return render_template("quiz_result.html", mission=mission, acertos=acertos, total=total,
                            pct=pct, detalhe=detalhe)


# ---------------------------------------------------------------------------
# APIs de interacao diaria
# ---------------------------------------------------------------------------
@app.route("/api/log_mission/<int:mission_id>", methods=["POST"])
@guest_allowed
def log_mission(mission_id):
    db = get_db()
    user_id = session["user_id"]
    mission = db.execute(
        "SELECT * FROM missions WHERE id=? AND user_id=?", (mission_id, user_id)
    ).fetchone()
    if mission is None:
        return jsonify({"error": "missao nao encontrada"}), 404
    if mission["completion_pct"] is not None:
        return jsonify({"error": "missao ja registrada"}), 400

    payload = request.get_json(silent=True) or request.form
    try:
        pct = float(payload.get("pct", 0))
    except (TypeError, ValueError):
        return jsonify({"error": "percentual invalido"}), 400
    pct = max(0, min(100, pct))

    points = compute_mission_points(mission["base_points"], pct)
    db.execute(
        "UPDATE missions SET completion_pct=?, points_earned=?, logged_at=? WHERE id=?",
        (pct, points, datetime.now().isoformat(), mission_id),
    )
    db.commit()

    return jsonify({"ok": True, "pct": pct, "points": points})


@app.route("/log_sleep", methods=["POST"])
@guest_allowed
def log_sleep():
    user_id = session["user_id"]
    horas = request.form.get("horas")
    db = get_db()
    today = date.today().isoformat()
    try:
        horas_val = float(horas)
    except (TypeError, ValueError):
        horas_val = None
    if horas_val is not None:
        db.execute(
            "INSERT INTO sleep_logs (user_id, date, horas) VALUES (?, ?, ?) "
            "ON CONFLICT (user_id, date) DO UPDATE SET horas=EXCLUDED.horas",
            (user_id, today, horas_val),
        )
        db.commit()
    return redirect(url_for("dashboard"))


init_db()

if __name__ == "__main__":
    debug = os.environ.get("FLASK_DEBUG", "1") == "1"
    app.run(debug=debug, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
