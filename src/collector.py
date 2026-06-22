#!/usr/bin/env python3
from __future__ import annotations

import argparse
import concurrent.futures
import datetime as dt
import ipaddress
import json
import math
import os
import re
import shutil
import sqlite3
import sys
import tarfile
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Iterable

APP_HOME = Path(os.environ.get("MVFEED_HOME", "/opt/mvfeed"))
API_URL = os.environ.get(
    "MVFEED_API_URL",
    "https://siberguvenlik.gov.tr/api/address/index",
)
DB_PATH = Path(os.environ.get("MVFEED_DB_PATH", str(APP_HOME / "data/feed.db")))
PUBLIC_ROOT = Path(
    os.environ.get("MVFEED_PUBLIC_ROOT", "/srv/mvfeed/public")
)
STAGING_ROOT = Path(
    os.environ.get("MVFEED_STAGING_ROOT", str(APP_HOME / "staging"))
)
BACKUP_ROOT = Path(
    os.environ.get("MVFEED_BACKUP_ROOT", str(APP_HOME / "backups"))
)
ROUTE_CONFIG = Path(
    os.environ.get("MVFEED_ROUTE_CONFIG", "/etc/mvfeed/routes.json")
)
LOG_PREFIX = os.environ.get("MVFEED_LOG_PREFIX", "[mvfeed]")
PAGE_SIZE = max(1, int(os.environ.get("MVFEED_PAGE_SIZE", "20")))
REQUEST_DELAY = max(0.0, float(os.environ.get("MVFEED_REQUEST_DELAY", "0.20")))
FULL_WORKERS = max(1, min(32, int(os.environ.get("MVFEED_WORKERS", "16"))))
BATCH_DELAY = max(0.0, float(os.environ.get("MVFEED_BATCH_DELAY", "0.20")))
MAX_RETRIES = max(1, int(os.environ.get("MVFEED_MAX_RETRIES", "7")))
OVERLAP_HOURS = max(1, int(os.environ.get("MVFEED_OVERLAP_HOURS", "24")))
BACKUP_KEEP = max(1, int(os.environ.get("MVFEED_BACKUP_KEEP", "7")))

HEADERS = {
    "User-Agent": os.environ.get("MVFEED_USER_AGENT", "MultiVendorThreatFeed/1.0"),
    "Accept": "application/json",
    "Referer": "https://siberguvenlik.gov.tr/",
}

DOMAIN_RE = re.compile(
    r"^(?=.{1,253}\.?$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.?$",
    re.IGNORECASE,
)


def log(message: str) -> None:
    stamp = dt.datetime.now().astimezone().isoformat(timespec="seconds")
    print(f"{stamp} {LOG_PREFIX} {message}", flush=True)


def utc_now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def api_datetime(value: dt.datetime) -> str:
    return value.astimezone(dt.timezone.utc).replace(tzinfo=None).strftime("%Y-%m-%d %H:%M:%S")


def parse_api_datetime(value: str | None) -> dt.datetime | None:
    if not value:
        return None
    try:
        parsed = dt.datetime.fromisoformat(value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=dt.timezone.utc)
        return parsed.astimezone(dt.timezone.utc)
    except ValueError:
        return None


def connect_db() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=60)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA temp_store=MEMORY")
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS ioc (
            id INTEGER PRIMARY KEY,
            value TEXT NOT NULL,
            type TEXT NOT NULL,
            description TEXT,
            source TEXT,
            observed_at TEXT,
            criticality INTEGER,
            connection_type TEXT,
            cached_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_ioc_type_value
            ON ioc(type, value);

        CREATE INDEX IF NOT EXISTS idx_ioc_observed_at
            ON ioc(observed_at);

        CREATE TABLE IF NOT EXISTS meta (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        """
    )
    return conn


def meta_get(conn: sqlite3.Connection, key: str) -> str | None:
    row = conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
    return str(row["value"]) if row else None


def meta_set(conn: sqlite3.Connection, key: str, value: Any) -> None:
    conn.execute(
        """
        INSERT INTO meta(key, value) VALUES(?, ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value
        """,
        (key, str(value)),
    )


def fetch_page(params: dict[str, Any]) -> dict[str, Any]:
    url = API_URL + "?" + urllib.parse.urlencode(params)
    request = urllib.request.Request(url, headers=HEADERS)

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                payload = response.read()
            data = json.loads(payload.decode("utf-8"))
            if not isinstance(data, dict) or not isinstance(data.get("models"), list):
                raise ValueError("API response schema is invalid")
            return data
        except urllib.error.HTTPError as exc:
            if exc.code not in (408, 429, 500, 502, 503, 504) or attempt == MAX_RETRIES:
                raise
            retry_after = exc.headers.get("Retry-After")
            wait = float(retry_after) if retry_after and retry_after.isdigit() else min(60, 2 ** attempt)
            log(f"HTTP {exc.code}; retry {attempt}/{MAX_RETRIES} after {wait:.0f}s")
            time.sleep(wait)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError) as exc:
            if attempt == MAX_RETRIES:
                raise
            wait = min(60, 2 ** attempt)
            log(f"Temporary API error: {exc}; retry {attempt}/{MAX_RETRIES} after {wait}s")
            time.sleep(wait)

    raise RuntimeError("unreachable")


def upsert_models(conn: sqlite3.Connection, models: Iterable[dict[str, Any]]) -> int:
    now = utc_now().isoformat(timespec="seconds")
    rows: list[tuple[Any, ...]] = []

    for model in models:
        try:
            ioc_id = int(model["id"])
            value = str(model.get("url", "")).strip()
            ioc_type = str(model.get("type", "")).strip().lower()
        except (KeyError, TypeError, ValueError):
            continue

        if not value or ioc_type not in {"domain", "url", "ip", "ip6", "ip6net"}:
            continue

        criticality = model.get("criticality_level")
        try:
            criticality_int = int(criticality) if criticality is not None else None
        except (TypeError, ValueError):
            criticality_int = None

        rows.append(
            (
                ioc_id,
                value,
                ioc_type,
                model.get("desc"),
                model.get("source"),
                model.get("date"),
                criticality_int,
                model.get("connectiontype"),
                now,
            )
        )

    conn.executemany(
        """
        INSERT INTO ioc(
            id, value, type, description, source, observed_at,
            criticality, connection_type, cached_at
        )
        VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            value = excluded.value,
            type = excluded.type,
            description = excluded.description,
            source = excluded.source,
            observed_at = excluded.observed_at,
            criticality = excluded.criticality,
            connection_type = excluded.connection_type,
            cached_at = excluded.cached_at
        """,
        rows,
    )
    return len(rows)


def full_sync(conn: sqlite3.Connection) -> None:
    cutoff = meta_get(conn, "full_cutoff")
    next_page = int(meta_get(conn, "full_next_page") or "1")

    if not cutoff:
        cutoff = api_datetime(utc_now())
        next_page = 1
        meta_set(conn, "full_cutoff", cutoff)
        meta_set(conn, "full_next_page", next_page)
        meta_set(conn, "full_complete", "0")
        conn.commit()

    first = fetch_page({"page": next_page, "date_lte": cutoff})
    total = int(first.get("totalCount") or 0)
    count = int(first.get("count") or len(first.get("models", [])) or PAGE_SIZE)
    total_pages = max(1, math.ceil(total / count))

    log(
        f"Full sync cutoff={cutoff}; total={total}; pages={total_pages}; "
        f"starting page={next_page}; workers={FULL_WORKERS}"
    )

    page = next_page
    first_page_data: dict[str, Any] | None = first

    with concurrent.futures.ThreadPoolExecutor(
        max_workers=FULL_WORKERS,
        thread_name_prefix="usomfetch",
    ) as executor:
        while page <= total_pages:
            batch_start = page
            batch_end = min(total_pages, batch_start + FULL_WORKERS - 1)
            batch_pages = list(range(batch_start, batch_end + 1))
            results: dict[int, dict[str, Any]] = {}
            futures: dict[concurrent.futures.Future[dict[str, Any]], int] = {}

            for batch_page in batch_pages:
                if first_page_data is not None and batch_page == next_page:
                    results[batch_page] = first_page_data
                    first_page_data = None
                else:
                    future = executor.submit(
                        fetch_page,
                        {"page": batch_page, "date_lte": cutoff},
                    )
                    futures[future] = batch_page

            for future in concurrent.futures.as_completed(futures):
                batch_page = futures[future]
                results[batch_page] = future.result()

            stored_in_batch = 0
            for batch_page in batch_pages:
                data = results.get(batch_page)
                if data is None:
                    raise RuntimeError(
                        f"Missing page result during full sync: {batch_page}/{total_pages}"
                    )
                models = data.get("models", [])
                if not models:
                    raise RuntimeError(
                        f"Unexpected empty page during full sync: {batch_page}/{total_pages}"
                    )
                stored_in_batch += upsert_models(conn, models)

            meta_set(conn, "full_next_page", batch_end + 1)
            meta_set(conn, "full_total_expected", total)
            conn.commit()

            if batch_end % 160 == 0 or batch_end == total_pages:
                cached = conn.execute("SELECT COUNT(*) AS c FROM ioc").fetchone()["c"]
                log(
                    f"Full sync page={batch_end}/{total_pages}; "
                    f"batch={batch_start}-{batch_end}; "
                    f"stored_in_batch={stored_in_batch}; db_rows={cached}"
                )

            page = batch_end + 1
            if page <= total_pages and BATCH_DELAY:
                time.sleep(BATCH_DELAY)

    meta_set(conn, "full_complete", "1")
    meta_set(conn, "full_completed_at", utc_now().isoformat(timespec="seconds"))
    meta_set(conn, "incremental_since", cutoff)
    conn.commit()
    log("Full sync completed")


def incremental_sync(conn: sqlite3.Connection) -> None:
    if meta_get(conn, "full_complete") != "1":
        raise RuntimeError("Full sync is not complete")

    previous = parse_api_datetime(meta_get(conn, "incremental_since"))
    if previous is None:
        previous = utc_now() - dt.timedelta(hours=OVERLAP_HOURS)

    since = previous - dt.timedelta(hours=OVERLAP_HOURS)
    cutoff_dt = utc_now()
    cutoff = api_datetime(cutoff_dt)

    first = fetch_page(
        {
            "page": 1,
            "date_gte": api_datetime(since),
            "date_lte": cutoff,
        }
    )
    total = int(first.get("totalCount") or 0)
    count = int(first.get("count") or len(first.get("models", [])) or PAGE_SIZE)
    total_pages = math.ceil(total / count) if total else 0

    log(
        f"Incremental sync since={api_datetime(since)} cutoff={cutoff}; "
        f"total={total}; pages={total_pages}"
    )

    inserted = 0
    for page in range(1, total_pages + 1):
        data = first if page == 1 else fetch_page(
            {
                "page": page,
                "date_gte": api_datetime(since),
                "date_lte": cutoff,
            }
        )
        inserted += upsert_models(conn, data.get("models", []))
        if page % 25 == 0 or page == total_pages:
            conn.commit()
        time.sleep(REQUEST_DELAY)

    meta_set(conn, "incremental_since", cutoff)
    meta_set(conn, "last_incremental_at", cutoff_dt.isoformat(timespec="seconds"))
    conn.commit()
    log(f"Incremental sync completed; processed={inserted}")


def normalize_domain(raw: str) -> str | None:
    value = raw.strip().lower().rstrip(".")
    value = re.sub(r"^[a-z][a-z0-9+.-]*://", "", value)
    value = value.split("/", 1)[0]
    if value.startswith("*."):
        value = value[2:]
    try:
        value = value.encode("idna").decode("ascii")
    except UnicodeError:
        return None
    if DOMAIN_RE.fullmatch(value):
        return value
    return None


def normalize_url(raw: str) -> str | None:
    value = raw.strip()
    if not value:
        return None
    if "://" not in value:
        value = "http://" + value
    try:
        parsed = urllib.parse.urlsplit(value)
    except ValueError:
        return None
    host = normalize_domain(parsed.hostname or "")
    if not host:
        return None
    port = f":{parsed.port}" if parsed.port else ""
    path = parsed.path or ""
    query = f"?{parsed.query}" if parsed.query else ""
    result = f"{host}{port}{path}{query}"
    return result[:2048]


def normalize_ip(raw: str, expected: str) -> str | None:
    value = raw.strip()
    try:
        if expected == "ip":
            address = ipaddress.ip_address(value)
            return str(address) if address.version == 4 else None
        if expected == "ip6":
            address = ipaddress.ip_address(value)
            return str(address) if address.version == 6 else None
        if expected == "ip6net":
            network = ipaddress.ip_network(value, strict=False)
            return str(network) if network.version == 6 else None
    except ValueError:
        return None
    return None


def atomic_write(path: Path, values: Iterable[str]) -> int:
    unique = sorted(set(values))
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            for value in unique:
                handle.write(value + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temp_name, 0o644)
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)
    return len(unique)



ALLOWED_OUTPUT_KEYS = {
    "ipv4",
    "ipv6",
    "ipv6net",
    "domain",
    "url",
    "all_ip",
}


def load_route_config() -> tuple[str, dict[str, str]]:
    """Load public output routes without hardcoding production URL paths.

    The JSON file maps relative output paths to normalized feed sets. Keeping
    this outside the repository lets operators choose private aliases without
    publishing their production route layout.
    """
    if not ROUTE_CONFIG.is_file():
        raise RuntimeError(
            f"Route configuration is missing: {ROUTE_CONFIG}. "
            "Copy config/routes.example.json and adjust it before publishing."
        )

    try:
        payload = json.loads(ROUTE_CONFIG.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Unable to read route configuration: {exc}") from exc

    status_prefix = str(payload.get("status_prefix", "core")).strip("/")
    raw_outputs = payload.get("outputs")
    if not status_prefix or not isinstance(raw_outputs, dict) or not raw_outputs:
        raise RuntimeError("Route configuration must define status_prefix and outputs")

    outputs: dict[str, str] = {}
    for raw_path, raw_key in raw_outputs.items():
        relative = Path(str(raw_path))
        key = str(raw_key)

        if relative.is_absolute() or ".." in relative.parts:
            raise RuntimeError(f"Unsafe output path in route configuration: {raw_path}")
        if key not in ALLOWED_OUTPUT_KEYS:
            raise RuntimeError(f"Unsupported output key for {raw_path}: {key}")

        normalized = relative.as_posix().lstrip("/")
        if not normalized or normalized.endswith("/"):
            raise RuntimeError(f"Invalid output file path: {raw_path}")
        outputs[normalized] = key

    return status_prefix, outputs

def backup_current() -> None:
    if not PUBLIC_ROOT.exists():
        return
    BACKUP_ROOT.mkdir(parents=True, exist_ok=True)
    stamp = utc_now().strftime("%Y%m%dT%H%M%SZ")
    archive = BACKUP_ROOT / f"feeds-{stamp}.tar.gz"
    with tarfile.open(archive, "w:gz") as tar:
        for child in PUBLIC_ROOT.iterdir():
            if child.name in {"healthz", ".well-known"}:
                continue
            tar.add(child, arcname=child.name)

    archives = sorted(BACKUP_ROOT.glob("feeds-*.tar.gz"), reverse=True)
    for old in archives[BACKUP_KEEP:]:
        old.unlink(missing_ok=True)


def publish(conn: sqlite3.Connection) -> None:
    if meta_get(conn, "full_complete") != "1":
        raise RuntimeError("Refusing to publish before full sync completes")

    rows = conn.execute("SELECT value, type FROM ioc").fetchall()
    feeds: dict[str, set[str]] = {
        "ipv4": set(),
        "ipv6": set(),
        "ipv6net": set(),
        "domain": set(),
        "url": set(),
    }

    rejected = 0
    for row in rows:
        raw = str(row["value"])
        ioc_type = str(row["type"])
        normalized: str | None
        if ioc_type == "domain":
            normalized = normalize_domain(raw)
            target = "domain"
        elif ioc_type == "url":
            normalized = normalize_url(raw)
            target = "url"
        elif ioc_type in {"ip", "ip6", "ip6net"}:
            normalized = normalize_ip(raw, ioc_type)
            target = {"ip": "ipv4", "ip6": "ipv6", "ip6net": "ipv6net"}[ioc_type]
        else:
            normalized = None
            target = ""

        if normalized:
            feeds[target].add(normalized)
        else:
            rejected += 1

    total_valid = sum(len(values) for values in feeds.values())
    if total_valid < 1000:
        raise RuntimeError(f"Refusing to publish suspiciously small feed: {total_valid}")

    STAGING_ROOT.mkdir(parents=True, exist_ok=True)
    run_dir = Path(tempfile.mkdtemp(prefix="publish-", dir=STAGING_ROOT))

    try:
        all_ip = feeds["ipv4"] | feeds["ipv6"] | feeds["ipv6net"]


        status_prefix, route_outputs = load_route_config()
        feed_sets: dict[str, set[str]] = {
            **feeds,
            "all_ip": all_ip,
        }

        counts: dict[str, int] = {}
        for relative, feed_key in route_outputs.items():
            values = feed_sets[feed_key]
            counts[relative] = atomic_write(run_dir / relative, values)

        status = {
            "status": "ok",
            "generated_at": utc_now().isoformat(timespec="seconds"),
            "database_rows": len(rows),
            "valid_records": total_valid,
            "rejected_records": rejected,
            "counts": {
                "ipv4": len(feeds["ipv4"]),
                "ipv6": len(feeds["ipv6"]),
                "ipv6net": len(feeds["ipv6net"]),
                "domain": len(feeds["domain"]),
                "url": len(feeds["url"]),
            },
        }
        atomic_write(run_dir / status_prefix / "status.txt", [json.dumps(status, ensure_ascii=False)])
        (run_dir / status_prefix / "status.json").write_text(
            json.dumps(status, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        os.chmod(run_dir / status_prefix / "status.json", 0o644)

        backup_current()

        for source in run_dir.rglob("*"):
            if not source.is_file():
                continue
            relative = source.relative_to(run_dir)
            destination = PUBLIC_ROOT / relative
            destination.parent.mkdir(parents=True, exist_ok=True)

            # Staging and public roots may live on separate filesystems.
            # Copy into a temporary file inside the destination directory,
            # fsync it, then atomically replace the final file in-place.
            fd, temp_name = tempfile.mkstemp(
                prefix=f".{destination.name}.",
                dir=destination.parent,
            )
            try:
                with source.open("rb") as src_handle, os.fdopen(fd, "wb") as dst_handle:
                    shutil.copyfileobj(src_handle, dst_handle)
                    dst_handle.flush()
                    os.fsync(dst_handle.fileno())
                os.chmod(temp_name, source.stat().st_mode & 0o777)
                os.replace(temp_name, destination)
            finally:
                if os.path.exists(temp_name):
                    os.unlink(temp_name)

        meta_set(conn, "last_publish_at", status["generated_at"])
        conn.commit()
        log(f"Published feeds: {status['counts']}; rejected={rejected}")
    finally:
        shutil.rmtree(run_dir, ignore_errors=True)


def status(conn: sqlite3.Connection) -> None:
    counts = {
        row["type"]: row["count"]
        for row in conn.execute(
            "SELECT type, COUNT(*) AS count FROM ioc GROUP BY type ORDER BY type"
        )
    }
    result = {
        "database": str(DB_PATH),
        "rows_by_type": counts,
        "full_complete": meta_get(conn, "full_complete"),
        "full_next_page": meta_get(conn, "full_next_page"),
        "full_cutoff": meta_get(conn, "full_cutoff"),
        "last_incremental_at": meta_get(conn, "last_incremental_at"),
        "last_publish_at": meta_get(conn, "last_publish_at"),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


def main() -> int:
    parser = argparse.ArgumentParser(description="Multi-vendor threat-feed collector")
    parser.add_argument(
        "command",
        choices=["full", "incremental", "publish", "sync", "status"],
    )
    args = parser.parse_args()

    for directory in (STAGING_ROOT, BACKUP_ROOT, PUBLIC_ROOT):
        directory.mkdir(parents=True, exist_ok=True)

    conn = connect_db()
    try:
        if args.command == "full":
            full_sync(conn)
        elif args.command == "incremental":
            incremental_sync(conn)
        elif args.command == "publish":
            publish(conn)
        elif args.command == "sync":
            incremental_sync(conn)
            publish(conn)
        elif args.command == "status":
            status(conn)
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        log("Interrupted")
        raise SystemExit(130)
    except Exception as exc:
        log(f"ERROR: {exc}")
        raise
