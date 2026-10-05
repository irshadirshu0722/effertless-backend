FROM python:3.12-slim AS builder

WORKDIR /app

# Install Poetry for reproducible dependency installation.
RUN pip install --no-cache-dir "poetry>=2.0,<3.0"

# Copy dependency definitions before application code to keep Docker layers cacheable.
COPY pyproject.toml poetry.lock* ./

# Install application and development dependencies for the local development image.
RUN poetry config virtualenvs.create false && \
    poetry install --no-interaction --no-ansi --no-root

# Production runner stage
FROM python:3.12-slim AS runner

WORKDIR /app

# Create non-root user
RUN groupadd -r effortless && useradd -r -g effortless -d /app -s /sbin/nologin effortless

# Copy installed packages from builder
COPY --from=builder /usr/local /usr/local

# Copy application source
COPY src/ src/

# Set ownership
RUN chown -R effortless:effortless /app

USER effortless

EXPOSE 8000

ENV APP_ENV=production \
    APP_DEBUG=false \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
