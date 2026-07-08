---
name: Pull Request
about: Submit a change to Vibhu-Oska AI-OS
---

## Summary
<!-- One-line description of what this PR does. -->

## Type of change

- [ ] `fix` — bug fix (non-breaking)
- [ ] `feat` — new feature
- [ ] `refactor` — restructuring without feature change
- [ ] `perf` — performance improvement
- [ ] `test` — test additions or corrections
- [ ] `docs` — documentation update
- [ ] `chore` — build/tooling/CI change

## What changed?

| File / Module | Change description |
|---|---|
| `Backend/...` | |
| `Models/...` | |
| `Frontend/...` | |
| `Tests/...` | |

## Testing

- [ ] All existing tests pass (`python -m pytest Tests/ -q`)
- [ ] New tests added for changed behaviour
- [ ] Manually tested via WebSocket / dashboard
- [ ] Tested on CPU-only fallback path (BackupCore)
- [ ] Tested with Sovereign GPT checkpoint (if applicable)

## Checklist

- [ ] Code follows Vibhu-Oska module boundary rules (no cross-core logic leakage)
- [ ] No external API calls introduced (zero cloud dependency policy)
- [ ] No `sys.path.append` workarounds (absolute imports only)
- [ ] Docstrings updated for changed functions
- [ ] `.env.example` updated if new env vars were added
- [ ] `CHANGELOG.md` updated (if applicable)

## Related issues
Closes # <!-- issue number -->

## Screenshots / recordings
<!-- Attach UI screenshots or terminal output if relevant. -->
