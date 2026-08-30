# Safety rules

Run synthetic local scenarios only. A loopback application can still mutate its own backend, so review click/form effects before testing it. The included static server denies hidden files, directory listings and symlink escapes. Screenshots may contain personal information: keep them local and inspect before any sharing. Do not bypass login or protection to make a check green.

Use only the authorized organization/workspace. Honor API refusal, scope mismatch, conflict and reset gates. Never persist secrets or absolute personal paths. Dry runs cannot authorize a later external action by themselves.
