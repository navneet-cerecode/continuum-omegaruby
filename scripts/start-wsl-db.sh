#!/bin/bash
# Run only the task-owned Redis + official FalkorDB module, with local persistence.
set -euo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"
runtime=/tmp/continuum-runtime
export LD_LIBRARY_PATH="$runtime/root/usr/lib/x86_64-linux-gnu:$runtime/root/lib/x86_64-linux-gnu"
mkdir -p "$root/.runtime/database"
exec "$runtime/root/usr/bin/redis-server" --bind 127.0.0.1 --port 6380 --protected-mode yes \
  --dir "$root/.runtime/database" --appendonly yes --appendfsync everysec \
  --loadmodule "$root/.runtime/falkordb.so" TIMEOUT_DEFAULT 3000 TIMEOUT_MAX 5000
