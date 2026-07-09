FROM --platform=linux/arm64 ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

# Copy dependency file and install
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir bedrock-agentcore aws-opentelemetry-distro

# Copy agent code
COPY *.py ./
COPY tools/ ./tools/

EXPOSE 8080

# Run with OTEL instrumentation for AgentCore observability
CMD ["opentelemetry-instrument", "python", "agent.py"]
