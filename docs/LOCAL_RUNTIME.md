# Local FalkorDB fallback used for verification

Docker Compose is the portable default. On the implementation machine, Docker Desktop 4.84.0 failed before engine startup because its inference Unix socket could not be opened. No Docker reset, global setting change or unrelated data removal was performed.

The existing Ubuntu WSL runtime was usable. Redis packages were downloaded and unpacked under `/tmp/continuum-runtime` with task-local apt indexes, without system package installation. The official FalkorDB 4.14.11 x64 module was downloaded into ignored `.runtime/falkordb.so`:

```powershell
New-Item -ItemType Directory -Force .runtime
Invoke-WebRequest https://github.com/FalkorDB/FalkorDB/releases/download/v4.14.11/falkordb-x64.so -OutFile .runtime\falkordb.so
wsl -d Ubuntu -- bash /mnt/c/path/to/GraphHacks/scripts/setup-wsl-runtime.sh --start
```

Replace `/mnt/c/path/to/GraphHacks` with the WSL form of your checkout path. The setup script fetches Debian packages from the configured Ubuntu repositories into its temporary runtime and starts Redis with the official module. It stays in the foreground; keep this terminal open. Stop with Ctrl+C for a graceful save. Persistent AOF/RDB files are in `.runtime/database`, inside the checkout; the temporary package runtime may be cleared when WSL exits. Rerun setup with `--start` in that case.

Then follow the native Python/Node setup in README, using database `127.0.0.1:6380`. Windows localhost forwarding to WSL was verified on this machine. Network/runtime differences on another machine may require its local WSL host address; do not expose Redis publicly.

`scripts/start-wsl-db.sh` can restart the already-unpacked runtime while WSL stays running. The optional script requires Ubuntu's configured package repositories and a compatible glibc-based x64 environment. The module's release license and Redis package licenses apply. It is real FalkorDB, not an emulation or alternative graph store.
