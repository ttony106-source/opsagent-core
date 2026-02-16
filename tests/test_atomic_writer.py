from __future__ import annotations

from pathlib import Path

from opsagent.runlog import atomic_write_text


def test_atomic_writer_uses_temp_then_rename(monkeypatch, tmp_path: Path) -> None:
    dest = tmp_path / "RUNLOG.jsonl"
    calls: list[tuple[Path, Path]] = []

    def fake_replace(src: str | Path, dst: str | Path) -> None:
        src_path = Path(src)
        dst_path = Path(dst)
        calls.append((src_path, dst_path))
        src_path.rename(dst_path)

    monkeypatch.setattr("opsagent.runlog.os.replace", fake_replace)
    atomic_write_text(dest, "line\n")

    assert dest.read_text(encoding="utf-8") == "line\n"
    assert len(calls) == 1
    src, dst = calls[0]
    assert src.suffix == ".tmp"
    assert dst == dest
