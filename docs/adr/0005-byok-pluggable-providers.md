# BYOK pluggable AI providers

The platform must work with zero AI spend (pure deterministic retrieval), with local models (Ollama), or with commercial APIs (OpenAI, Anthropic) — using the user's own keys, never a hosted proxy. All LLM access goes through one provider abstraction; the Q&A pipeline degrades to retrieval-only when no provider is configured.

## Considered Options

- **Bundled API proxy with margin** (SaaS-style): rejected — contradicts self-hosted positioning, adds key custody liability.
- **Single hardcoded provider**: rejected — locks local/offline users out and couples core value to an external vendor.
- **Provider interface + BYOK config** (`LLM_PROVIDER`, `*_API_KEY`, Ollama base URL): chosen.

## Consequences

- Every LLM-consuming feature must define its no-provider behaviour up front; "degrade to retrieval" is a contract, not an error path.
- Provider-specific quirks (system prompts, token limits) are absorbed by the prompts package (`packages/prompts`), not scattered across call sites.
- No telemetry about prompt content leaves the deployment unless the user configures a cloud provider themselves.
