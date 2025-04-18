# Use a slim Debian-based Python image
FROM public.ecr.aws/docker/library/python:3.11

# Define the Lambda task root
ARG LAMBDA_TASK_ROOT=/var/task

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    python3-pip \
    curl \
    unzip \
    wget \
    jq \
    # OpenSlide dependencies
    openslide-tools \
    # OpenCV dependencies
    libopencv-dev \
    python3-opencv \
    && rm -rf /var/lib/apt/lists/*

# Install Python packages
RUN pip3 install --no-cache-dir \
    openslide-python \
    openslide-bin \
    awslambdaric \
    boto3 \
    pytz \
    numpy \
    pillow

# Copy your function code
COPY lambda_function.py ${LAMBDA_TASK_ROOT}/

# Set the working directory
WORKDIR ${LAMBDA_TASK_ROOT}

# Set the entrypoint to the RIC
ENTRYPOINT ["python", "-m", "awslambdaric"]

# Set the handler as the command
CMD ["lambda_function.lambda_handler"]