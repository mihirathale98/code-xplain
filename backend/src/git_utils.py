from typing import List, Dict, Optional
import requests
from datetime import datetime
import re

class GitHubAPI:
    def __init__(self, token: Optional[str] = None, base_url: str = "https://api.github.com"):
        """Initialize GitHub API client"""
        self.base_url = base_url
        self.headers = {
            "Accept": "application/vnd.github.v3+json"
        }
        if token:
            self.headers["Authorization"] = f"token {token}"

    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """Make a request to GitHub API"""
        url = f"{self.base_url}{endpoint}"
        response = requests.get(url, headers=self.headers, params=params)
        response.raise_for_status()
        return response.json()

    def get_repo_info(self, owner: str, repo: str) -> Dict:
        """Get repository information"""
        return self._make_request(f"/repos/{owner}/{repo}")

    def get_issues(self, owner: str, repo: str, state: str = "all", labels: Optional[List[str]] = None) -> List[Dict]:
        """Get issues for a repository"""
        params = {"state": state}
        if labels:
            params["labels"] = ",".join(labels)
        return self._make_request(f"/repos/{owner}/{repo}/issues", params=params)

    def get_pull_requests(self, owner: str, repo: str, state: str = "all") -> List[Dict]:
        """Get pull requests for a repository"""
        params = {"state": state}
        return self._make_request(f"/repos/{owner}/{repo}/pulls", params=params)

    def search_issues(self, query: str, owner: str, repo: str) -> List[Dict]:
        """Search issues and PRs using GitHub's search API"""
        # Clean up the query to be more search-friendly
        clean_query = ' '.join(query.split())  # Remove extra whitespace
        search_query = f"repo:{owner}/{repo} {clean_query}"
        params = {"q": search_query}
        response = self._make_request("/search/issues", params=params)
        # GitHub search API returns items in a 'items' field
        return response.get('items', [])

    def get_issue_comments(self, owner: str, repo: str, issue_number: int) -> List[Dict]:
        """Get comments for a specific issue"""
        return self._make_request(f"/repos/{owner}/{repo}/issues/{issue_number}/comments")

    def get_pr_reviews(self, owner: str, repo: str, pr_number: int) -> List[Dict]:
        """Get reviews for a specific pull request"""
        return self._make_request(f"/repos/{owner}/{repo}/pulls/{pr_number}/reviews")

class GitUtils:
    def __init__(self, token: Optional[str] = None):
        """Initialize Git utilities"""
        self.github = GitHubAPI(token=token)
        self.repo_cache = {}

    def parse_repo_url(self, repo_url: str) -> tuple[str, str]:
        """Parse GitHub repository URL to get owner and repo name"""
        # Handle different URL formats
        patterns = [
            r"github\.com[:/]([^/]+)/([^/]+?)(?:\.git)?$",  # https://github.com/owner/repo.git
            r"git@github\.com:([^/]+)/([^/]+?)(?:\.git)?$"  # git@github.com:owner/repo.git
        ]
        
        for pattern in patterns:
            match = re.search(pattern, repo_url)
            if match:
                owner = match.group(1)
                repo = match.group(2)
                # Remove .git extension if present
                if repo.endswith('.git'):
                    repo = repo[:-4]
                return owner, repo
        
        raise ValueError(f"Invalid GitHub repository URL: {repo_url}")

    def get_repo_metadata(self, repo_url: str) -> Dict:
        """Get repository metadata including issues and PRs"""
        if repo_url in self.repo_cache:
            return self.repo_cache[repo_url]

        owner, repo = self.parse_repo_url(repo_url)
        
        # Get repository info
        repo_info = self.github.get_repo_info(owner, repo)
        
        # Get issues and PRs
        issues = self.github.get_issues(owner, repo)
        prs = self.github.get_pull_requests(owner, repo)
        
        # Combine and cache the data
        metadata = {
            "repo_info": repo_info,
            "issues": issues,
            "pull_requests": prs,
            "last_updated": datetime.now().isoformat()
        }
        
        self.repo_cache[repo_url] = metadata
        return metadata

    def search_related_issues(self, repo_url: str, query: str) -> List[Dict]:
        """Search for issues and PRs related to a specific query"""
        owner, repo = self.parse_repo_url(repo_url)
        return self.github.search_issues(query, owner, repo)

    def get_issue_details(self, repo_url: str, issue_number: int) -> Dict:
        """Get detailed information about a specific issue"""
        owner, repo = self.parse_repo_url(repo_url)
        
        # Get issue details
        issue = self.github.get_issues(owner, repo, state="all")
        issue = next((i for i in issue if i["number"] == issue_number), None)
        
        if not issue:
            raise ValueError(f"Issue #{issue_number} not found")
        
        # Get comments
        comments = self.github.get_issue_comments(owner, repo, issue_number)
        
        # If it's a PR, get reviews
        if "pull_request" in issue:
            reviews = self.github.get_pr_reviews(owner, repo, issue_number)
        else:
            reviews = []
        
        return {
            "issue": issue,
            "comments": comments,
            "reviews": reviews
        }

    def find_similar_issues(self, repo_url: str, title: str, body: str) -> List[Dict]:
        """Find similar issues based on title and body content"""
        # Combine title and body for search
        search_query = f"{title} {body}"
        return self.search_related_issues(repo_url, search_query) 