# Life Builder -- imagem de producao (Flask + PostgreSQL, servido via gunicorn)
FROM python:3.12-slim

# evita .pyc no volume e garante logs em tempo real no `docker logs`
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# usuario nao-root (boa pratica de seguranca em containers)
RUN useradd --create-home --uid 1000 appuser \
    && chown -R appuser:appuser /app
USER appuser

ENV PORT=5000

EXPOSE 5000

# init_db() ja roda na importacao de app.py (veja o fim do arquivo), entao o
# gunicorn cria as tabelas sozinho no primeiro start -- nao precisa de um
# comando de setup separado. Requer DB_HOST/DB_USER/DB_PASSWORD/DB_NAME
# configurados via variavel de ambiente (ver .env.example).
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--timeout", "60", "app:app"]
