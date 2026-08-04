# -*- coding: utf-8 -*-
"""
Life Builder Assistant -- envio de e-mail transacional (hoje so recuperacao de
senha), via SMTP puro (biblioteca padrao do Python, sem dependencia nova).

Mesmo principio do restante do app com servicos externos opcionais (Groq/
DeepSeek em ai.py): sem SMTP_HOST configurado, `send_password_reset` nao
manda nada e devolve False -- o fluxo de reset de senha continua existindo,
so nao chega e-mail nenhum. Para permitir testar o fluxo localmente sem um
provedor de verdade, o link de reset e sempre logado no console do servidor
nesse caso (nunca devolvido na resposta HTTP -- isso vazaria o token para
qualquer um que interceptasse a requisicao)."""
import os
import smtplib
from email.message import EmailMessage

SMTP_HOST = os.environ.get("SMTP_HOST")
SMTP_PORT = int(os.environ.get("SMTP_PORT", 587))
SMTP_USER = os.environ.get("SMTP_USER")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD")
SMTP_FROM = os.environ.get("SMTP_FROM", SMTP_USER or "no-reply@life-builder.local")
# a maioria dos provedores (Gmail, SendGrid, Resend, Amazon SES via SMTP)
# fala STARTTLS na porta 587 -- ajustavel se o provedor exigir outra coisa.
SMTP_USE_TLS = os.environ.get("SMTP_USE_TLS", "1") == "1"


def email_available():
    return bool(SMTP_HOST and SMTP_USER and SMTP_PASSWORD)


def send_password_reset(to_email, reset_url):
    """Retorna True se o e-mail foi enviado de verdade. Falha silenciosamente
    (loga e devolve False) se o SMTP nao estiver configurado ou o envio
    falhar por qualquer motivo -- quem chama trata isso como "ok, mas sem
    e-mail", nunca como erro fatal do fluxo de reset."""
    if not email_available():
        print(f"[email_sender] SMTP nao configurado -- link de reset para {to_email}: {reset_url}")
        return False

    msg = EmailMessage()
    msg["Subject"] = "Redefinir sua senha -- Life Builder"
    msg["From"] = SMTP_FROM
    msg["To"] = to_email
    msg.set_content(
        "Recebemos um pedido para redefinir a senha da sua conta no Life Builder.\n\n"
        f"Para criar uma nova senha, acesse: {reset_url}\n\n"
        "Esse link expira em 1 hora. Se você não pediu essa redefinição, "
        "pode ignorar este e-mail -- sua senha continua a mesma."
    )

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
            if SMTP_USE_TLS:
                server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
        return True
    except (smtplib.SMTPException, OSError, TimeoutError) as e:
        print(f"[email_sender] falha ao enviar e-mail de reset para {to_email}: {e}")
        return False
