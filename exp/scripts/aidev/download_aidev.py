from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from .common import DEFAULT_TABLES, RAW_DIR, ensure_dir, write_json


def is_readable_parquet(path: Path) -> bool:
    if not path.exists() or path.stat().st_size <= 0:
        return False
    try:
        import pyarrow.parquet as pq

        pq.ParquetFile(path).metadata
        return True
    except Exception:
        return False


def file_url(repo_id: str, filename: str) -> str:
    return f"https://huggingface.co/datasets/{repo_id}/resolve/main/{filename}"


def curl_download(repo_id: str, filename: str, output_dir: Path, force: bool = False) -> str:
    target = output_dir / filename
    if target.exists() and is_readable_parquet(target) and not force:
        return str(target)
    if force and target.exists():
        target.unlink()

    command = [
        "curl",
        "-L",
        "--fail",
        "--retry",
        "5",
        "--retry-delay",
        "2",
        "--continue-at",
        "-",
        "--output",
        str(target),
        file_url(repo_id, filename),
    ]
    subprocess.run(command, check=True)
    if not is_readable_parquet(target):
        raise RuntimeError(f"Downloaded file is not a readable parquet file: {target}")
    return str(target)


def http_download(repo_id: str, filename: str, output_dir: Path, force: bool = False) -> str:
    try:
        import requests
    except ImportError:
        print(
            "Missing dependency: requests. Install with `python -m pip install -r requirements-emse.txt`.",
            file=sys.stderr,
        )
        raise SystemExit(2)

    target = output_dir / filename
    if target.exists() and is_readable_parquet(target) and not force:
        return str(target)

    url = file_url(repo_id, filename)
    tmp_target = target.with_suffix(target.suffix + ".tmp")
    with requests.get(url, stream=True, timeout=(30, 180)) as response:
        response.raise_for_status()
        with tmp_target.open("wb") as handle:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    handle.write(chunk)
    tmp_target.replace(target)
    return str(target)


def main() -> None:
    parser = argparse.ArgumentParser(description="Download selected AIDev tables from Hugging Face.")
    parser.add_argument("--repo-id", default="hao-li/AIDev")
    parser.add_argument("--output-dir", type=Path, default=RAW_DIR)
    parser.add_argument("--all", action="store_true", help="Download the full dataset snapshot instead of selected tables.")
    parser.add_argument(
        "--method",
        choices=["curl", "http", "hf", "snapshot"],
        default="curl",
        help="Download method. Default curl supports resumable downloads and avoids Hugging Face Xet client hangs.",
    )
    parser.add_argument("--force", action="store_true", help="Redownload files even if they already exist.")
    parser.add_argument("--tables", nargs="*", default=DEFAULT_TABLES, help="Table names to include when not using --all.")
    args = parser.parse_args()

    output_dir = ensure_dir(args.output_dir)
    allow_patterns = None
    if not args.all:
        allow_patterns = []
        for table in args.tables:
            allow_patterns.extend([f"*{table}*", f"**/{table}*", f"**/{table}/**"])

    downloaded: list[str] = []
    if args.method in {"curl", "http"}:
        filenames = None
        if args.all:
            filenames = [
                "all_pull_request.parquet",
                "all_repository.parquet",
                "all_user.parquet",
                "human_pr_task_type.parquet",
                "human_pull_request.parquet",
                "issue.parquet",
                "pr_comments.parquet",
                "pr_commit_details.parquet",
                "pr_commits.parquet",
                "pr_review_comments.parquet",
                "pr_review_comments_v2.parquet",
                "pr_reviews.parquet",
                "pr_task_type.parquet",
                "pr_timeline.parquet",
                "pull_request.parquet",
                "related_issue.parquet",
                "repository.parquet",
                "user.parquet",
            ]
        else:
            filenames = [f"{table}.parquet" for table in args.tables]
        for filename in filenames:
            if args.method == "curl":
                local_file = curl_download(args.repo_id, filename, output_dir, force=args.force)
            else:
                local_file = http_download(args.repo_id, filename, output_dir, force=args.force)
            downloaded.append(local_file)
            print(f"downloaded: {filename}")
        local_path = str(output_dir)
    else:
        try:
            from huggingface_hub import hf_hub_download, list_repo_files, snapshot_download
        except ImportError:
            print(
                "Missing dependency: huggingface_hub. Install with `python -m pip install -r requirements-emse.txt`.",
                file=sys.stderr,
            )
            raise SystemExit(2)

    if args.method == "snapshot":
        local_path = snapshot_download(
            repo_id=args.repo_id,
            repo_type="dataset",
            local_dir=str(output_dir),
            allow_patterns=allow_patterns,
        )
        downloaded.append(local_path)
    elif args.method == "hf":
        repo_files = list_repo_files(args.repo_id, repo_type="dataset")
        wanted = repo_files if args.all else [path for path in repo_files if any(path.endswith(f"{table}.parquet") for table in args.tables)]
        for filename in wanted:
            local_file = hf_hub_download(
                repo_id=args.repo_id,
                repo_type="dataset",
                filename=filename,
                local_dir=str(output_dir),
            )
            downloaded.append(local_file)
            print(f"downloaded: {filename}")
        local_path = str(output_dir)
    payload = {
        "repo_id": args.repo_id,
        "output_dir": str(output_dir),
        "local_path": local_path,
        "tables": "all" if args.all else args.tables,
        "method": args.method,
        "downloaded": downloaded,
    }
    write_json(output_dir.parent / "download_manifest.json", payload)
    print(f"AIDev download complete: {local_path}")


if __name__ == "__main__":
    main()
