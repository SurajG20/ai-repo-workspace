# GitHub OAuth as the only identity provider

The product ingests GitHub repositories, so the source of code and the source of identity are the same system. We support exactly one auth provider: GitHub OAuth, with the resulting token Fernet-encrypted at rest and exchanged for a short-lived first-party JWT. A `/auth/dev/login` endpoint exists solely for local/self-hosted use without OAuth credentials.

## Considered Options

- **Email/password + repository token entry**: rejected — two credential systems to secure, worse UX, and tokens pasted into settings rot silently.
- **Multiple OAuth providers (GitLab, Bitbucket)**: deferred until ingestion supports those forges; identity follows ingestion targets, not the reverse.
- **GitHub-only OAuth + dev login**: chosen.

## Consequences

- Users without GitHub cannot authenticate in production mode; this is accepted scope, not a gap.
- The dev login endpoint is a convenience, not a backdoor: it creates local-scoped users with no GitHub token and no forge access.
- JWT issuance/verification stays in `app/core/security.py`; rotating `API_SECRET_KEY` invalidates all sessions at once.
