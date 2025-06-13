from typing import List, Dict, Optional
import requests
from datetime import datetime
import re
import logging

logger = logging.getLogger(__name__)

class GitHubAPI:
    def __init__(self, token: Optional[str] = None, base_url: str = "https://api.github.com"):
        """Initialize GitHub API client"""
        self.base_url = base_url
        self.headers = {
            "Accept": "application/vnd.github.v3+json"
        }
        if token:
            self.headers["Authorization"] = f"token {token}"
            logger.info("GitHub API initialized with authentication token")
        else:
            logger.warning("GitHub API initialized without authentication token - rate limits will apply")

    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """Make a request to GitHub API"""
        url = f"{self.base_url}{endpoint}"
        logger.debug(f"Making request to: {url}")
        
        try:
            response = requests.get(url, headers=self.headers, params=params)
            
            # Log rate limit information
            if 'X-RateLimit-Remaining' in response.headers:
                remaining = response.headers['X-RateLimit-Remaining']
                logger.debug(f"GitHub API rate limit remaining: {remaining}")
            
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if response.status_code == 403:
                logger.error("GitHub API rate limit exceeded or access forbidden")
                raise Exception("GitHub API rate limit exceeded. Please add a GitHub token or wait.")
            elif response.status_code == 404:
                logger.error(f"GitHub resource not found: {url}")
                raise Exception(f"GitHub resource not found: {endpoint}")
            else:
                logger.error(f"GitHub API error {response.status_code}: {response.text}")
                raise Exception(f"GitHub API error: {response.status_code}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error: {str(e)}")
            raise Exception(f"Network error accessing GitHub API: {str(e)}")

    def get_repo_info(self, owner: str, repo: str) -> Dict:
        """Get repository information"""
        logger.info(f"Getting repository info for {owner}/{repo}")
        return self._make_request(f"/repos/{owner}/{repo}")

    def get_issues(self, owner: str, repo: str, state: str = "all", labels: Optional[List[str]] = None) -> List[Dict]:
        """Get issues for a repository"""
        logger.info(f"Getting issues for {owner}/{repo}")
        params = {"state": state, "per_page": 100}  # Increase per_page for more results
        if labels:
            params["labels"] = ",".join(labels)
        return self._make_request(f"/repos/{owner}/{repo}/issues", params=params)

    def get_pull_requests(self, owner: str, repo: str, state: str = "all") -> List[Dict]:
        """Get pull requests for a repository"""
        logger.info(f"Getting pull requests for {owner}/{repo}")
        params = {"state": state, "per_page": 100}  # Increase per_page for more results
        return self._make_request(f"/repos/{owner}/{repo}/pulls", params=params)

    def search_issues(self, query: str, owner: str, repo: str) -> List[Dict]:
        """Search issues and PRs using GitHub's search API"""
        logger.info(f"Searching issues in {owner}/{repo} with query: {query}")
        
        # Clean up the query to be more search-friendly
        clean_query = ' '.join(query.split())  # Remove extra whitespace
        
        # Create multiple search strategies
        search_queries = [
            f"repo:{owner}/{repo} {clean_query}",
            f"repo:{owner}/{repo} in:title {clean_query}",
            f"repo:{owner}/{repo} in:body {clean_query}",
        ]
        
        all_results = []
        seen_numbers = set()
        
        for search_query in search_queries:
            try:
                logger.debug(f"Trying search query: {search_query}")
                params = {"q": search_query, "per_page": 50}
                response = self._make_request("/search/issues", params=params)
                
                # GitHub search API returns items in a 'items' field
                items = response.get('items', [])
                logger.debug(f"Found {len(items)} results for query: {search_query}")
                
                # Add unique results
                for item in items:
                    if item.get('number') not in seen_numbers:
                        all_results.append(item)
                        seen_numbers.add(item.get('number'))
                        
            except Exception as e:
                logger.warning(f"Search query failed: {search_query}, error: {str(e)}")
                continue
        
        logger.info(f"Total unique issues found: {len(all_results)}")
        return all_results

    def get_issue_comments(self, owner: str, repo: str, issue_number: int) -> List[Dict]:
        """Get comments for a specific issue"""
        logger.info(f"Getting comments for issue #{issue_number} in {owner}/{repo}")
        return self._make_request(f"/repos/{owner}/{repo}/issues/{issue_number}/comments")

    def get_pr_reviews(self, owner: str, repo: str, pr_number: int) -> List[Dict]:
        """Get reviews for a specific pull request"""
        logger.info(f"Getting reviews for PR #{pr_number} in {owner}/{repo}")
        return self._make_request(f"/repos/{owner}/{repo}/pulls/{pr_number}/reviews")

class GitUtils:
    def __init__(self, token: Optional[str] = None):
        """Initialize Git utilities"""
        self.github = GitHubAPI(token=token)
        self.repo_cache = {}

    def parse_repo_url(self, repo_url: str) -> tuple[str, str]:
        """Parse GitHub repository URL to get owner and repo name"""
        logger.debug(f"Parsing repository URL: {repo_url}")
        
        # Handle different URL formats
        patterns = [
            r"github\.com[:/]([^/]+)/([^/]+?)(?:\.git)?/?$",  # https://github.com/owner/repo.git
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
                logger.debug(f"Parsed as owner: {owner}, repo: {repo}")
                return owner, repo
        
        raise ValueError(f"Invalid GitHub repository URL: {repo_url}")

    def get_repo_metadata(self, repo_url: str) -> Dict:
        """Get repository metadata including issues and PRs"""
        if repo_url in self.repo_cache:
            logger.info(f"Using cached metadata for {repo_url}")
            return self.repo_cache[repo_url]

        owner, repo = self.parse_repo_url(repo_url)
        
        try:
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
            logger.info(f"Cached metadata for {repo_url}")
            return metadata
        except Exception as e:
            logger.error(f"Failed to get repository metadata: {str(e)}")
            raise

    def search_related_issues(self, repo_url: str, query: str) -> List[Dict]:
        """Search for issues and PRs related to a specific query"""
        owner, repo = self.parse_repo_url(repo_url)
        return self.github.search_issues(query, owner, repo)

    def get_issue_details(self, repo_url: str, issue_number: int) -> Dict:
        """Get detailed information about a specific issue"""
        owner, repo = self.parse_repo_url(repo_url)
        
        try:
            # Get issue details
            issues = self.github.get_issues(owner, repo, state="all")
            issue = next((i for i in issues if i["number"] == issue_number), None)
            
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
        except Exception as e:
            logger.error(f"Failed to get issue details: {str(e)}")
            raise

    def find_similar_issues(self, repo_url: str, title: str, body: str) -> List[Dict]:
        """Find similar issues based on title and body content"""
        # Combine title and body for search
        search_query = f"{title} {body}"
        return self.search_related_issues(repo_url, search_query) 