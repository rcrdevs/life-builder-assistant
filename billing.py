# -*- coding: utf-8 -*-
"""
Life Builder Assistant -- integracao de faturamento (Stripe Checkout +
assinatura recorrente).

Mesmo principio de todo servico externo opcional no projeto (Groq/DeepSeek em
ai.py, SMTP em email_sender.py): sem STRIPE_SECRET_KEY configurada, o app
inteiro continua funcionando normal -- so a tela de upgrade mostra "em breve"
em vez dos botoes de assinatura (ver billing_available() e a rota /upgrade em
app.py).

O que este modulo faz:
- Cria uma Stripe Checkout Session pra assinar o plano Pro ou Elite.
- Verifica a assinatura de eventos de webhook da Stripe.

O que este modulo NAO faz (fica em app.py, de proposito -- e logica de
negocio, nao integracao com servico externo): decidir quando ativar/
desativar um plano, escrever no banco, ou qualquer regra sobre cota de IA.
Isso ja e tratado por ai_billing.py; este modulo so faz a ponte com a Stripe.
"""
import os

STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET")

# preco (tokens de IA por mes) de cada plano pago -- ver a auditoria de
# monetizacao: Pro cobre uso normal com nota de estrategia todo ciclo + uso
# moderado de quiz; Elite e uma cota alta de "uso justo", ainda barata em
# custo real de IA (Groq/DeepSeek, ver ai_billing.PROVIDER_PRICING).
PLAN_TOKENS = {
    "pro": 500_000,
    "elite": 1_500_000,
}
# cada plano precisa de um Price ID criado no dashboard da Stripe -- nao tem
# como isso existir antes de a conta Stripe ser criada, entao fica em env var.
PLAN_PRICE_ENV = {
    "pro": "STRIPE_PRICE_PRO",
    "elite": "STRIPE_PRICE_ELITE",
}


def billing_available():
    return bool(STRIPE_SECRET_KEY)


def _stripe():
    import stripe
    stripe.api_key = STRIPE_SECRET_KEY
    return stripe


def create_checkout_session(account, plan, success_url, cancel_url):
    """Cria uma Stripe Checkout Session pra assinar `plan` ('pro'/'elite').
    Retorna a URL de checkout, ou None se a Stripe nao estiver configurada,
    o plano for invalido, o Price ID daquele plano nao estiver definido, ou a
    chamada a API falhar por qualquer motivo -- quem chama deve tratar None
    caindo de volta pra tela de upgrade sem quebrar a navegacao."""
    if not billing_available() or plan not in PLAN_TOKENS:
        return None
    price_id = os.environ.get(PLAN_PRICE_ENV[plan])
    if not price_id:
        return None

    stripe = _stripe()
    kwargs = dict(
        mode="subscription",
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=success_url,
        cancel_url=cancel_url,
        client_reference_id=account["id"],
        metadata={"account_id": account["id"], "plan": plan},
    )
    if account.get("stripe_customer_id"):
        kwargs["customer"] = account["stripe_customer_id"]
    elif account.get("email"):
        kwargs["customer_email"] = account["email"]

    try:
        session = stripe.checkout.Session.create(**kwargs)
        return session.url
    except Exception:
        return None


def verify_webhook_event(payload, sig_header):
    """Verifica a assinatura de um evento de webhook da Stripe. Retorna o
    evento (dict-like) se valido, ou None se o webhook nao estiver
    configurado ou a assinatura nao bater -- quem chama deve responder 400
    nesse caso, sem processar nada do corpo da requisicao."""
    if not billing_available() or not STRIPE_WEBHOOK_SECRET:
        return None
    stripe = _stripe()
    try:
        return stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
    except (ValueError, stripe.error.SignatureVerificationError):
        return None
