FROM python:3.14-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_ROOT_USER_ACTION=ignore \
    PORT=8000

RUN groupadd --system learnmate \
    && useradd --system --gid learnmate --create-home learnmate \
    && mkdir -p /data \
    && chown learnmate:learnmate /data

WORKDIR /app

COPY requirements.txt ./
RUN python -m pip install --upgrade pip && python -m pip install -r requirements.txt

COPY --chown=learnmate:learnmate alembic.ini ./
COPY --chown=learnmate:learnmate alembic ./alembic
COPY --chown=learnmate:learnmate app ./app

USER learnmate
EXPOSE 8000

ENV DATABASE_URL=sqlite:////data/learnmate.db

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/ready', timeout=3)"

CMD ["sh", "-c", "exec python -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
