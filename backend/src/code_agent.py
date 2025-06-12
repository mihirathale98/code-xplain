import json
import csv
from typing import List, Dict, Optional
from pydantic import BaseModel
from pydantic_ai import Agent, RunContext
import os
from llm_api import LLMApi
from code_parser import analyze_repo

class CodeSearchResult(BaseModel):
    """Model for code search results"""
    file_path: str
    code: str
    imports: List[str]
    used_by: List[str]

class CodeAgent:
    def __init__(self, llm_provider: str, api_key: Optional[str] = None):
        """Initialize the code agent with LLM API and tools"""
        self.llm = LLMApi(provider=llm_provider, api_key=api_key)
        self.file_structure = {}
        self.usage_lookup = {}
        self.code_data = {}
        
        # Create the agent with tools
        self.agent = Agent(
            'openai:gpt-4o-mini',
            instructions=(
                "You are a code analysis expert that understands codebases through structured exploration. "
                "Always start by using the 'read_file_structure' tool to understand the codebase organization. "
                "Then, based on the query, use 'fetch_code' to examine specific files and 'find_code_usage' to understand dependencies. "
                "Be thorough in your analysis and explain your reasoning at each step."
            ),
            verbose=True,
        )
        
        # Register tools
        self._register_tools()

    def _register_tools(self):
        """Register all tools with the agent"""
        
        @self.agent.tool
        def read_file_structure(ctx: RunContext) -> Dict:
            """Read and return the complete file structure of the codebase"""
            return {
                "file_structure": self.file_structure,
                "total_files": len(self.file_structure),
                "file_types": {
                    "python": len([f for f in self.file_structure.keys() if f.endswith('.py')]),
                    "other": len([f for f in self.file_structure.keys() if not f.endswith('.py')])
                }
            }

        @self.agent.tool
        def fetch_code(ctx: RunContext, file_path: str) -> Dict:
            """Fetch code content for a specific file"""
            if file_path not in self.code_data:
                return {"error": f"File {file_path} not found"}
            
            return {
                "file_path": file_path,
                "code": self.code_data[file_path],
                "imports": self.file_structure.get(file_path, {}).get('imports', []),
                "used_by": self.file_structure.get(file_path, {}).get('used_by', [])
            }

        @self.agent.tool
        def find_code_usage(ctx: RunContext, file_path: str) -> Dict:
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

    def load_repo_data(self, repo_url: str):
        """Load repository data using code_parser"""
        self.file_structure, csv_str, self.usage_lookup = analyze_repo(repo_url)
        
        # Parse CSV data
        csv_reader = csv.DictReader(csv_str.splitlines())
        self.code_data = {row['relative_path']: row['code'] for row in csv_reader}
        # print(self.code_data)

    def analyze_code(self, query: str) -> str:
        """Analyze code based on user query"""
        messages = [
            {"role": "system", "content": "You are a code analysis expert."},
            {"role": "user", "content": query}
        ]
        return self.llm.chat(messages=messages)

    def run(self, query: str) -> str:
        """Run the agent with a query"""
        return self.agent.run_sync(query)

# Example usage:
if __name__ == "__main__":
    # Initialize the agent
    agent = CodeAgent(llm_provider='openai', api_key=os.getenv('OPENAI_API_KEY'))
    
    # Load repository data
    agent.load_repo_data('https://github.com/Red-Hat-AI-Innovation-Team/mini_trainer')
    
    # The agent will automatically:
    # 1. Start with read_file_structure
    # 2. Use fetch_code for specific files
    # 3. Use find_code_usage for dependency analysis
    result = agent.run("Explain the main functionality of this codebase and how to train a model using it")
    print(result.output)
    
    # result = agent.run("Find all files that use the database connection")
    # print(result.output)
