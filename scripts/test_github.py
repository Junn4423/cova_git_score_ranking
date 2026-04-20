"""
Quick smoke test for GitHub API client.
Tests public endpoints that don't require authentication.
"""

import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.github.client import GitHubClient


def test_github_client():
    """Test basic GitHub API connectivity using public endpoints."""
    client = GitHubClient(token="")  # Public access, no token needed
    
    print("=== GitHub API Smoke Test ===\n")

    # 1. Test rate limit (works without auth)
    print("1. Testing rate limit endpoint...")
    try:
        rate = client.get_rate_limit()
        remaining = rate["resources"]["core"]["remaining"]
        limit = rate["resources"]["core"]["limit"]
        print(f"   ✅ Rate limit: {remaining}/{limit}\n")
    except Exception as e:
        print(f"   ❌ Failed: {e}\n")
        return False

    # 2. Test get a public repo
    print("2. Testing get public repo (facebook/react)...")
    try:
        repo = client.get_repo("facebook/react")
        print(f"   ✅ Repo: {repo['full_name']}")
        print(f"   ⭐ Stars: {repo['stargazers_count']}")
        print(f"   📄 Default branch: {repo['default_branch']}\n")
    except Exception as e:
        print(f"   ❌ Failed: {e}\n")
        return False

    # 3. Test list commits (public)
    print("3. Testing list commits (facebook/react, last 5)...")
    try:
        commits = client.list_commits("facebook/react", max_pages=1)
        for c in commits[:5]:
            sha = c["sha"][:7]
            msg = c["commit"]["message"].split("\n")[0][:60]
            author = c["commit"]["author"]["name"]
            print(f"   [{sha}] {author}: {msg}")
        print(f"   ✅ Got {len(commits)} commits\n")
    except Exception as e:
        print(f"   ❌ Failed: {e}\n")
        return False

    # 4. Test list PRs (public)
    print("4. Testing list pull requests (facebook/react, last 3)...")
    try:
        prs = client.list_pull_requests("facebook/react", max_pages=1)
        for pr in prs[:3]:
            print(f"   PR #{pr['number']}: {pr['title'][:50]} [{pr['state']}]")
        print(f"   ✅ Got {len(prs)} PRs\n")
    except Exception as e:
        print(f"   ❌ Failed: {e}\n")
        return False

    client.close()
    print("=== All GitHub API tests passed! ===")
    return True


if __name__ == "__main__":
    success = test_github_client()
    sys.exit(0 if success else 1)
