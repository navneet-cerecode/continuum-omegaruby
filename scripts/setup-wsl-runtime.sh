#!/bin/bash
# Optional local fallback when Docker Desktop cannot start. No system installation.
set -euo pipefail
runtime=/tmp/continuum-runtime
mkdir -p "$runtime/lists/partial" "$runtime/cache/archives/partial" "$runtime/root"
cd "$runtime"
apt-get -o "Dir::State::lists=$runtime/lists" -o "Dir::Cache=$runtime/cache" -o Debug::NoLocking=true update
apt-get -o "Dir::State::lists=$runtime/lists" download redis-server redis-tools libjemalloc2 liblzf1 libatomic1 libgomp1
for package in ./*.deb; do dpkg-deb -x "$package" root; done
export LD_LIBRARY_PATH="$runtime/root/usr/lib/x86_64-linux-gnu:$runtime/root/lib/x86_64-linux-gnu"
ldd "$runtime/root/usr/bin/redis-server"
root="$(cd "$(dirname "$0")/.." && pwd)"
ldd "$root/.runtime/falkordb.so"
"$runtime/root/usr/bin/redis-server" --version
if [ "${1:-}" = "--start" ]; then
  exec bash "$(dirname "$0")/start-wsl-db.sh"
fi
