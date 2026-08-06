# -*- coding: utf-8 -*-
"""
Life Builder Assistant -- controle de cota/custo de IA por conta.

Hoje o app usa UMA chave de API por provedor (Groq / DeepSeek), configurada
via variavel de ambiente e compartilhada por todos os usuarios -- os usuarios
nunca tem/criam chave propria (isso e o modelo certo pra um SaaS: quem paga
a Groq/DeepSeek e o Life Builder, nao cada usuario individualmente).

O que faltava pra isso ser sustentavel com usuarios de verdade e um teto de
uso por conta. Este modulo resolve isso com o padrao mais simples que
funciona: cada CONTA (login -- uma conta pode ter varias builds) recebe um
numero fixo de tokens gratis no cadastro (`FREE_TRIAL_AI_TOKENS`). Toda
chamada de IA bem-sucedida debita dessa cota e fica registrada em
`ai_usage_log` (auditoria + base pra decidir preco de plano pago depois).
Quando a cota acaba, a IA simplesmente para de ser chamada -- o resto do
app (missoes, pontos, progressao) continua 100% funcional, exatamente como
ja acontece hoje quando a chave de API nao esta configurada.

Nada aqui depende de gateway de pagamento -- e so a contabilidade de uso.
Plugar Stripe/Mercado Pago depois so precisa trocar `ai_plan` de 'trial'
para 'paid' (ou 'blocked') e resetar/aumentar `ai_tokens_granted` mensalmente
via webhook -- o resto (checagem de cota, registro de uso) nao muda.
"""
import os
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Teste gratis
# ---------------------------------------------------------------------------
# 150k tokens da pra cobrir, com folga, os primeiros ciclos de uso real:
# ~250-300 notas de estrategia (MAX_TOKENS=260 cada, ver ai.py) OU uma
# combinacao de notas + ~10-15 gerações de simulado (QUIZ_MAX_TOKENS=2200
# cada). Ajustavel por variavel de ambiente sem precisar alterar codigo.
FREE_TRIAL_AI_TOKENS = int(os.environ.get("FREE_TRIAL_AI_TOKENS", 150_000))

# Margem de seguranca: nao tenta uma chamada nova se a cota restante for
# menor que isso -- evita ficar no negativo por causa de uma unica chamada
# grande (ex.: geracao de quiz, que sozinha pode consumir ~2.5k tokens).
QUOTA_SAFETY_MARGIN = 2_500

# ---------------------------------------------------------------------------
# Precos por provedor (USD por 1 milhao de tokens) -- conferidos em ago/2026
# nas paginas oficiais de pricing da Groq e da DeepSeek. Preços de LLM mudam
# com frequencia; revise esses numeros periodicamente (ou puxe de uma API de
# pricing, se/quando o provedor oferecer uma) antes de usar como base direta
# de cobranca.
PROVIDER_PRICING = {
    # OpenRouter repassa o preco do modelo escolhido sem markup na inferencia
    # (a taxa dele e na compra de credito). Estes numeros sao do padrao
    # OPENROUTER_MODEL (google/gemini-2.5-flash); se trocar o modelo, ajuste
    # aqui -- senao o custo estimado no painel fica errado.
    "openrouter": {"input_per_m": 0.30, "output_per_m": 2.50},
    # Groq -- llama-3.3-70b-versatile
    "groq": {"input_per_m": 0.59, "output_per_m": 0.79},
}


def estimate_cost_usd(provider, usage):
    """usage: dict com prompt_tokens/completion_tokens (formato OpenAI-compatible,
    devolvido por qualquer provedor OpenAI-compatible). Retorna custo estimado em USD."""
    pricing = PROVIDER_PRICING.get(provider)
    if not pricing or not usage:
        return 0.0
    prompt = usage.get("prompt_tokens") or 0
    completion = usage.get("completion_tokens") or 0
    return (prompt / 1_000_000) * pricing["input_per_m"] + (completion / 1_000_000) * pricing["output_per_m"]


def get_quota(account):
    """account: RealDictRow/dict da tabela `accounts` (precisa ter
    ai_tokens_granted, ai_tokens_used, ai_plan). Retorna um resumo pronto
    pra exibir na UI."""
    granted = account.get("ai_tokens_granted") if account else None
    used = account.get("ai_tokens_used") if account else None
    granted = FREE_TRIAL_AI_TOKENS if granted is None else granted
    used = 0.0 if used is None else used
    remaining = max(0.0, granted - used)
    pct_used = 0 if granted <= 0 else min(100, round((used / granted) * 100))
    return {
        "plan": (account.get("ai_plan") if account else None) or "trial",
        "granted": granted,
        "used": round(used),
        "remaining": round(remaining),
        "pct_used": pct_used,
        "exhausted": remaining <= QUOTA_SAFETY_MARGIN,
    }


def has_quota(account):
    if not account:
        return False
    if (account.get("ai_plan") or "trial") == "blocked":
        return False
    return not get_quota(account)["exhausted"]


def record_usage(db, account_id, user_id, provider, model, purpose, usage):
    """Debita a cota da conta e grava uma linha de auditoria em ai_usage_log.
    Chamar só depois de uma chamada de IA bem-sucedida (usage vindo da API)."""
    if not usage or not account_id:
        return
    prompt = int(usage.get("prompt_tokens") or 0)
    completion = int(usage.get("completion_tokens") or 0)
    total = int(usage.get("total_tokens") or (prompt + completion))
    cost = estimate_cost_usd(provider, usage)

    db.execute(
        "UPDATE accounts SET ai_tokens_used = COALESCE(ai_tokens_used, 0) + ? WHERE id = ?",
        (total, account_id),
    )
    db.execute(
        "INSERT INTO ai_usage_log (account_id, user_id, provider, model, purpose, "
        "prompt_tokens, completion_tokens, total_tokens, cost_usd, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (account_id, user_id, provider, model, purpose, prompt, completion, total, cost,
         datetime.now(timezone.utc).isoformat()),
    )
    db.commit()
