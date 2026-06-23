FROM frappe/bench:latest

ENV PYTHONUNBUFFERED=1
ENV FRAPPE_BENCH_DIR=/home/frappe/frappe-bench

# Extra tooling: curl (healthcheck) + netcat (wait-for-db in entrypoint)
USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*
USER frappe

WORKDIR /home/frappe

# Stage the custom app source outside the bench dir so `bench init` sees an
# empty target directory.
COPY --chown=frappe:frappe ./apps/condobuddy2_erp /home/frappe/condobuddy2_erp

# Initialise the bench (downloads the Frappe framework) and register the custom
# app at build time. Site creation needs a running MariaDB, so it is deferred to
# the entrypoint at first container start.
RUN bench init --skip-redis-config-generation --frappe-branch version-15 ${FRAPPE_BENCH_DIR} \
    && cd ${FRAPPE_BENCH_DIR} \
    # Register the local custom app manually. `bench get-app <path>` chokes on
    # non-git local sources in this bench version, so we wire it up directly.
    && cp -r /home/frappe/condobuddy2_erp ${FRAPPE_BENCH_DIR}/apps/condobuddy2_erp \
    && ${FRAPPE_BENCH_DIR}/env/bin/pip install --no-cache-dir -e ${FRAPPE_BENCH_DIR}/apps/condobuddy2_erp \
    && printf 'frappe\ncondobuddy2_erp\n' > ${FRAPPE_BENCH_DIR}/sites/apps.txt \
    # Point the bench at the shared external services from docker-compose.
    && bench set-config -g db_host mariadb \
    && bench set-config -g redis_cache "redis://redis:6379/3" \
    && bench set-config -g redis_queue "redis://redis:6379/4" \
    && bench set-config -g redis_socketio "redis://redis:6379/5" \
    && bench set-config -g webserver_port 8080 \
    # `bench start` otherwise spawns its own redis processes and serves on 8000.
    && sed -i '/^redis_/d' Procfile \
    && sed -i 's/--port 8000/--port 8080/' Procfile

WORKDIR ${FRAPPE_BENCH_DIR}

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=10s --start-period=180s --retries=5 \
    CMD curl -f http://localhost:8080/api/method/ping || exit 1

USER root
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
USER frappe

ENTRYPOINT ["/entrypoint.sh"]
CMD ["start"]
