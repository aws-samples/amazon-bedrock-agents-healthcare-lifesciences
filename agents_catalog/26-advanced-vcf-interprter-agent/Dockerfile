FROM public.ecr.aws/docker/library/python:3.10-slim
WORKDIR /app



COPY runtime_requirements.txt runtime_requirements.txt
# Install from requirements file
RUN pip install -r runtime_requirements.txt





# Set AWS region environment variable

ENV AWS_REGION=us-east-1
ENV AWS_DEFAULT_REGION=us-east-1


# Signal that this is running in Docker for host binding logic
ENV DOCKER_CONTAINER=1

# Create non-root user
RUN useradd -m -u 1000 bedrock_agentcore
USER bedrock_agentcore

EXPOSE 8080
EXPOSE 8000

# Copy entire project (respecting .dockerignore)
COPY . .

# Use the full module path

CMD ["python", "-m", "vcf_agent_marker"]
