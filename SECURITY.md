# Security Policy

## Reporting a vulnerability

If you find a security issue, please report it privately rather than opening a public issue. The preferred channel is a GitHub Security Advisory on this repository. You can also reach the maintainer directly using the contact listed in the repository profile.

When you report:

- Describe the vulnerability type (auth bypass, XSS, SSRF, SQL injection, etc.).
- Identify the affected component and version.
- Include steps to reproduce when possible.
- Describe potential impact and severity.
- Suggest a fix if you have one in mind.

Please do not publicly disclose the issue before a fix has shipped. The default coordination window is 90 days. Receipt of a report is acknowledged within 48 hours, and credit is given in the resulting advisory unless you prefer to remain anonymous.

## Known limitations and how to mitigate them

This project is a reference codebase intended for learning and adaptation. The list below describes the current state of the security surface and the steps required before deploying anything based on it.

### LLM prompt injection

User input (text, STT transcripts, tool outputs) can manipulate the LLM. Mitigations in place:

- The system prompt is server-controlled and not user-editable.
- Destructive actions (memory deletion, thread deletion) require `HumanInTheLoopMiddleware` approval.
- Tool outputs are wrapped with delimiters to discourage instruction injection.
- Basic injection patterns are filtered in `backend/api/routes/v1/voice.py`.

For production, deploy with human approval gates enabled and review any tool you add for privilege escalation paths.

### Multi-tenant isolation

JWT auth (login, register, refresh) is implemented in `backend/api/routes/v1/auth.py` and enforced for HTTP routes. The LangGraph thread store, however, is currently shared across users. Before exposing this to multiple tenants:

- Pass the authenticated `user_id` into every LangGraph call as part of `configurable`.
- Add access-control checks on thread and memory operations so a user cannot read another user's threads.
- Verify per-user isolation under load.

### SSRF in `fetch_url`

The agent's `fetch_url` tool lets the LLM request arbitrary URLs. Current safeguards:

- Only `http` and `https` schemes are accepted.
- Per-request timeout (15 to 20 seconds).
- Response size limit (8000 characters).

Gaps that need closing for production:

- No private IP-range blocking (RFC1918, loopback, link-local, AWS IMDS at 169.254.169.254).
- Redirects are followed without re-validation.

The simplest fix for a hostile environment is to send all egress through a forward proxy that blocks private ranges.

### Secrets management

- `.env`, `.env.*`, and similar files are excluded by `.gitignore`. Verified: no `.env` is tracked.
- API keys belong in environment variables or a secrets manager (Vault, AWS Secrets Manager, GCP Secret Manager), not in source.
- Rotate keys if a developer leaves the project or a workstation is compromised.
- For Docker deployments, prefer Docker secrets or mounted volumes over baking values into images.

### WebSocket security

- Use `wss://` in production. Configure TLS on nginx or your load balancer.
- Origin-header validation is implemented in `voice.py`.
- Per-IP rate limiting is enabled (default 25 requests per minute, configurable).
- The `verify_api_key` middleware enforces token-based auth when `API_KEY` is set.

Open items:

- The optional API key is read from a query parameter (`?token=...`), which can leak into logs. A header- or message-based handshake is preferred for production.
- There is no per-connection idle timeout. Five minutes is a reasonable default to add at the nginx layer.

### Audio data privacy

Voice recordings contain biometric information. Today:

- Voice-cloning reference audio is staged under `/tmp` with default permissions.
- There is no encryption at rest for staged audio.
- There is no audit log for voice-cloning requests.
- Files are deleted automatically on success but may linger after errors.

For deployment:

- Use `tempfile.NamedTemporaryFile(mode="wb", delete=True)` with restricted permissions.
- Add a consent step before voice cloning runs.
- Log all biometric operations (request id, user id, timestamp).
- Encrypt at rest if you retain reference audio for any reason.

### Dependency vulnerabilities

- Run `pip audit` (or `uv pip audit`) and `npm audit` regularly. CI integration is recommended.
- Enable Dependabot alerts on the GitHub repository.
- Pin dependency versions in production via `uv.lock` and `package-lock.json`.

The maintainers aim to patch critical vulnerabilities within 24 hours, high within a week, and medium or low in the next regular release.

## Deployment checklist

Before exposing a deployment to the internet:

- [ ] Rotate every key copied from a `.env.example` template.
- [ ] Set a strong, randomly generated `POSTGRES_PASSWORD` (32 or more characters).
- [ ] Set a secure `API_KEY` for backend authentication.
- [ ] Generate a fresh `SECRET_KEY` (`python -c 'import secrets; print(secrets.token_urlsafe(32))'`).
- [ ] Enable HTTPS and TLS (Let's Encrypt or a corporate CA).
- [ ] Set `ENVIRONMENT=production` and `DEBUG=false`.
- [ ] Configure `CORS_ORIGINS` to specific domains. No wildcards.
- [ ] Plumb authenticated `user_id` into every LangGraph call.
- [ ] Restrict database access via VPC or firewall rules.
- [ ] Enable audit logging for sensitive operations (login, voice cloning, memory writes).
- [ ] Run `pip audit` and `npm audit` in CI.
- [ ] Set up monitoring and alerting (Sentry, Datadog, or similar).
- [ ] Implement per-user rate limits, not only per-IP.
- [ ] Test SSRF, CSRF, and XSS in your deployment environment.
- [ ] Review every third-party MCP server before enabling it (`agent/mcp.json`).

## Acknowledgments

Researchers who report responsibly will be listed here once disclosure cycles complete.

## References

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [OWASP Top 10 for LLM Applications](https://owasp.org/www-project-top-10-for-large-language-model-applications/)
- [CWE/SANS Top 25](https://cwe.mitre.org/top25/)
- [Web Security Academy](https://portswigger.net/web-security)

Last updated: 2026-05-08.
