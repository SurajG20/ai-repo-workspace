from __future__ import annotations

import os
import shutil

import git
import structlog

from ..main import app

logger = structlog.get_logger(__name__)


@app.task(name="clone_repository", bind=True, max_retries=3)
def clone_repository(self, clone_url: str, local_path: str, access_token: str = "") -> dict:
    logger.info("cloning_repository", url=clone_url, path=local_path)
    try:
        if os.path.exists(local_path):
            shutil.rmtree(local_path)

        authenticated_url = clone_url
        if access_token and "github.com" in clone_url:
            authenticated_url = clone_url.replace(
                "https://", f"https://x-access-token:{access_token}@"
            )

        repo = git.Repo.clone_from(authenticated_url, local_path, depth=1)
        head_sha = repo.head.commit.hexsha
        logger.info("clone_complete", sha=head_sha)
        return {"status": "completed", "sha": head_sha, "path": local_path}
    except Exception as e:
        logger.error("clone_failed", error=str(e))
        raise self.retry(exc=e)


@app.task(name="create_snapshot", bind=True, max_retries=2)
def create_snapshot(self, local_path: str, repository_id: str) -> dict:
    logger.info("creating_snapshot", repo_id=repository_id)
    try:
        repo = git.Repo(local_path, search_parent_directories=True)
        head_sha = repo.head.commit.hexsha
        try:
            branch = repo.active_branch.name
        except (TypeError, ValueError):
            branch = repo.head.commit.hexsha[:12]

        file_count = 0
        total_size = 0
        for root, _, files in os.walk(local_path):
            for f in files:
                if ".git" in root:
                    continue
                file_count += 1
                try:
                    total_size += os.path.getsize(os.path.join(root, f))
                except OSError:
                    pass

        return {
            "status": "completed",
            "commit_sha": head_sha,
            "branch": branch,
            "file_count": file_count,
            "total_size_bytes": total_size,
        }
    except Exception as e:
        logger.error("snapshot_failed", error=str(e))
        raise self.retry(exc=e)
