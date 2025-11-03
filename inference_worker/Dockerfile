FROM nvidia/cuda:11.8.0-cudnn8-devel-ubuntu22.04 AS builder

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHON_VERSION=3.11

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    python${PYTHON_VERSION} \
    python3-pip \
    python${PYTHON_VERSION}-venv \
    git \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

RUN python${PYTHON_VERSION} -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .

RUN pip install --no-cache-dir torch==2.1.1 torchvision==0.16.1 torchaudio==2.1.1 --index-url https://download.pytorch.org/whl/cu118
RUN pip install --no-cache-dir -r requirements.txt


FROM nvidia/cuda:11.8.0-cudnn8-runtime-ubuntu22.04

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    python3.11 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app

COPY inference.py .
COPY tracing.py .

CMD ["python3", "inference.py"]