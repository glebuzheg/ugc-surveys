FROM ghcr.io/astral-sh/uv:0.9.5-python3.13-bookworm-slim@sha256:60d8ee2c1f7ffce050822adcb44907514e39f29d2d7b37732e8fca9f4f6113af

ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_NO_CACHE=1 \
    PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PATH="/app/.venv/bin:$PATH"
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project && useradd --create-home app \
    && mkdir staticfiles && chown app:app staticfiles
COPY --chown=app:app . .
USER app
EXPOSE 8000
CMD ["sh", "-c", "python manage.py collectstatic --noinput && exec uvicorn config.asgi:application --host 0.0.0.0 --port 8000 --workers ${WEB_CONCURRENCY:-1} --lifespan off"]
