FROM pytorch/pytorch:2.6.0-cuda12.4-cudnn9-devel

ENV TZ=UTC
ENV DEBIAN_FRONTEND=noninteractive

# Add NVIDIA runtime environment
ENV NVIDIA_VISIBLE_DEVICES all
ENV NVIDIA_DRIVER_CAPABILITIES compute,utility
ENV NVIDIA_REQUIRE_CUDA "cuda>=11.0"

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    python3-pip \
    curl \
    unzip \
    wget \
    jq \
    && rm -rf /var/lib/apt/lists/*

RUN apt-get update && apt-get install -y \
    openslide-tools \
    libopencv-dev \
    python3-opencv \
    && rm -rf /var/lib/apt/lists/*
    
RUN curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip" && \
    unzip awscliv2.zip && \
    ./aws/install

# Install Trident
RUN pip install git+https://github.com/mahmoodlab/trident.git
RUN pip install boto3

WORKDIR /trident

# Create entrypoint script
COPY entrypoint.sh /trident/entrypoint.sh
COPY inference.py /trident/inference.py
COPY model.py /trident/model.py
COPY model.pth /
RUN chmod +x /trident/entrypoint.sh

ENTRYPOINT ["/trident/entrypoint.sh"]