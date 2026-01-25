#!/bin/bash
set -e

echo "🚀 Starting Home Miner Manager..."

# Run database migrations
echo "📦 Running database migrations..."
for migration in /app/core/migrations/*.py; do
    if [ -f "$migration" ]; then
        echo "  Running $(basename $migration)..."
        python3 "$migration" /config/data.db || echo "  ⚠️ Migration $(basename $migration) failed or already applied"
    fi
done

echo "✅ Migrations complete"

# Start the main application
uvicorn main:app --host 0.0.0.0 --port ${WEB_PORT}
