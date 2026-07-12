FROM python:3.11-slim-bookworm

WORKDIR /workspace

# Copy benchmark content and reference databases
COPY config/ /workspace/config/
COPY data/ /workspace/data/
COPY task_data/ /workspace/task_data/

# Copy source
COPY src/ /workspace/src/
COPY pyproject.toml /workspace/
COPY README.md /workspace/
COPY LICENSE LICENSE-DATA NOTICE /workspace/

# Install the package and its bounded Inspect dependency.
RUN pip install --no-cache-dir .

CMD ["tail", "-f", "/dev/null"]
