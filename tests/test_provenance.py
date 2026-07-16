import json
import multiprocessing
from pathlib import Path

import pytest

from src.provenance import AuditIntegrityError, AuditStore


def append_audit_event(directory: str, index: int) -> None:
    AuditStore(Path(directory)).append({"event_type": "concurrent", "index": index})


def test_audit_records_are_hash_chained(tmp_path: Path) -> None:
    store = AuditStore(tmp_path)
    first = store.append({"event_type": "first"})
    second = store.append({"event_type": "second"})
    assert first.sequence == 1
    assert second.sequence == 2
    assert first.previous_record_sha256 is None
    assert second.previous_record_sha256 == first.record_sha256
    assert store.verify_chain() == second.record_sha256


def test_audit_tampering_is_detected(tmp_path: Path) -> None:
    store = AuditStore(tmp_path)
    store.append({"event_type": "first"})
    record = next(tmp_path.glob("*.json"))
    payload = json.loads(record.read_text())
    payload["event"]["event_type"] = "altered"
    record.write_text(json.dumps(payload))
    with pytest.raises(AuditIntegrityError, match="digest mismatch"):
        store.verify_chain()


def test_audit_tail_truncation_is_detected_by_persisted_head(tmp_path: Path) -> None:
    store = AuditStore(tmp_path)
    store.append({"event_type": "first"})
    second = store.append({"event_type": "second"})
    record = next(tmp_path.glob(f"*_{second.record_sha256}.json"))
    record.unlink()

    with pytest.raises(AuditIntegrityError, match="head does not match"):
        store.verify_chain()


def test_audit_sequence_does_not_depend_on_wall_clock(tmp_path: Path) -> None:
    store = AuditStore(tmp_path)
    for index in range(3):
        store.append({"event_type": "ordered", "index": index})

    assert [path.name.split("_", maxsplit=1)[0] for path in sorted(tmp_path.glob("*.json"))] == [
        "00000000000000000001",
        "00000000000000000002",
        "00000000000000000003",
    ]


def test_audit_appends_are_serialized_across_processes(tmp_path: Path) -> None:
    context = multiprocessing.get_context("spawn")
    processes = [
        context.Process(target=append_audit_event, args=(str(tmp_path), index))
        for index in range(4)
    ]
    for process in processes:
        process.start()
    for process in processes:
        process.join(timeout=10)
        assert process.exitcode == 0

    store = AuditStore(tmp_path)
    assert store.verify_chain() is not None
    assert len(list(tmp_path.glob("*.json"))) == 4
