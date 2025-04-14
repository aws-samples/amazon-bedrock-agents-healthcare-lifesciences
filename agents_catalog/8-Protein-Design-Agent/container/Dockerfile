ARG AWS_DEFAULT_REGION=us-east-1

FROM 763104351884.dkr.ecr.${AWS_DEFAULT_REGION}.amazonaws.com/pytorch-inference:2.4.0-gpu-py311-cu124-ubuntu22.04-ec2

# Install git and other build dependencies
RUN apt-get update \
    && apt-get install -y git \
    && apt-get upgrade -y \
    && apt-get autoremove -y \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install additional dependencies from requirements.txt file
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -U -r /tmp/requirements.txt \
    && rm /tmp/requirements.txt

# Clone and install EvoProtGrad
RUN git clone https://github.com/NREL/EvoProtGrad.git /tmp/EvoProtGrad \
    && cd /tmp/EvoProtGrad \
    && pip install -e . \
    && cd / \
    && rm -rf /tmp/EvoProtGrad/.git

# Copy scripts
COPY scripts/ /home/scripts/
WORKDIR /home/scripts

## Cleanup ##
RUN pip cache purge \
    && rm -rf /tmp/tmp* \
    && rm -iRf /root/.cache