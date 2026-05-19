FROM python:3.12-slim AS builder

# uvのインストール: https://docs.astral.sh/uv/guides/integration/docker/#installing-uv
COPY --from=ghcr.io/astral-sh/uv:0.11.8 /uv /uvx /bin/

ENV VIRTUAL_ENV=/app/.venv
RUN uv venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# パッケージのインストール
COPY ./scripts/pyproject.toml ./scripts/uv.lock .
RUN uv pip install --no-cache -r pyproject.toml

COPY ./scripts /app/scripts

WORKDIR /app

# 仮想環境の有効化
ENV PATH="/app/.venv/bin:$PATH"

CMD ["/bin/bash"]