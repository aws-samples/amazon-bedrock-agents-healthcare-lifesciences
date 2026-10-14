FROM --platform=linux/arm64 ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir bedrock-agentcore aws-opentelemetry-distro

COPY *.py ./
COPY tools/ ./tools/
COPY workflows/ ./workflows/

EXPOSE 8080

CMD ["opentelemetry-instrument", "python", "agent.py"]
