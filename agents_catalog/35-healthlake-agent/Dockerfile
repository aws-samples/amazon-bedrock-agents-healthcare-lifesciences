# AgentCore-compatible Dockerfile
FROM public.ecr.aws/docker/library/python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies including bedrock-agentcore
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir bedrock-agentcore

# Copy application code
COPY . .

# AgentCore uses port 8080 by default
EXPOSE 8080

# Run the AgentCore application
CMD ["python", "agent_agentcore.py"]
