FROM public.ecr.aws/lambda/python:3.13

COPY bedrock-ez-search ${LAMBDA_TASK_ROOT}/bedrock-ez-search
COPY cik-ref.json ${LAMBDA_TASK_ROOT}
COPY lambda_function.py ${LAMBDA_TASK_ROOT}
COPY requirements.txt ${LAMBDA_TASK_ROOT}

RUN dnf update -y \
    && dnf clean all \
    && rm -rf /var/cache/dnf/* \
    && pip install ${LAMBDA_TASK_ROOT}/bedrock-ez-search \
    && pip install -r ${LAMBDA_TASK_ROOT}/requirements.txt

CMD [ "lambda_function.handler" ]