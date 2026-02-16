# nosemgrep dockerfile-source-not-pinned
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim
WORKDIR /app

ARG AWS_REGION="us-east-1"

# All environment variables in one layer
ENV UV_SYSTEM_PYTHON=1 \
    UV_COMPILE_BYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DOCKER_CONTAINER=1

COPY requirements.txt requirements.txt

# Install from requirements file
RUN uv pip install --no-cache-dir -r requirements.txt
RUN uv pip install --no-cache-dir aws-opentelemetry-distro>=0.10.1


# Set AWS region environment variable
ENV AWS_REGION=$AWS_REGION
ENV AWS_DEFAULT_REGION=$AWS_REGION

# Signal that this is running in Docker for host binding logic
ENV DOCKER_CONTAINER=1

# Create non-root user
RUN useradd -m -u 1000 bedrock_agentcore
USER bedrock_agentcore

EXPOSE 8080
EXPOSE 8000

# Copy entire project (respecting .dockerignore)
COPY . .

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD ["/bin/sh", "-c", "python -c \"import socket; s=socket.socket(); s.settimeout(1); s.connect(('localhost', 8080)); s.close()\" || exit 1"]

# Use the full module path
CMD ["opentelemetry-instrument", "python", "-m", "kb"]
