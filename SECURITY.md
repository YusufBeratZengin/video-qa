# Security policy

## Supported versions

Security fixes currently target the latest 0.1.x release.

## Reporting a vulnerability

Use GitHub's private vulnerability reporting if enabled:
[Report a vulnerability](https://github.com/YusufBeratZengin/video-qa/security/advisories/new).
If that channel is unavailable, open a minimal issue requesting a private
reporting channel. Do not post exploit details, credentials, personal data, or
private media in public issues. No response-time guarantee is offered.

## Local media processing

video-qa invokes installed FFmpeg/ffprobe binaries without a shell. It restricts
input protocols to local files and pipes and uses a timeout for each subprocess.
It does not upload media or invoke remote analysis services. Reports include
file paths and decoder diagnostics; review them before sharing.

Media parsers are complex native software. Keep FFmpeg and Python updated, and
process untrusted media in an isolated environment with appropriate CPU, memory,
filesystem, and runtime limits. The quality gate itself is not a security sandbox
or a malware scanner. Local media manifests can still reference other local
files. Do not run it with elevated privileges or arbitrary binary paths supplied
by untrusted callers.
