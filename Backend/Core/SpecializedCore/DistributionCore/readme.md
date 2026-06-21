# DistributionCore

The Stubvi public compiler, telemetry ingestion endpoint, and decentralized training data feed. DistributionCore implements the asymmetric out-of-tree distribution protocol that separates the private sovereign core from the public Stubvi tier.

## Responsibility

1. **Bundle Compilation**: Copy only whitelisted files to a public output directory, stripping all internal markers and verifying no private paths leaked
2. **Integrity Verification**: Scan a compiled bundle for any _PRIVATE_PATH_PATTERNS that must never appear in public distributions
3. **Telemetry Ingestion**: Receive anonymized usage packets from opt-in public Stubvi installations
4. **Telemetry Flush**: Write queued telemetry to `Data/training/telemetry/telemetry.jsonl` for offline fine-tuning

## The Stubvi Protocol

The public **Stubvi** tier is built exclusively by this module's `compile_bundle()` method:

- Only files on `_WHITELIST` are included in the output
- All `_INTERNAL_MARKERS` are replaced with `[STUBVI_REDACTED]`
- A `BUNDLE_MANIFEST.json` and `BUNDLE_MANIFEST.sha256` are generated for integrity tracking
- `verify_bundle()` scans the output against `_PRIVATE_PATH_PATTERNS` — any violation aborts deployment

**Cryptographic gate**: The SHA-256 hash of the manifest must be verified before the bundle is published. This hash is the deployment authorization token.

## Supported Actions

| Action | Description |
|---|---|
| `compile_bundle` | Build a public-safe Stubvi bundle |
| `verify_bundle` | Scan a bundle for private path leaks |
| `ingest_telemetry` | Queue an anonymized telemetry packet |
| `flush_telemetry` | Write queued packets to JSONL training file |

## PII Safety

Every telemetry packet is checked against a PII blocklist before queuing. Packets containing fields named `email`, `password`, `ip_address`, `username`, `name`, or `phone` are silently rejected.

## Key File

`DistributionCore.py` — ~280 lines

## Critical Security Rules

- **Never** add private weight paths to `_WHITELIST`
- **Never** include model checkpoint files in any bundle
- `_PRIVATE_PATH_PATTERNS` must be updated whenever new private assets are added to the project
