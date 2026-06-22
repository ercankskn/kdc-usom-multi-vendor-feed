# KDC USOM Multi‑Vendor Feed

A self-hosted Python service that collects threat indicators published by USOM, normalizes them, and generates firewall-ready text feeds for multiple vendors.

This repository contains only the collector, installer, example configuration, tests, and systemd units. KDC production hostnames, customer addresses, cloud resource names, approval flows, and website files are deliberately excluded.

[Türkçe dokümantasyon](README.md)

## Vendor output aliases

The example route map uses short, configurable aliases:

- `pa` — Palo Alto Networks
- `fg` — Fortinet FortiGate
- `sf` — Sophos Firewall
- `cp` — Check Point
- `sw` — SonicWall
- `wg` — WatchGuard

Production routes are not hard-coded. They are controlled through `/etc/mvfeed/routes.json` and can be replaced with operator-specific values.

> An obscure path is not an access-control mechanism. Protect the publication endpoint with TLS, network allowlists, authentication, rate limiting, monitoring, and other controls appropriate to your environment.

## Features

- resumable initial synchronization
- up to 16 workers for the full import
- overlapping incremental updates to avoid missing late records
- IPv4, IPv6, domain, and URL normalization
- vendor-shaped outputs from one local dataset
- atomic publishing across different filesystems
- SQLite state management
- recurring systemd timer
- rolling feed backups and JSON/text status output

## Install with Git

Ubuntu 24.04 and Debian-family systems:

```bash
git clone https://github.com/ercankskn/kdc-usom-multi-vendor-feed.git
cd kdc-usom-multi-vendor-feed
sudo bash scripts/install.sh
```

Review the route and runtime configuration:

```bash
sudoedit /etc/mvfeed/routes.json
sudoedit /etc/mvfeed/mvfeed.env
```

Start the initial synchronization:

```bash
sudo systemctl start mvfeed-full.service
sudo journalctl -u mvfeed-full.service -f
```

Enable incremental updates after the initial synchronization completes:

```bash
sudo systemctl enable --now mvfeed-sync.timer
systemctl list-timers mvfeed-sync.timer --all
```

## Tests

```bash
python3 -m py_compile src/collector.py
python3 -m unittest discover -s tests -v
```

## License

No open-source license has been selected for this draft. Add a suitable license before announcing the project if you want others to use, modify, or redistribute it.

## Security

Do not open public issues for suspected vulnerabilities. Read [SECURITY.md](SECURITY.md) for reporting and deployment guidance.
