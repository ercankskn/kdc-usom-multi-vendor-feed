# Architecture

1. The collector reads the upstream JSON API.
2. Records are cached in a local SQLite database using WAL mode.
3. A full synchronization can resume from its last committed page.
4. Incremental synchronization overlaps the previous window to handle late-arriving records safely.
5. Normalized feed sets are mapped to relative output files by an external JSON route configuration.
6. Files are built in staging, copied to a temporary file on the destination filesystem, fsynced, and atomically renamed.
7. systemd runs the initial job and the recurring incremental job.

The project uses only the Python standard library at runtime.
