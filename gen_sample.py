# gen_sample.py
import argparse
import base64
import json
import os
import re
import subprocess
import ssl
import urllib.request
import urllib.error

try:
    import certifi
    _CAFILE = certifi.where()
except ImportError:
    _CAFILE = None
from pathlib import Path

GITHUB_API = "https://api.github.com"


def try_git(cmd, default=""):
    try:
        return subprocess.check_output(
            cmd, shell=True, text=True, stderr=subprocess.DEVNULL
        ).strip()
    except Exception:
        return default


def api_get(url, token=None):
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "gh-qc-skill",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    if _CAFILE:
        ctx = ssl.create_default_context(cafile=_CAFILE)
    else:
        ctx = ssl.create_default_context()

    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30, context=ctx) as r:
        return json.loads(r.read().decode("utf-8"))


def parse_repo_url(url):
    m = re.search(r"github\.com[:/]([^/]+)/([^/.#?]+)", url)
    if not m:
        raise SystemExit(f"无法解析 GitHub URL: {url}")
    return m.group(1), m.group(2).replace(".git", "")


def from_http(repo_url, token=None):
    owner, repo = parse_repo_url(repo_url)
    repo_id = f"{owner}/{repo}"
    repo_api = f"{GITHUB_API}/repos/{repo_id}"

    info = api_get(repo_api, token)
    default_branch = info.get("default_branch", "main")
    license_info = info.get("license") or {}
    license_spdx = license_info.get("spdx_id") or None
    if license_spdx in ("NOASSERTION", "NONE"):
        license_spdx = None

    commit_info = api_get(f"{repo_api}/commits/{default_branch}", token)
    commit_sha = commit_info["sha"]
    last_commit_at = commit_info["commit"]["committer"]["date"]

    readme = ""
    try:
        rd = api_get(f"{repo_api}/readme", token)
        readme = base64.b64decode(rd["content"]).decode("utf-8", errors="ignore")
    except urllib.error.HTTPError:
        pass

    milestones = api_get(f"{repo_api}/milestones?state=all&per_page=1", token)
    if not milestones:
        raise SystemExit(f"{repo_id} 没有任何 Milestone，请先在 GitHub 上创建")

    ms = milestones[0]
    ms_number = ms["number"]
    issues_raw = api_get(
        f"{repo_api}/issues?milestone={ms_number}&state=all&per_page=100", token
    )
    issues = []
    for it in issues_raw:
        if "pull_request" in it:
            continue
        issues.append({
            "issue_id": it["id"],
            "title": it["title"],
            "body": (it.get("body") or "")[:2000],
            "state": it["state"],
            "labels": [l["name"] for l in it.get("labels", [])],
            "comments_count": it.get("comments", 0),
            "author": (it.get("user") or {}).get("login"),
            "is_bot": (it.get("user") or {}).get("type") == "Bot",
        })

    milestone = {
        "milestone_id": ms["id"],
        "repo_id": repo_id,
        "title": ms["title"],
        "description": ms.get("description") or "",
        "state": ms["state"],
        "created_at": ms.get("created_at"),
        "due_on": ms.get("due_on"),
        "closed_at": ms.get("closed_at"),
        "open_issues": ms.get("open_issues", 0),
        "closed_issues": ms.get("closed_issues", 0),
        "issues": issues,
    }

    repo_snapshot = {
        "repo_id": repo_id,
        "repo_url": f"https://github.com/{repo_id}",
        "commit_sha": commit_sha,
        "default_branch": default_branch,
        "license": license_spdx,
        "stars": info.get("stargazers_count", 0),
        "forks": info.get("forks_count", 0),
        "language": info.get("language"),
        "size_kb": info.get("size", 0),
        "is_fork": info.get("fork", False),
        "is_archived": info.get("archived", False),
        "readme": readme,
        "has_tests": False,
        "has_ci": False,
        "has_lockfile": False,
        "last_commit_at": last_commit_at,
        "contributors": 1,
    }

    return {"repo": repo_snapshot, "milestone": milestone}


def from_git(owner=None, repo=None, sha=None, license_="MIT"):
    if not owner or not repo:
        remote = try_git("git remote get-url origin")
        if remote:
            m = re.search(r"github\.com[:/](.+?)/(.+?)(?:\.git)?$", remote)
            if m:
                owner, repo = m.group(1), m.group(2)
        if not owner or not repo:
            raise SystemExit("缺少 owner/repo，请传 --owner --repo 或 --repo-url")
    if not sha:
        sha = try_git("git rev-parse HEAD")
        if not sha:
            raise SystemExit("缺少 commit SHA，请传 --sha")

    repo_id = f"{owner}/{repo}"
    readme_path = Path("README.md")
    readme = readme_path.read_text(encoding="utf-8") if readme_path.exists() else ""

    return {
        "repo": {
            "repo_id": repo_id,
            "repo_url": f"https://github.com/{repo_id}",
            "commit_sha": sha,
            "default_branch": "main",
            "license": license_,
            "stars": 1,
            "forks": 0,
            "language": "Python",
            "size_kb": 1024,
            "is_fork": False,
            "is_archived": False,
            "readme": readme,
            "has_tests": False,
            "has_ci": False,
            "has_lockfile": False,
            "last_commit_at": "2026-09-21T00:00:00Z",
            "contributors": 1,
        },
        "milestone": {
            "milestone_id": 1,
            "repo_id": repo_id,
            "title": "v1.0 初始版本",
            "description": "完成质检流水线基础功能。",
            "state": "open",
            "open_issues": 0,
            "closed_issues": 3,
            "issues": [
                {
                    "issue_id": 101,
                    "title": "实现准入规则",
                    "body": "实现 license、fork、敏感信息等准入检查。",
                    "state": "closed",
                    "labels": ["feature"],
                    "comments_count": 0,
                    "author": owner,
                },
            ],
        },
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--repo-url", help="GitHub 仓库 URL，例如 https://github.com/owner/repo")
    p.add_argument("--owner")
    p.add_argument("--repo")
    p.add_argument("--sha")
    p.add_argument("--license", default="MIT")
    p.add_argument("--out", default="examples/sample.json")
    p.add_argument("--token", default=os.environ.get("GITHUB_TOKEN", ""))
    args = p.parse_args()

    if args.repo_url:
        sample = from_http(args.repo_url, token=args.token or None)
    else:
        sample = from_git(args.owner, args.repo, args.sha, args.license)

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(
        json.dumps(sample, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"已生成 {args.out}")
    print(f"  repo_id = {sample['repo']['repo_id']}")
    print(f"  commit  = {sample['repo']['commit_sha']}")
    print(f"  ms      = {sample['milestone']['title']}")


if __name__ == "__main__":
    main()