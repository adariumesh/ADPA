# ADPA Lambda Container Image
# Optimized for AWS Lambda with all ML dependencies

FROM public.ecr.aws/lambda/python:3.11

# Copy requirements
COPY requirements.txt ${LAMBDA_TASK_ROOT}/

# Install ML dependencies
RUN pip install --no-cache-dir \
    pandas==2.1.0 \
    numpy==1.24.3 \
    scikit-learn==1.3.0 \
    scipy==1.11.4 \
    boto3>=1.34.0 \
    pydantic>=2.0.0 \
    joblib>=1.3.0

# Copy application code
COPY src/ ${LAMBDA_TASK_ROOT}/src/
COPY lambda_function.py ${LAMBDA_TASK_ROOT}/
COPY config/ ${LAMBDA_TASK_ROOT}/config/

# Set environment variables
ENV PYTHONPATH=${LAMBDA_TASK_ROOT}
ENV PYTHONUNBUFFERED=1

# Lambda handler
CMD ["lambda_function.lambda_handler"]