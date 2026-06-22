#!/usr/bin/env python3
"""Generate reviewable firewall integration kits from a feed base URL.

The generated output is intentionally conservative: it prepares URLs, object names,
checks, and vendor-specific snippets without logging into or changing a firewall.
Always review the result against the exact firmware release before applying it.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

VENDORS = {
    "palo-alto": {
        "alias": "pa",
        "template": "palo-alto-edl-plan.txt",
        "files": {"IP_URL": "pa/ip.txt", "DOMAIN_URL": "pa/domain.txt", "URL_URL": "pa/url.txt"},
    },
    "fortigate": {
        "alias": "fg",
        "template": "fortigate-cli.conf",
        "files": {"IP_URL": "fg/ip.txt", "DOMAIN_URL": "fg/domain.txt", "URL_URL": "fg/url.txt"},
    },
    "sophos": {
        "alias": "sf",
        "template": "sophos-feed-plan.txt",
        "files": {"IP_URL": "sf/ipv4.txt", "DOMAIN_URL": "sf/domain.txt", "URL_URL": "sf/url.txt"},
    },
    "check-point": {
        "alias": "cp",
        "template": "check-point-feed-plan.txt",
        "files": {"IP_URL": "cp/ip.txt", "DOMAIN_URL": "cp/domain.txt", "URL_URL": "cp/url.txt"},
    },
    "sonicwall": {
        "alias": "sw",
        "template": "sonicwall-deag-plan.txt",
        "files": {"IP_URL": "sw/ip.txt", "FQDN_URL": "sw/fqdn.txt"},
    },
    "watchguard": {
        "alias": "wg",
        "template": "watchguard-integration-plan.txt",
        "files": {"IP_URL": "wg/ip.txt", "FQDN_URL": "wg/fqdn.txt"},
    },
}

ALIASES = {
    "pa": "palo-alto",
    "paloalto": "palo-alto",
    "palo-alto": "palo-alto",
    "fg": "fortigate",
    "fortinet": "fortigate",
    "fortigate": "fortigate",
    "sf": "sophos",
    "sophos": "sophos",
    "sophos-firewall": "sophos",
    "cp": "check-point",
    "checkpoint": "check-point",
    "check-point": "check-point",
    "sw": "sonicwall",
    "sonicwall": "sonicwall",
    "wg": "watchguard",
    "watchguard": "watchguard",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a vendor-specific firewall integration kit."
    )
    parser.add_argument("--vendor", required=True, help="Vendor name or short alias")
    parser.add_argument("--base-url", required=True, help="Feed base URL, preferably HTTPS")
    parser.add_argument("--object-prefix", default="USOM", help="Object name prefix")
    parser.add_argument("--interval", type=int, default=15, help="Refresh interval in minutes")
    parser.add_argument("--output", default="build/firewall-kit", help="Output directory")
    parser.add_argument(
        "--allow-http",
        action="store_true",
        help="Allow plain HTTP. Not recommended for production.",
    )
    parser.add_argument("--force", action="store_true", help="Overwrite an existing output directory")
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


def normalize_prefix(value: str) -> str:
    value = value.strip()
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,32}", value):
        raise ValueError("object prefix must be 1-32 letters, numbers, underscores, or hyphens")
    return value


def render(template: str, values: dict[str, str]) -> str:
    for key, value in values.items():
        template = template.replace("{{" + key + "}}", value)
    leftovers = sorted(set(re.findall(r"\{\{([A-Z0-9_]+)\}\}", template)))
    if leftovers:
        raise ValueError(f"unresolved template values: {', '.join(leftovers)}")
    return template


def main() -> int:
    args = parse_args()
    try:
        vendor_key = ALIASES.get(args.vendor.strip().lower())
        if vendor_key is None:
            raise ValueError("unsupported vendor; choose pa, fg, sf, cp, sw, or wg")

        base_url = normalize_base_url(args.base_url, args.allow_http)
        prefix = normalize_prefix(args.object_prefix)
        if not 1 <= args.interval <= 43200:
            raise ValueError("interval must be between 1 and 43200 minutes")

        repo_root = Path(__file__).resolve().parents[1]
        vendor = VENDORS[vendor_key]
        template_path = repo_root / "templates" / "firewalls" / vendor["alias"] / vendor["template"]
        if not template_path.is_file():
            raise FileNotFoundError(f"template not found: {template_path}")

        output_root = Path(args.output).resolve() / vendor_key
        if output_root.exists() and any(output_root.iterdir()) and not args.force:
            raise FileExistsError(f"output directory is not empty: {output_root}; use --force")
        output_root.mkdir(parents=True, exist_ok=True)

        urls = {name: f"{base_url}/{relative}" for name, relative in vendor["files"].items()}
        values = {
            **urls,
            "BASE_URL": base_url,
            "OBJECT_PREFIX": prefix,
            "INTERVAL_MIN": str(args.interval),
            "VENDOR": vendor_key,
        }

        rendered = render(template_path.read_text(encoding="utf-8"), values)
        output_file = output_root / vendor["template"]
        output_file.write_text(rendered, encoding="utf-8", newline="\n")

        feed_lines = [f"{name}={url}" for name, url in sorted(urls.items())]
        (output_root / "feed-urls.txt").write_text("\n".join(feed_lines) + "\n", encoding="utf-8")

        manifest = {
            "schema_version": 1,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "vendor": vendor_key,
            "vendor_alias": vendor["alias"],
            "base_url": base_url,
            "object_prefix": prefix,
            "refresh_interval_minutes": args.interval,
            "feeds": urls,
            "output_file": output_file.name,
            "safety": {
                "automatic_firewall_changes": False,
                "review_required": True,
                "notes": [
                    "Review the generated kit against the exact firmware version.",
                    "Keep TLS certificate validation enabled.",
                    "Apply changes in a maintenance window and verify rollback steps.",
                ],
            },
        }
        (output_root / "manifest.json").write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )

        print(f"Generated: {output_root}")
        print(f"Primary file: {output_file}")
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
