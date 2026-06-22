#!/usr/bin/env python3
"""Verify vendor feed URLs without changing a firewall."""

from __future__ import annotations

import argparse
import ssl
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

VENDOR_FILES = {
    "palo-alto": ("pa/ip.txt", "pa/domain.txt", "pa/url.txt"),
    "fortigate": ("fg/ip.txt", "fg/domain.txt", "fg/url.txt"),
    "sophos": ("sf/ipv4.txt", "sf/domain.txt", "sf/url.txt"),
    "check-point": ("cp/ip.txt", "cp/domain.txt", "cp/url.txt"),
    "sonicwall": ("sw/ip.txt", "sw/fqdn.txt"),
    "watchguard": ("wg/ip.txt", "wg/fqdn.txt"),
}

ALIASES = {
    "pa": "palo-alto", "paloalto": "palo-alto", "palo-alto": "palo-alto",
    "fg": "fortigate", "fortinet": "fortigate", "fortigate": "fortigate",
    "sf": "sophos", "sophos": "sophos", "sophos-firewall": "sophos",
    "cp": "check-point", "checkpoint": "check-point", "check-point": "check-point",
    "sw": "sonicwall", "sonicwall": "sonicwall",
    "wg": "watchguard", "watchguard": "watchguard",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check feed reachability and basic content.")
    parser.add_argument("--vendor", required=True)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument("--allow-http", action="store_true")
    return parser.parse_args()


def normalize_base_url(value: str, allow_http: bool) -> str:
    value = value.strip().rstrip("/")
    parsed = urlparse(value)
    if parsed.scheme not in {"https", "http"} or not parsed.netloc:
        raise ValueError("base URL must be an absolute HTTP or HTTPS URL")
    if parsed.scheme == "http" and not allow_http:
        raise ValueError("plain HTTP is disabled; use HTTPS or pass --allow-http")
    if parsed.query or parsed.fragment:
        raise ValueError("base URL must not contain a query string or fragment")
    return value


def main() -> int:
    args = parse_args()
    vendor_key = ALIASES.get(args.vendor.strip().lower())
    if vendor_key is None:
        print("ERROR: unsupported vendor", file=sys.stderr)
        return 2

    try:
        base_url = normalize_base_url(args.base_url, args.allow_http)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    context = ssl.create_default_context()
    failures = 0

    for relative in VENDOR_FILES[vendor_key]:
        url = f"{base_url}/{relative}"
        request = Request(url, headers={"User-Agent": "mvfeed-verifier/1.0"})
        try:
            with urlopen(request, timeout=args.timeout, context=context) as response:
                sample = response.read(512)
                status = getattr(response, "status", 200)
                content_type = response.headers.get("Content-Type", "unknown")
                print(
                    f"OK   {status:<3} {len(sample):>4}B sample  "
                    f"{content_type:<30} {url}"
                )
        except HTTPError as exc:
            failures += 1
            print(f"FAIL HTTP {exc.code}: {url}")
        except URLError as exc:
            failures += 1
            print(f"FAIL {exc.reason}: {url}")

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
