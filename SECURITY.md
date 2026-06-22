# Security policy

## Reporting a vulnerability

Please do not open a public issue for a suspected vulnerability. Contact the repository owner privately and include the affected version, reproduction steps, and likely impact.

## Deployment notes

This project generates files; it does not provide access control. A short or uncommon URL path is not a security boundary. Protect the publication endpoint with TLS and an appropriate combination of network allowlists, authentication, rate limiting, monitoring, and patch management.

Keep these items outside the repository:

- real route aliases
- hostnames and public IP addresses
- credentials, API keys, tokens, certificates, and private keys
- customer or organization-specific identifiers
- production web-server and cloud firewall configuration

Run secret scanning before every public release and rotate any secret that was ever committed, even if the commit was later deleted.
