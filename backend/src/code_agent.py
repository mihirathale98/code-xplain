import json
import csv
import re
from typing import List, Dict, Optional, Tuple
from pydantic import BaseModel
import os
import logging
from llm_api import LLMApi
from code_parser import analyze_repo
from git_utils import GitUtils

logger = logging.getLogger(__name__)

class CodeSearchResult(BaseModel):
    """Model for code search results"""
    file_path: str
    code: str
    imports: List[str]
    used_by: List[str]

class IntentAnalysis(BaseModel):
    """Model for intent analysis results"""
    intent_type: str
    requires_tools: bool
    confidence: float
    reasoning: str
    suggested_tools: List[str]
    can_answer_from_context: bool

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

    def identify_intent(self, query: str, chat_history: List[Dict] = None) -> Dict:
        """Identify the intent of the user query and determine if tool calls are needed"""
        logger.info(f"Identifying intent for query: {query[:100]}...")
        
        # Prepare chat history context
        history_context = ""
        if chat_history:
            recent_history = chat_history[-6:]  # Last 6 messages for context
            history_context = "\n".join([
                f"{msg.get('role', 'unknown')}: {msg.get('content', '')[:200]}..."
                for msg in recent_history
            ])
        
        intent_prompt = f"""You are an intent identification agent for a code analysis system. 
        Analyze the user's query and chat history to determine:
        1. What the user is trying to accomplish
        2. Whether tool calls are needed or if you can answer from conversation context
        3. Which specific tools might be needed
        
        Available tools:
        - read_file_structure: Get overview of codebase structure
        - fetch_code: Get specific file content
        - find_code_usage: Find dependencies and usage of files
        - search_related_issues: Search GitHub issues/PRs
        - get_issue_details: Get detailed issue information
        
        Intent types:
        - code_analysis: Needs to examine specific code files
        - architecture_overview: Needs file structure information
        - issue_search: Needs to search GitHub issues/PRs
        - issue_details: Needs specific issue information
        - general_conversation: Can be answered without tools
        - clarification: Asking for clarification or follow-up
        - greeting: Simple greeting or introduction
        
        Return your analysis in JSON format:
        ```json
        {{
            "intent_type": "one of the intent types above",
            "requires_tools": true/false,
            "confidence": 0.0-1.0,
            "reasoning": "explanation of your decision",
            "suggested_tools": ["list", "of", "tools", "if", "needed"],
            "can_answer_from_context": true/false,
            "response_strategy": "how to approach the response"
        }}
        ```
        
        Current Query: {query}
        
        Chat History:
        {history_context if history_context else "No previous conversation"}
        
        Repository Status: {"Loaded" if self.current_repo_url else "Not loaded"}
        """
        
        try:
            intent_response = self.llm.chat(messages=[{"role": "user", "content": intent_prompt}])
            intent_data, _ = self._extract_json(intent_response)
            
            if not intent_data:
                # Fallback intent analysis
                logger.warning("Failed to parse intent JSON, using fallback analysis")
                intent_data = self._fallback_intent_analysis(query, chat_history)
            
            logger.info(f"Intent identified: {intent_data.get('intent_type')} (confidence: {intent_data.get('confidence')})")
            return intent_data
            
        except Exception as e:
            logger.error(f"Error in intent identification: {str(e)}")
            return self._fallback_intent_analysis(query, chat_history)

    def _fallback_intent_analysis(self, query: str, chat_history: List[Dict] = None) -> Dict:
        """Fallback intent analysis using simple heuristics"""
        query_lower = query.lower()
        
        # Simple keyword-based intent detection
        if any(word in query_lower for word in ['hello', 'hi', 'hey', 'greetings']):
            return {
                "intent_type": "greeting",
                "requires_tools": False,
                "confidence": 0.9,
                "reasoning": "Query contains greeting words",
                "suggested_tools": [],
                "can_answer_from_context": True,
                "response_strategy": "friendly_greeting"
            }
        
        if any(word in query_lower for word in ['issue', 'bug', 'pr', 'pull request', 'problem']):
            return {
                "intent_type": "issue_search",
                "requires_tools": True,
                "confidence": 0.8,
                "reasoning": "Query mentions issues or bugs",
                "suggested_tools": ["search_related_issues"],
                "can_answer_from_context": False,
                "response_strategy": "search_and_analyze"
            }
        
        if any(word in query_lower for word in ['structure', 'architecture', 'overview', 'files']):
            return {
                "intent_type": "architecture_overview",
                "requires_tools": True,
                "confidence": 0.8,
                "reasoning": "Query asks about code structure",
                "suggested_tools": ["read_file_structure"],
                "can_answer_from_context": False,
                "response_strategy": "structural_analysis"
            }
        
        # Default to code analysis if repository is loaded
        if self.current_repo_url:
            return {
                "intent_type": "code_analysis",
                "requires_tools": True,
                "confidence": 0.6,
                "reasoning": "General code-related query with repository loaded",
                "suggested_tools": ["read_file_structure", "fetch_code"],
                "can_answer_from_context": False,
                "response_strategy": "comprehensive_analysis"
            }
        
        return {
            "intent_type": "general_conversation",
            "requires_tools": False,
            "confidence": 0.7,
            "reasoning": "No specific code analysis intent detected",
            "suggested_tools": [],
            "can_answer_from_context": True,
            "response_strategy": "conversational"
        }

    def handle_conversational_response(self, query: str, chat_history: List[Dict] = None, intent_data: Dict = None) -> str:
        """Handle responses that don't require tool calls"""
        logger.info("Generating conversational response without tool calls")
        
        # Prepare context from chat history
        context = ""
        if chat_history:
            recent_history = chat_history[-4:]  # Last 4 messages for context
            context = "\n".join([
                f"{msg.get('role', 'unknown')}: {msg.get('content', '')}"
                for msg in recent_history
            ])
        
        conversational_prompt = f"""You are a helpful code analysis assistant. The user's query doesn't require specific tool calls or code examination.
        
        Respond naturally and helpfully based on the conversation context and your general knowledge.
        
        Intent Analysis: {json.dumps(intent_data, indent=2) if intent_data else "Not available"}
        
        Recent Conversation:
        {context if context else "No previous conversation"}
        
        Current Query: {query}
        
        Repository Status: {"Repository loaded and ready for analysis" if self.current_repo_url else "No repository currently loaded"}
        
        Provide a helpful, conversational response. If the user needs code analysis, guide them on how to ask specific questions about the codebase.
        """
        
        return self.llm.chat(messages=[{"role": "user", "content": conversational_prompt}])

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
            logger.info(f"Searching for issues related to: {query}")
            issues = self.git.search_related_issues(self.current_repo_url, query)
            logger.info(f"Found {len(issues)} related issues/PRs")
            
            # Format issues for better display
            formatted_issues = []
            for issue in issues[:10]:  # Return top 10 results
                formatted_issues.append({
                    "number": issue.get("number"),
                    "title": issue.get("title"),
                    "state": issue.get("state"),
                    "url": issue.get("html_url"),
                    "created_at": issue.get("created_at"),
                    "updated_at": issue.get("updated_at"),
                    "labels": [label.get("name") for label in issue.get("labels", [])],
                    "is_pull_request": "pull_request" in issue
                })
            
            return {
                "total_results": len(issues),
                "issues": formatted_issues,
                "query": query
            }
        except Exception as e:
            error_msg = f"Error searching issues: {str(e)}"
            logger.error(error_msg)
            return {"error": error_msg}

    def get_issue_details(self, issue_number: int) -> Dict:
        """Get detailed information about a specific issue"""
        if not self.current_repo_url:
            return {"error": "No repository loaded"}
        
        try:
            logger.info(f"Getting details for issue #{issue_number}")
            return self.git.get_issue_details(self.current_repo_url, issue_number)
        except Exception as e:
            error_msg = f"Error getting issue details: {str(e)}"
            logger.error(error_msg)
            return {"error": error_msg}

    def load_repo_data(self, repo_url: str):
        """Load repository data using code_parser and git utilities"""
        logger.info(f"Loading repository data for: {repo_url}")
        self.current_repo_url = repo_url
        self.file_structure, csv_str, self.usage_lookup = analyze_repo(repo_url)
        
        # Parse CSV data
        csv_reader = csv.DictReader(csv_str.splitlines())
        self.code_data = {row['relative_path']: row['code'] for row in csv_reader}
        
        # Load repository metadata
        try:
            logger.info("Loading repository metadata...")
            self.git.get_repo_metadata(repo_url)
            logger.info("Repository metadata loaded successfully")
        except Exception as e:
            logger.warning(f"Could not load repository metadata: {e}")

    def analyze_code(self, query: str) -> str:
        """Analyze code based on user query"""
        messages = [
            {"role": "system", "content": "You are a code analysis expert."},
            {"role": "user", "content": query}
        ]
        return self.llm.chat(messages=messages)

    def run(self, query: str, chat_history: List[Dict] = None) -> str:
        """Run the agent with a query, using intent identification to determine approach"""
        logger.info(f"Starting analysis for query: {query}")
        
        # Step 1: Identify intent
        intent_data = self.identify_intent(query, chat_history)
        logger.info(f"Intent analysis: {intent_data.get('intent_type')} (requires_tools: {intent_data.get('requires_tools')})")
        
        # Step 2: Handle based on intent
        if not intent_data.get('requires_tools', True):
            # Handle conversational responses without tool calls
            return self.handle_conversational_response(query, chat_history, intent_data)
        
        # Step 3: Repository check for tool-requiring intents
        if intent_data.get('requires_tools') and not self.current_repo_url:
            return "I'd be happy to help with code analysis, but no repository is currently loaded. Please load a repository first using the repository URL input, then I can analyze the code, search for issues, or examine the file structure."
        
        # Step 4: Execute tool-based analysis
        return self._execute_tool_based_analysis(query, chat_history, intent_data)

    def _execute_tool_based_analysis(self, query: str, chat_history: List[Dict], intent_data: Dict) -> str:
        """Execute analysis that requires tool calls"""
        logger.info("Executing tool-based analysis")
        
        # Get file structure (always useful for context)
        file_structure = self.read_file_structure()
        logger.info(f"Found {len(file_structure['file_structure'])} files")
        
        # Execute tools based on intent
        issues_data = None
        file_info = {}
        
        suggested_tools = intent_data.get('suggested_tools', [])
        
        # Search for issues if suggested
        if 'search_related_issues' in suggested_tools:
            logger.info("Searching for related issues...")
            issues_data = self.search_related_issues(query)
            if "error" not in issues_data:
                logger.info(f"Found {issues_data['total_results']} related issues/PRs")
            else:
                logger.error(f"Error searching issues: {issues_data['error']}")
        
        # Analyze files if needed
        if any(tool in suggested_tools for tool in ['fetch_code', 'find_code_usage']) or intent_data.get('intent_type') == 'code_analysis':
            # Determine which files to examine
            analysis_prompt = f"""Based on the query and file structure, determine which files to examine.
            Return your response in JSON format:

            ```json
            {{
                "files_to_examine": ["list", "of", "file", "paths"],
                "analysis_plan": "brief description of analysis approach"
            }}
            ```

            Query: {query}
            Intent: {intent_data.get('intent_type')}
            File Structure: {json.dumps(file_structure, indent=2)}
            """
            
            analysis_response = self.llm.chat(messages=[{"role": "user", "content": analysis_prompt}])
            analysis, _ = self._extract_json(analysis_response)
            
            # Gather file information
            for file_path in analysis.get("files_to_examine", [])[:5]:  # Limit to 5 files
                logger.info(f"Examining file: {file_path}")
                code_result = self.fetch_code(file_path)
                usage_result = self.find_code_usage(file_path)
                
                file_info[file_path] = {
                    "code": code_result,
                    "usage": usage_result
                }
        
        # Generate final response
        final_prompt = f"""Based on the following information, provide a comprehensive response to the user's query.

        Query: {query}
        Intent Analysis: {json.dumps(intent_data, indent=2)}
        File Structure: {json.dumps(file_structure, indent=2)}
        File Information: {json.dumps(file_info, indent=2)}
        Issues Information: {json.dumps(issues_data, indent=2) if issues_data else "No issues data"}
        
        Chat History Context:
        {json.dumps(chat_history[-4:] if chat_history else [], indent=2)}

        Provide a detailed, well-structured response that directly addresses the user's query.
        Include relevant code examples, issue references, or architectural insights as appropriate.
        """
        
        logger.info("Generating final response...")
        final_response = self.llm.chat(messages=[{"role": "user", "content": final_prompt}])
        
        return final_response
