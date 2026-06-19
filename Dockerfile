FROM python:3.14-slim AS builder

# Installing uv: https://docs.astral.sh/uv/guides/integration/docker/#installing-uv
COPY --from=ghcr.io/astral-sh/uv:0.11.20 /uv /uvx /bin/

WORKDIR /app

# Installing dependencies
RUN --mount=type=bind,source=scripts/uv.lock,target=uv.lock \
  --mount=type=bind,source=scripts/pyproject.toml,target=pyproject.toml \
  uv export --frozen --no-cache \
  | uv pip install --system --no-cache -r -

COPY ./scripts /app/

CMD ["/bin/bash"]
