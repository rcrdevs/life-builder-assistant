# -*- coding: utf-8 -*-
"""
Life Builder Assistant -- sondas de diagnostico das integracoes externas.

Por que isso existe: todo servico externo aqui (IA, e-mail, pagamento, vídeo)
falha em SILENCIO de proposito -- se a IA cair, o usuario recebe o fallback
determinístico em vez de um erro na cara. Isso e bom pro usuario e péssimo pra
quem mantem o app: tres falhas reais passaram meses despercebidas --

  1. a Groq recusava toda chamada (Cloudflare bloqueava o User-Agent do urllib);
  2. a conta DeepSeek ficou sem saldo (HTTP 402);
  3. a nota de estrategia voltava vazia por incompatibilidade de chave no JSON.

Nenhuma delas aparecia em lugar nenhum. Estas sondas fazem a pergunta direta
-- "esse provedor responde AGORA?" -- e devolvem o motivo real quando nao.

Sem Flask e sem banco de proposito: sao funcoes puras de rede, faceis de
chamar de um script ou de um teste.
"""
import json
import os
import smtplib
import urllib.error
import urllib.request

import ai
import billing
import email_sender
import youtube_api

PROBE_TIMEOUT = 15


def _resultado(ok, detalhe, extra=None):
    saida = {"ok": ok, "detalhe": detalhe}
    if extra:
        saida.update(extra)
    return saida


def _probe_chat_completions(nome, url, api_key, model):
    """Chamada minima (1 token) a uma API estilo OpenAI, so pra saber se ela
    aceita a chave e responde."""
    if not api_key:
        return _resultado(None, "não configurado (sem chave)")
    payload = {"model": model, "messages": [{"role": "user", "content": "ping"}], "max_tokens": 1}
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode("utf-8"), method="POST",
        headers=ai._auth_headers(api_key),
    )
    try:
        with urllib.request.urlopen(req, timeout=PROBE_TIMEOUT) as resp:
            json.loads(resp.read().decode("utf-8"))
        return _resultado(True, f"respondendo (modelo {model})")
    except urllib.error.HTTPError as e:
        try:
            corpo = e.read().decode("utf-8")
            msg = (json.loads(corpo).get("error") or {}).get("message") or corpo[:160]
        except Exception:
            msg = ""
        dica = {
            401: "chave inválida ou revogada",
            402: "sem saldo — a conta precisa de crédito",
            403: "acesso recusado (bloqueio de origem ou permissão da chave)",
            429: "limite de requisições atingido",
        }.get(e.code, "")
        partes = [f"HTTP {e.code}"]
        if dica:
            partes.append(dica)
        if msg:
            partes.append(f"“{msg.strip()}”")
        return _resultado(False, " — ".join(partes))
    except (urllib.error.URLError, ValueError, TimeoutError) as e:
        return _resultado(False, f"falha de rede: {e!r}")


def probe_openrouter():
    """Alem do ping, consulta o credito -- 'sem saldo' e o modo de falha tipico
    de provedor pre-pago, e foi exatamente o que derrubou a geracao de quiz em
    producao antes (numa outra API, mas o mesmo tipo de falha)."""
    base = _probe_chat_completions(
        "openrouter", ai.OPENROUTER_URL, ai.OPENROUTER_API_KEY, ai.OPENROUTER_MODEL)
    if not ai.OPENROUTER_API_KEY:
        return base
    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/credits",
        headers=ai._auth_headers(ai.OPENROUTER_API_KEY),
    )
    try:
        with urllib.request.urlopen(req, timeout=PROBE_TIMEOUT) as resp:
            info = (json.loads(resp.read().decode("utf-8")) or {}).get("data") or {}
        comprado = float(info.get("total_credits") or 0)
        usado = float(info.get("total_usage") or 0)
        base["saldo"] = f"US$ {comprado - usado:.2f} restantes (de US$ {comprado:.2f})"
        base["saldo_disponivel"] = (comprado - usado) > 0
    except Exception:
        pass
    return base


def probe_groq():
    return _probe_chat_completions("groq", ai.GROQ_URL, ai.GROQ_API_KEY, ai.GROQ_MODEL)


def probe_youtube():
    if not youtube_api.youtube_available():
        return _resultado(None, "não configurado (sem YOUTUBE_API_KEY) — recomendações usam os canais curados")
    video = youtube_api.search_video("aula de português para concurso")
    if video:
        return _resultado(True, f"respondendo (exemplo: {video['titulo'][:60]})")
    return _resultado(False, "não retornou resultado — cota diária esgotada ou chave sem permissão")


def probe_smtp():
    if not email_sender.email_available():
        return _resultado(None, "não configurado — o link de recuperação de senha só vai pro log do servidor")
    try:
        with smtplib.SMTP(email_sender.SMTP_HOST, email_sender.SMTP_PORT, timeout=PROBE_TIMEOUT) as s:
            if email_sender.SMTP_USE_TLS:
                s.starttls()
            s.login(email_sender.SMTP_USER, email_sender.SMTP_PASSWORD)
        return _resultado(True, f"autenticado em {email_sender.SMTP_HOST}")
    except (smtplib.SMTPException, OSError, TimeoutError) as e:
        return _resultado(False, f"falha ao autenticar: {e!r}")


def probe_stripe():
    if not billing.billing_available():
        return _resultado(None, "não configurado — a tela de planos mostra 'em breve'")
    faltando = [
        env for plano, env in billing.PLAN_PRICE_ENV.items() if not os.environ.get(env)
    ]
    try:
        stripe = billing._stripe()
        stripe.Account.retrieve()
    except Exception as e:
        return _resultado(False, f"chave recusada: {e!r}")
    if faltando:
        return _resultado(False, f"chave OK, mas faltam os Price IDs: {', '.join(faltando)}")
    if not billing.STRIPE_WEBHOOK_SECRET:
        return _resultado(False, "chave OK, mas sem STRIPE_WEBHOOK_SECRET — assinaturas não seriam ativadas")
    return _resultado(True, "chave, preços e webhook configurados")


# Ordem importa: e a ordem em que aparecem no painel, das mais criticas
# (geram conteudo pro usuario) pras acessorias.
PROBES = [
    ("OpenRouter (primário — quiz, prova e nota)", probe_openrouter),
    ("Groq (fallback gratuito)", probe_groq),
    ("YouTube Data API (vídeos)", probe_youtube),
    ("SMTP (recuperação de senha)", probe_smtp),
    ("Stripe (assinaturas)", probe_stripe),
]


def run_all():
    """Roda todas as sondas em sequencia. Retorna lista de (nome, resultado).
    Chamado so sob demanda (botao no painel) -- cada sonda faz rede."""
    return [(nome, fn()) for nome, fn in PROBES]


def config_overview():
    """Estado de configuracao SEM tocar na rede -- serve pra pagina abrir
    rapido, antes de o admin pedir o teste ao vivo."""
    return [
        ("OPENROUTER_API_KEY", bool(ai.OPENROUTER_API_KEY), ai.OPENROUTER_MODEL),
        ("GROQ_API_KEY", bool(ai.GROQ_API_KEY), ai.GROQ_MODEL),
        ("YOUTUBE_API_KEY", youtube_api.youtube_available(), "—"),
        ("SMTP_HOST", email_sender.email_available(), email_sender.SMTP_HOST or "—"),
        ("STRIPE_SECRET_KEY", billing.billing_available(), "—"),
    ]
