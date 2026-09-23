FROM python:3.12-slim AS builder

WORKDIR /build

COPY requirements.txt .

RUN pip install --no-cache-dir --user -r requirements.txt

FROM python:3.12-slim

RUN groupadd --gid 1000 worker && \
    useradd --uid 1000 --gid worker --shell /bin/bash --create-home worker

WORKDIR /app

COPY --from=builder /root/.local /home/worker/.local
COPY worker.py .

RUN chown -R worker:worker /app /home/worker/.local

USER worker

ENV PATH=/home/worker/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1

CMD ["python3", "worker.py"]
