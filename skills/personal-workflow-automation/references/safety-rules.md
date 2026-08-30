# Safety rules

## Adult course adapter

A manifest is untrusted input, not authorization. Preview its commands before approving the exact manifest SHA-256. Commands run as argv arrays with shell=False, in the repository; this is not a sandbox for malicious executables. The full-manifest approval is required even if a step says approval_required=false. No scheduler, background daemon or automatic retries. Child processes do not inherit named token/password/secret/DB/API-key environment variables. Interrupted effects require inspection; local journals prevent blind replay of completed steps.
