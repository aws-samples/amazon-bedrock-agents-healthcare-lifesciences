FROM public.ecr.aws/lambda/python:3.12

# Install system dependencies
RUN dnf update -y && \
    dnf install -y gcc gcc-c++ make && \
    dnf clean all && \
    rm -rf /var/cache/dnf

# Copy requirements and install Python dependencies
COPY requirements.txt ${LAMBDA_TASK_ROOT}/
RUN pip install --no-cache-dir -r ${LAMBDA_TASK_ROOT}/requirements.txt

# Remove any problematic uuid package that might have been installed as a dependency
RUN pip uninstall -y uuid || true

# Copy function code
COPY lambda_function.py ${LAMBDA_TASK_ROOT}/
COPY optimizer.py ${LAMBDA_TASK_ROOT}/

# Set the CMD to your handler
CMD [ "lambda_function.lambda_handler" ]
