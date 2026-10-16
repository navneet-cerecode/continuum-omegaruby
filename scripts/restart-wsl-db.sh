#!/bin/bash
set -euo pipefail
runtime=/tmp/continuum-runtime
export LD_LIBRARY_PATH="$runtime/root/usr/lib/x86_64-linux-gnu:$runtime/root/lib/x86_64-linux-gnu"
"$runtime/root/usr/bin/redis-cli" -h 127.0.0.1 -p 6380 SHUTDOWN SAVE
printf 'Task-owned FalkorDB stopped. Restarting in 20 seconds for outage verification.\n'
sleep 20
exec bash "$(dirname "$0")/start-wsl-db.sh"
