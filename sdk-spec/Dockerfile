# Runs this SDK, built from source, under the Flagsmith SDK behavioural spec.
# docker build -f sdk-spec/Dockerfile --build-context harness=<sdk-spec>/harness/python .
FROM python:3.15-slim

WORKDIR /sdk
COPY pyproject.toml poetry.lock README.md ./
COPY flagsmith ./flagsmith
RUN pip install --no-cache-dir .

COPY --from=harness harness.py /harness/harness.py
COPY sdk-spec/steps.py ./sdk-spec/steps.py

ENTRYPOINT ["python", "/harness/harness.py", "sdk-spec/steps.py"]
