# opsagent-core

OpsAgent v1.0 fail-closed enforcement loop with:

- Atomic append-only run log (`logs/RUNLOG.jsonl`) and state (`logs/RUNLOG.state.json`).
- Canonical JSON hash chain (`hash_curr = sha256(canonical_json(entry)+hash_prev)`).
- Policy binding + schema validation gate before any execution.
- Evidence capture per run under `governance-ledger/evidence/YYYY-MM/RUN-<RUN_ID>/`.
- Governance manifest seals under `governance-ledger/seals/manifests/YYYY-MM/`.

## CLI

```bash
python -m opsagent validate
python -m opsagent simulate --action unknown_action --payload examples/payload.json --actor user:alice --mode DRY_RUN
python -m opsagent run --action approve_release --payload examples/allow-payload.json --actor ceo:janedoe --mode FAIL_CLOSED
```

### Example payload files

Create `examples/payload.json`:

```json
{
  "scope": "full"
}
```

Create `examples/allow-payload.json`:

```json
{
  "change_ticket": "CHG-2026-0001"
}
```

## Windows PowerShell quick start

```powershell
py -3 -m pip install pytest
py -3 -m pytest -q
py -3 scripts/validate_policies.py
'{"scope":"full"}' | Set-Content -Path .\payload.json
py -3 -m opsagent simulate --action unknown_action --payload .\payload.json --actor user:alice --mode DRY_RUN
'{"change_ticket":"CHG-2026-0001"}' | Set-Content -Path .\allow-payload.json
py -3 -m opsagent run --action approve_release --payload .\allow-payload.json --actor ceo:janedoe --mode FAIL_CLOSED
```
