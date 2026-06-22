FROM frappe/bench:latest

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV FRAPPE_BENCH_DIR=/home/frappe/frappe-bench

USER root

# Install additional system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    vim \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

# Create bench directory
RUN mkdir -p ${FRAPPE_BENCH_DIR} && chown -R frappe:frappe ${FRAPPE_BENCH_DIR}

USER frappe

WORKDIR ${FRAPPE_BENCH_DIR}

# Copy custom app
COPY --chown=frappe:frappe ./apps/condobuddy2_erp ${FRAPPE_BENCH_DIR}/apps/condobuddy2_erp

# Initialize bench (this will be done at runtime via entrypoint)
# We keep the image lean; bench init happens on first container start

# Expose ports
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8080/api/method/healthcheck || exit 1

# Entrypoint
COPY --chown=frappe:frappe docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
CMD ["start"]
