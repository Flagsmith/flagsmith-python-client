# Builds the SDK from source with the adapter for the Flagsmith SDK behavioural spec.
# Build from the repository root: docker build -f spec-adapter/Dockerfile .
FROM python:3.12-slim

WORKDIR /sdk
COPY pyproject.toml poetry.lock README.md ./
COPY flagsmith ./flagsmith
RUN pip install --no-cache-dir .

COPY spec-adapter/adapter.py ./spec-adapter/adapter.py

ENV PORT=8080
EXPOSE 8080
CMD ["python", "spec-adapter/adapter.py"]
