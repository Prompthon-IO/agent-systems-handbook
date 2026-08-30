# Safety rules

Preview approval cannot authorize production. Never create a provider project, expose a credential, bypass deployment protection, or repeat an uncertain submission automatically. Provider-owned responses can include secrets, so the client filters to an explicit metadata allowlist. API tokens go only to api.vercel.com, never the deployed app. Custom domains/redirects require manual browser verification and are not silently accepted by this helper.

Use only the authorized organization/workspace. Honor API refusal, scope mismatch, conflict and reset gates. Never persist secrets or absolute personal paths. Dry runs cannot authorize a later external action by themselves.
