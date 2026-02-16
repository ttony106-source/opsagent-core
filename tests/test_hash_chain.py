from __future__ import annotations

from opsagent.hashing import chained_entry_hash


def test_hash_chain_correctness() -> None:
    entry_one = {"run_id": "000001", "action": "a"}
    first_hash = chained_entry_hash(entry_one, "GENESIS")

    entry_two = {"run_id": "000002", "action": "b", "hash_prev": first_hash}
    second_hash = chained_entry_hash(entry_two, first_hash)

    assert len(first_hash) == 64
    assert len(second_hash) == 64
    assert first_hash != second_hash
