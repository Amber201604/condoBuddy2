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

# Initialise the bench (downloads the Frappe framework) and fetch ERPNext. This
# layer is independent of the custom app source, so iterating on the custom app
# does NOT re-trigger the expensive Frappe/ERPNext download + asset build.
#
# ERPNext provides the modules (Manufacturing, Buying, Accounts, Projects,
# Stock, ...) and the `erpnext` python package that the vendored procurement
# DocTypes in condobuddy2_erp depend on. Must match the Frappe branch.
# Site creation needs a running MariaDB, so it is deferred to the entrypoint.
RUN bench init --skip-redis-config-generation --frappe-branch version-15 ${FRAPPE_BENCH_DIR} \
    && cd ${FRAPPE_BENCH_DIR} \
    && bench get-app --branch version-15 erpnext \
    # Point the bench at the shared external services from docker-compose.
    && bench set-config -g db_host mariadb \
    && bench set-config -g redis_cache "redis://redis:6379/3" \
    && bench set-config -g redis_queue "redis://redis:6379/4" \
    && bench set-config -g redis_socketio "redis://redis:6379/5" \
    && bench set-config -g webserver_port 8080 \
    # `bench start` otherwise spawns its own redis processes and serves on 8000.
    && sed -i '/^redis_/d' Procfile \
    && sed -i 's/--port 8000/--port 8080/' Procfile

# Register the local custom app. Placed late so edits only rebuild cheap layers.
# `bench get-app <path>` chokes on non-git local sources in this bench version,
# so we wire it up directly.
COPY --chown=frappe:frappe ./apps/condobuddy2_erp ${FRAPPE_BENCH_DIR}/apps/condobuddy2_erp
RUN cd ${FRAPPE_BENCH_DIR} \
    && ${FRAPPE_BENCH_DIR}/env/bin/pip install --no-cache-dir -e ${FRAPPE_BENCH_DIR}/apps/condobuddy2_erp \
    # Enforce install/load order: frappe -> erpnext -> condobuddy2_erp (the
    # custom app depends on erpnext doctypes).
    && printf 'frappe\nerpnext\ncondobuddy2_erp\n' > ${FRAPPE_BENCH_DIR}/sites/apps.txt

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
