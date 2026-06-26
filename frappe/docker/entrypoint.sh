#!/bin/bash
set -e

FRAPPE_BENCH_DIR=/home/frappe/frappe-bench
SITE_NAME="${FRAPPE_SITE_NAME:-condobuddy2.local}"
MARIADB_HOST="${MARIADB_HOST:-mariadb}"
MARIADB_ROOT_PASSWORD="${MARIADB_ROOT_PASSWORD:-condobuddy_mariadb_root}"
ADMIN_PASSWORD="${FRAPPE_ADMIN_PASSWORD:-admin}"
CORE_BACKEND_URL="${CORE_BACKEND_URL:-http://core:8000}"

cd "$FRAPPE_BENCH_DIR"

# Create the site on first boot. The bench itself (framework + custom app) is
# already baked into the image; only the site needs a live MariaDB.
if [ "$1" = "start" ] && [ ! -f "sites/$SITE_NAME/site_config.json" ]; then
    echo "Waiting for MariaDB at ${MARIADB_HOST}:3306..."
    until nc -z "$MARIADB_HOST" 3306; do
        sleep 2
    done
    echo "MariaDB is reachable. Creating site ${SITE_NAME}..."

    bench new-site "$SITE_NAME" \
        --db-host "$MARIADB_HOST" \
        --mariadb-root-password "$MARIADB_ROOT_PASSWORD" \
        --admin-password "$ADMIN_PASSWORD" \
        --no-mariadb-socket

    bench use "$SITE_NAME"
    bench --site "$SITE_NAME" set-config condobuddy_core_url "$CORE_BACKEND_URL"

    # ERPNext must be installed before the custom app, which extends its
    # procurement/manufacturing doctypes (BOM, Purchase Order, GL Entry, ...).
    echo "Installing erpnext..."
    bench --site "$SITE_NAME" install-app erpnext \
        || echo "WARN: install-app erpnext failed; condobuddy2_erp doctypes that depend on it may not work."

    echo "Installing condobuddy2_erp..."
    bench --site "$SITE_NAME" install-app condobuddy2_erp \
        || echo "WARN: install-app condobuddy2_erp failed; Frappe framework will still run."

    # `add-role` is best-effort: roles are normally shipped with the app.
    bench --site "$SITE_NAME" add-role "Resident" 2>/dev/null || true
    bench --site "$SITE_NAME" add-role "Property Manager" 2>/dev/null || true
fi

case "$1" in
    start)
        echo "Starting Frappe (site: ${SITE_NAME})..."
        exec bench start
        ;;
    migrate)
        echo "Running migrations..."
        exec bench --site "$SITE_NAME" migrate
        ;;
    worker)
        echo "Starting worker..."
        exec bench worker --queue default
        ;;
    scheduler)
        echo "Starting scheduler..."
        exec bench scheduler
        ;;
    *)
        exec "$@"
        ;;
esac
