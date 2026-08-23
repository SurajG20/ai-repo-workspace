from __future__ import annotations

import asyncio
import os
import tempfile
from datetime import UTC, datetime, timedelta

import pytest
from jobs import (
    IndexingPipeline,
    MemoryJobStore,
    RepositoryDeletedError,
    Stage,
)


class Clock:
    def __init__(self) -> None:
        self.t = datetime(2026, 1, 1, tzinfo=UTC)

    def __call__(self) -> datetime:
        return self.t

    def advance(self, **kwargs) -> None:
        self.t += timedelta(**kwargs)


def make_pipeline() -> tuple[IndexingPipeline, MemoryJobStore, str, Clock]:
    clock = Clock()
    store = MemoryJobStore(now_fn=clock)
    repo_id = store.add_repository(local_path="/repos/demo")
    return IndexingPipeline(store), store, repo_id, clock


def run(coro):
    return asyncio.run(coro)


def test_enqueue_refuses_deleted_repository():
    pipeline, store, _, _ = make_pipeline()
    deleted_id = store.add_repository(deleted=True)
    with pytest.raises(RepositoryDeletedError):
        run(pipeline.enqueue(deleted_id, Stage.CLONE))


def test_claim_of_clone_sets_repo_cloning():
    pipeline, store, repo_id, _ = make_pipeline()
    run(pipeline.enqueue(repo_id, Stage.CLONE))
    claimed = run(pipeline.claim_next("worker-1"))
    assert claimed is not None
    assert claimed.stage is Stage.CLONE
    assert claimed.repo.local_path == "/repos/demo"
    assert store.repo_status(repo_id) == "cloning"


def test_claims_are_exclusive_until_completed():
    pipeline, store, repo_id, _ = make_pipeline()
    run(pipeline.enqueue(repo_id, Stage.CLONE))
    first = run(pipeline.claim_next("worker-1"))
    second = run(pipeline.claim_next("worker-2"))
    assert first is not None
    assert second is None


def test_clone_completion_chains_parse_and_activates_repo():
    pipeline, store, repo_id, _ = make_pipeline()
    run(pipeline.enqueue(repo_id, Stage.CLONE))
    claimed = run(pipeline.claim_next("worker-1"))
    children = run(
        pipeline.complete(claimed, {"sha": "abc123", "path": "/repos/demo"})
    )
    assert [child.stage for child in children] == [Stage.PARSE]
    assert children[0].metadata["repo_path"] == "/repos/demo"
    assert store.repo_status(repo_id) == "active"


def test_snapshot_completion_inserts_snapshot_links_job_and_chains_parse():
    pipeline, store, repo_id, _ = make_pipeline()
    run(pipeline.enqueue(repo_id, Stage.SNAPSHOT))
    claimed = run(pipeline.claim_next("worker-1"))
    children = run(
        pipeline.complete(
            claimed,
            {"commit_sha": "deadbeef", "branch": "main", "file_count": 7, "total_size_bytes": 4096},
        )
    )
    assert store.snapshot_count() == 1
    assert children[0].snapshot_id == store.get_job(claimed.job_id).snapshot_id
    assert children[0].stage is Stage.PARSE
    assert children[0].parent_job_id == claimed.job_id


def test_parse_completion_fans_out_to_two_children():
    pipeline, store, repo_id, _ = make_pipeline()
    parse_job = run(pipeline.enqueue(repo_id, Stage.PARSE))
    claimed = run(pipeline.claim_next("worker-1"))
    children = run(
        pipeline.complete(claimed, {"language": "python", "symbols": [], "relationships": []})
    )
    assert [child.stage for child in children] == [Stage.GRAPH_SYNC, Stage.EMBED]
    assert all(child.parent_job_id == parse_job.id for child in children)
    assert children[0].metadata["language"] == "python"
    assert children[1].metadata == {
        "language": "python",
        "symbols": [],
        "relationships": [],
        "provider": None,
    }


def test_retry_requeues_then_exhaustion_fails_repo():
    pipeline, store, repo_id, _ = make_pipeline()
    run(pipeline.enqueue(repo_id, Stage.CLONE))

    outcome = None
    for expected_attempt in range(3):
        claimed = run(pipeline.claim_next("worker-1"))
        assert claimed.attempt == expected_attempt
        outcome = run(pipeline.fail(claimed, "clone boom"))

    assert outcome == "failed"
    assert store.get_job(claimed.job_id).status == "failed"
    assert store.repo_status(repo_id) == "error"


def test_stale_running_job_is_reclaimed_with_retry_count():
    pipeline, store, repo_id, clock = make_pipeline()
    run(pipeline.enqueue(repo_id, Stage.CLONE))
    stale_claim = run(pipeline.claim_next("worker-crashed"))
    clock.advance(minutes=20)

    reclaimed = run(pipeline.claim_next("worker-2", stale_after=timedelta(minutes=15)))

    assert reclaimed.job_id == stale_claim.job_id
    assert reclaimed.attempt == 1
    assert store.job_field(stale_claim.job_id, "retry_count") == 1


def test_legacy_started_status_is_healed_by_reclaim():
    pipeline, store, repo_id, clock = make_pipeline()
    job = run(pipeline.enqueue(repo_id, Stage.CLONE))
    row = store._jobs[job.id]
    row.status = "started"  # pre-pipeline dispatcher vocabulary
    clock.advance(hours=1)

    healed = run(pipeline.claim_next("worker-1"))

    assert healed.job_id == job.id
    assert store.get_job(job.id).status == "running"


def test_queued_jobs_of_deleted_repo_are_cancelled():
    pipeline, store, repo_id, _ = make_pipeline()
    run(pipeline.enqueue(repo_id, Stage.PARSE))
    store._repos[repo_id].deleted_at = Clock()()

    claimed = run(pipeline.claim_next("worker-1"))

    assert claimed is None
    statuses = [store.get_job(j.id).status for j in store._jobs.values()]
    assert statuses == ["cancelled"]


def test_artifact_survives_until_both_consumers_finish():
    pipeline, store, repo_id, _ = make_pipeline()
    run(pipeline.enqueue(repo_id, Stage.PARSE))
    parse_claimed = run(pipeline.claim_next("worker-1"))

    fd, artifact_path = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    try:
        with open(artifact_path, "w") as f:
            f.write("{}")

        children = run(
            pipeline.complete(
                parse_claimed, {"language": "python", "data_file": artifact_path}
            )
        )

        graph_child = next(c for c in children if c.stage is Stage.GRAPH_SYNC)
        embed_child = next(c for c in children if c.stage is Stage.EMBED)

        graph_claimed = run(pipeline.claim_next("worker-1"))
        assert graph_claimed.job_id == graph_child.id
        run(pipeline.complete(graph_claimed, {}))
        assert os.path.exists(artifact_path)

        embed_claimed = run(pipeline.claim_next("worker-1"))
        assert embed_claimed.job_id == embed_child.id
        run(pipeline.complete(embed_claimed, {}))
        assert not os.path.exists(artifact_path)
    finally:
        if os.path.exists(artifact_path):
            os.unlink(artifact_path)
