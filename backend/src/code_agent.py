import json
import csv
import re
from typing import List, Dict, Optional, Tuple
from pydantic import BaseModel
import os
from llm_api import LLMApi
from code_parser import analyze_repo
from git_utils import GitUtils

class CodeSearchResult(BaseModel):
    """Model for code search results"""
    file_path: str
    code: str
    imports: List[str]
    used_by: List[str]

class CodeAgent:
    def __init__(self, llm_provider: str, api_key: Optional[str] = None, github_token: Optional[str] = None):
        """Initialize the code agent with LLM API and tools"""
        self.llm = LLMApi(provider=llm_provider, api_key=api_key)
        self.git = GitUtils(token=github_token)
        self.file_structure = {}
        self.usage_lookup = {}
        self.code_data = {}
        self.current_repo_url = None

    def _extract_json(self, text: str) -> Tuple[Dict, str]:
        """Extract JSON from text using regex and return both the JSON and remaining text"""
        # Pattern to match JSON object between triple backticks
        json_pattern = r"```json\s*(\{[\s\S]*?\})\s*```"
        # Pattern to match JSON object without backticks
        fallback_pattern = r"(\{[\s\S]*?\})"
        
        # Try to find JSON with backticks first
        match = re.search(json_pattern, text)
        if match:
            try:
                json_data = json.loads(match.group(1))
                remaining_text = text[:match.start()] + text[match.end():]
                return json_data, remaining_text.strip()
            except json.JSONDecodeError:
                pass
        
        # If no match or invalid JSON, try without backticks
        match = re.search(fallback_pattern, text)
        if match:
            try:
                json_data = json.loads(match.group(1))
                remaining_text = text[:match.start()] + text[match.end():]
                return json_data, remaining_text.strip()
            except json.JSONDecodeError:
                pass
        
        return {}, text

    def read_file_structure(self) -> Dict:
        """Read and return the complete file structure of the codebase"""
        return {
            "file_structure": self.file_structure,
            "total_files": len(self.file_structure),
            "file_types": {
                "python": len([f for f in self.file_structure.keys() if f.endswith('.py')]),
                "other": len([f for f in self.file_structure.keys() if not f.endswith('.py')])
            }
        }

    def fetch_code(self, file_path: str) -> Dict:
        """Fetch code content for a specific file"""
        if file_path not in self.code_data:
            return {"error": f"File {file_path} not found"}
        
        return {
            "file_path": file_path,
            "code": self.code_data[file_path],
            "imports": self.file_structure.get(file_path, {}).get('imports', []),
            "used_by": self.file_structure.get(file_path, {}).get('used_by', [])
        }

    def find_code_usage(self, file_path: str) -> Dict:
        """Find all usages and dependencies of a specific file"""
        if file_path not in self.usage_lookup:
            return {"error": f"File {file_path} not found in usage lookup"}
        
        return {
            "file_path": file_path,
            "imports": self.file_structure.get(file_path, {}).get('imports', []),
            "used_by": self.usage_lookup[file_path],
            "total_dependencies": len(self.file_structure.get(file_path, {}).get('imports', [])),
            "total_dependents": len(self.usage_lookup[file_path])
        }

    def search_related_issues(self, query: str) -> Dict:
        """Search for issues and PRs related to the query"""
        if not self.current_repo_url:
            return {"error": "No repository loaded"}
        
        try:
            issues = self.git.search_related_issues(self.current_repo_url, query)
            return {
                "total_results": len(issues),
                "issues": issues[:5],  # Return top 5 results
                "query": query
            }
        except Exception as e:
            return {"error": str(e)}

    def get_issue_details(self, issue_number: int) -> Dict:
        """Get detailed information about a specific issue"""
        if not self.current_repo_url:
            return {"error": "No repository loaded"}
        
        try:
            return self.git.get_issue_details(self.current_repo_url, issue_number)
        except Exception as e:
            return {"error": str(e)}

    def load_repo_data(self, repo_url: str):
        """Load repository data using code_parser and git utilities"""
        self.current_repo_url = repo_url
        self.file_structure, csv_str, self.usage_lookup = analyze_repo(repo_url)
        
        # Parse CSV data
        csv_reader = csv.DictReader(csv_str.splitlines())
        self.code_data = {row['relative_path']: row['code'] for row in csv_reader}
        
        # Load repository metadata
        try:
            self.git.get_repo_metadata(repo_url)
        except Exception as e:
            print(f"Warning: Could not load repository metadata: {e}")

    def analyze_code(self, query: str) -> str:
        """Analyze code based on user query"""
        messages = [
            {"role": "system", "content": "You are a code analysis expert."},
            {"role": "user", "content": query}
        ]
        return self.llm.chat(messages=messages)

    def run(self, query: str) -> str:
        """Run the agent with a query"""
        print("\n=== Starting Analysis ===")
        print(f"Query: {query}")
        
        # First, get the file structure
        print("\n=== Tool: read_file_structure ===")
        file_structure = self.read_file_structure()
        print(f"Found {len(file_structure['file_structure'])} files")
        print(f"Python files: {file_structure['file_types']['python']}")
        print(f"Other files: {file_structure['file_types']['other']}")
        
        # Check if query is about issues or PRs
        if any(keyword in query.lower() for keyword in ['issue', 'bug', 'pr', 'pull request', 'feature request']):
            print("\n=== Tool: search_related_issues ===")
            issues = self.search_related_issues(query)
            if "error" not in issues:
                print(f"Found {issues['total_results']} related issues/PRs")
                for issue in issues['issues']:
                    print(f"Issue #{issue['number']}: {issue['title']}")
            else:
                print(f"Error searching issues: {issues['error']}")
        
        # Create a context with the file structure
        context = {
            "file_structure": file_structure,
            "query": query
        }
        
        # Analyze the query and determine which files to examine
        analysis_prompt = f"""Based on the following query and file structure, determine which files to examine.
        Return your response in the following JSON format:

        ```json
        {{
            "files_to_examine": ["list", "of", "file", "paths"],
            "analysis_plan": "brief description of how to analyze these files"
        }}
        ```

        Query: {query}
        File Structure: {json.dumps(file_structure, indent=2)}
        """
        
        analysis_response = self.llm.chat(messages=[{"role": "user", "content": analysis_prompt}])
        analysis, _ = self._extract_json(analysis_response)
        
        # Gather information about the relevant files
        print("\n=== Tool: fetch_code and find_code_usage ===")
        file_info = {}
        for file_path in analysis.get("files_to_examine", []):
            print(f"\nExamining file: {file_path}")
            code_result = self.fetch_code(file_path)
            usage_result = self.find_code_usage(file_path)
            
            if "error" in code_result:
                print(f"Error fetching code: {code_result['error']}")
            else:
                print(f"Found {len(code_result['imports'])} imports")
                print(f"Used by {len(code_result['used_by'])} files")
            
            if "error" in usage_result:
                print(f"Error finding usage: {usage_result['error']}")
            else:
                print(f"Total dependencies: {usage_result['total_dependencies']}")
                print(f"Total dependents: {usage_result['total_dependents']}")
            
            file_info[file_path] = {
                "code": code_result,
                "usage": usage_result
            }
        
        # Generate final response
        final_prompt = f"""Based on the following information, answer the user's query.
        If your response contains any structured data, format it as JSON between triple backticks.

        Query: {query}
        File Information: {json.dumps(file_info, indent=2)}
        Analysis Plan: {analysis.get('analysis_plan', '')}

        Provide a detailed and well-structured response.
        """
        
        print("\n=== Generating Final Response ===")
        final_response = self.llm.chat(messages=[{"role": "user", "content": final_prompt}])
        
        # Extract any JSON from the final response
        json_data, remaining_text = self._extract_json(final_response)
        if json_data:
            print("\n=== Found Structured Data ===")
            print(f"JSON keys: {list(json_data.keys())}")
        
        return final_response
