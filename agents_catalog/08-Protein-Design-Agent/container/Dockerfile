ARG AWS_DEFAULT_REGION=us-west-2

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
RUN /opt/conda/bin/pip install --no-cache-dir -U -r /tmp/requirements.txt \
    && rm /tmp/requirements.txt

# Clone and install EvoProtGrad
RUN git clone https://github.com/NREL/EvoProtGrad.git /tmp/EvoProtGrad \
    && cd /tmp/EvoProtGrad \
    && /opt/conda/bin/pip install . \
    && cd / \
    && rm -rf /tmp/EvoProtGrad/.git

# Debug print statements - these will appear in the CodeBuild logs
RUN echo "=== Python Path ===" && \
    /opt/conda/bin/python -c "import sys; print(sys.path)" && \
    echo "=== Installed Packages ===" && \
    /opt/conda/bin/pip list && \
    echo "=== EvoProtGrad Package Info ===" && \
    /opt/conda/bin/pip show evo_prot_grad || echo "EvoProtGrad not installed"

# Test importing the module
RUN echo "=== Testing Import ===" && \
    echo "import evo_prot_grad; print('Import successful')" > /tmp/test_import.py && \
    /opt/conda/bin/python /tmp/test_import.py

# Copy scripts
COPY scripts/ /home/scripts/
WORKDIR /home/scripts

## Cleanup ##
RUN /opt/conda/bin/pip cache purge \
    && rm -rf /tmp/tmp* \
    && rm -iRf /root/.cache