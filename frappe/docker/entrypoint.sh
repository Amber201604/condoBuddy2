#!/bin/bash
set -e

FRAPPE_BENCH_DIR=/home/frappe/frappe-bench
BENCH_NAME="condobuddy2"
SITE_NAME="condobuddy2.local"

# Initialize bench if not exists
if [ ! -d "$FRAPPE_BENCH_DIR/sites" ]; then
    echo "Initializing Frappe bench..."
    bench init --skip-redis-config-generation --frappe-branch version-15 $FRAPPE_BENCH_DIR
    
    cd $FRAPPE_BENCH_DIR
    
    # Add custom app
    bench --site $SITE_NAME get-app $FRAPPE_BENCH_DIR/apps/condobuddy2_erp
    
    # Create site
    bench new-site $SITE_NAME --mariadb-root-password $MARIADB_ROOT_PASSWORD --admin-password admin
    
    # Install app on site
    bench --site $SITE_NAME install-app condobuddy2_erp
    
    # Enable site
    bench use $SITE_NAME
    
    # Set config for core backend URL
    bench --site $SITE_NAME set-config condobuddy_core_url "${CORE_BACKEND_URL:-http://core:8000}"
    
    # Add roles
    bench --site $SITE_NAME add-role Resident
    bench --site $SITE_NAME add-role Property Manager
fi

cd $FRAPPE_BENCH_DIR

case "$1" in
    start)
        echo "Starting Frappe..."
        bench start
        ;;
    migrate)
        echo "Running migrations..."
        bench --site $SITE_NAME migrate
        ;;
    worker)
        echo "Starting worker..."
        bench worker --queue default
        ;;
    scheduler)
        echo "Starting scheduler..."
        bench scheduler
        ;;
    *)
        exec "$@"
        ;;
esac
