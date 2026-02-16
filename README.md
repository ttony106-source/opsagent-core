# opsagent-core

Execution engine, CLI, atomic run-log writer, hash chain, and evidence capture.

## Repository baseline

This repository is bootstrapped with three foundational domains:

- `opsagent-core/` - execution/runtime artifacts and run-log schema
- `automation-policies/` - policy definitions and policy schema
- `governance-ledger/` - governance approval ledger and ledger-entry schema

A fail-closed policy validation gate runs in CI via `.github/workflows/policy-validation.yml`.
