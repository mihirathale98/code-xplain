# Code-Xplain: AI-Powered Code Analysis System

A comprehensive code analysis system that combines AI-powered insights with GitHub integration to help developers understand, analyze, and explore codebases through natural language conversations.

## 🚀 Features

- **🤖 AI-Powered Analysis**: Uses Google Gemini 2.5 Pro for intelligent code understanding
- **💬 Conversational Interface**: Chat-based interaction with context awareness
- **🔍 Smart Intent Recognition**: Automatically determines when to use tools vs. conversational responses
- **📁 Repository Analysis**: Deep codebase structure analysis and file dependency mapping
- **🐛 GitHub Integration**: Search and analyze issues, PRs, and repository metadata
- **🎯 Context-Aware Responses**: Maintains conversation history for better interactions
- **⚡ Optimized Performance**: Only executes necessary tool calls based on user intent

## 🏗️ Architecture

```
code-xplain/
├── backend/                 # FastAPI backend
│   └── src/
│       ├── api.py          # Main API endpoints
│       ├── code_agent.py   # Core agent with intent identification
│       ├── llm_api.py      # LLM provider abstraction
│       ├── git_utils.py    # GitHub API integration
│       └── code_parser.py  # Repository parsing utilities
└── frontend/               # Streamlit frontend
    ├── app.py             # Main Streamlit application
    └── requirements.txt   # Frontend dependencies
```

## 🛠️ Setup & Installation

### Prerequisites

- Python 3.8+
- Google API Key (for Gemini 2.5 Pro)
- GitHub Token (optional, for enhanced API limits)
- Conda (recommended for environment management)

### 1. Create Conda Environment

```bash
# Create and activate conda environment
conda create -n code-xplain python=3.10
conda activate code-xplain

# Install dependencies
pip install -r requirements.txt
```

### 2. Clone the Repository

```bash
git clone https://github.com/mihirathale98/code-xplain.git
cd code-xplain
```

### 3. Backend Setup

```bash
# Navigate to backend
cd backend

# Install dependencies (includes Gemini by default)
pip install -r requirements.txt

# Optional: For other LLM providers, edit requirements.txt first
# Uncomment the desired provider lines in requirements.txt, then:
# pip install -r requirements.txt
```

#### Set Environment Variables
```bash
# Set environment variables (choose based on your provider)
export GOOGLE_API_KEY='your-google-api-key-here'      # For Gemini (default)
export OPENAI_API_KEY='your-openai-api-key-here'      # For OpenAI (if enabled)
export ANTHROPIC_API_KEY='your-anthropic-api-key'     # For Anthropic (if enabled)
export TOGETHER_API_KEY='your-together-api-key'       # For Together AI (if enabled)
export GITHUB_TOKEN='your-github-token-here'          # Optional but recommended
```

### 4. Frontend Setup

```bash
# Navigate to frontend
cd frontend

# Install dependencies
pip install -r requirements.txt
```

## 🚀 Running the Application

### Start the Backend

```bash
cd backend/src
uvicorn api:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

### Start the Frontend

```bash
cd frontend
streamlit run app.py
```

The web interface will be available at `http://localhost:8501`

## 🎨 User Interface

The Streamlit interface features:

- **📁 Repository Section**: Enter GitHub URLs and load repositories with a dedicated button
- **💬 Chat Controls**: Reset chat sessions and manage conversation history
- **📊 Status Display**: Real-time status of loaded repository and session information
- **🔍 Session Info**: Expandable section with detailed session metrics
- **👋 Welcome Guide**: Helpful onboarding with example repositories
- **🚀 Action Buttons**: Clear, emoji-enhanced buttons for all actions

## 📖 Usage Guide

### 1. Load a Repository

1. Open the Streamlit interface
2. In the sidebar, enter a GitHub repository URL:
   ```
   https://github.com/owner/repository.git
   ```
3. Click the "🚀 Load Repository" button
4. Wait for the "Repository loaded successfully" message

**Example repositories to try:**
- `https://github.com/fastapi/fastapi.git`
- `https://github.com/streamlit/streamlit.git`
- `https://github.com/microsoft/vscode.git`

### 2. Start Analyzing

The system uses intelligent intent recognition to provide the best responses:

#### **Greetings & General Chat**
```
User: "Hello! What can you help me with?"
→ Friendly introduction and guidance
```

#### **Code Structure Questions**
```
User: "What's the overall architecture of this project?"
→ Analyzes file structure and provides architectural overview
```

#### **Specific Code Analysis**
```
User: "How does the authentication system work?"
→ Examines relevant files and explains the implementation
```

#### **Bug & Issue Research**
```
User: "Are there any reported issues with the login feature?"
→ Searches GitHub issues and provides relevant findings
```

#### **Follow-up Questions**
```
User: "Can you explain that function in more detail?"
→ Uses conversation context to provide detailed explanations
```

### 3. Chat Features

- **Session Management**: Each browser session maintains its own chat history
- **Context Awareness**: The system remembers previous conversations
- **Reset Functionality**: Use "🗑️ Reset Chat" button to start fresh
- **Repository Switching**: Load different repositories using the "🚀 Load Repository" button
- **Status Monitoring**: Real-time status display showing repository and session information
- **Welcome Guidance**: Helpful instructions and example repositories when starting

## 🎯 Intent Recognition System

The system automatically identifies user intent and optimizes responses:

| Intent Type | Description | Tools Used | Example |
|-------------|-------------|------------|---------|
| `greeting` | Simple greetings | None | "Hello!", "Hi there!" |
| `general_conversation` | General questions | Context only | "What can you do?" |
| `code_analysis` | Code examination | File tools | "How does X work?" |
| `architecture_overview` | Structure questions | File structure | "Show me the project structure" |
| `issue_search` | Bug/issue research | GitHub API | "Any bugs with login?" |
| `issue_details` | Specific issue info | GitHub API | "Tell me about issue #123" |
| `clarification` | Follow-up questions | Context + tools | "Explain that function more" |

## 🔧 API Endpoints

### Repository Management
- `POST /load-repo` - Load a repository for analysis
- `GET /repo-status` - Check current repository status

### Analysis
- `POST /analyze` - Direct code analysis (legacy)
- `POST /chat/{session_id}` - Chat with intent recognition
- `GET /chat/{session_id}/history` - Get chat history
- `DELETE /chat/{session_id}` - Reset chat session

## 🎨 Example Interactions

### Architecture Analysis
```
User: "Give me an overview of this codebase"
Agent: "This repository has a FastAPI backend with 5 Python files and a Streamlit frontend. 
        The main components are:
        - api.py: REST API endpoints
        - code_agent.py: Core analysis logic with intent recognition
        - llm_api.py: LLM provider abstraction
        - git_utils.py: GitHub integration
        The architecture follows a clean separation with the agent handling business logic..."
```

### Code Deep Dive
```
User: "How does the intent identification work?"
Agent: "The intent identification system works through several steps:
        1. The identify_intent() method in code_agent.py analyzes the user query
        2. It uses chat history context to understand conversation flow
        3. The LLM determines intent type and required tools
        4. Based on intent, it either responds conversationally or executes tools
        
        Here's the key code from code_agent.py:
        [Shows relevant code snippets and explanations]"
```

### Issue Research
```
User: "Are there any performance issues reported?"
Agent: "I found 3 performance-related issues in the repository:
        
        Issue #45: "Slow response times on large repositories"
        - Status: Open
        - Labels: performance, bug
        - Created: 2024-01-15
        
        Issue #32: "Memory usage optimization needed"
        - Status: Closed
        - Labels: performance, enhancement
        - Resolved with commit abc123f
        
        [Additional details and analysis]"
```

## 🔍 Advanced Features

### Custom Queries
- **File Dependencies**: "What files depend on utils.py?"
- **Code Patterns**: "Show me all the API endpoints"
- **Error Handling**: "How are exceptions handled in this project?"
- **Testing**: "What's the test coverage like?"

### GitHub Integration
- **Issue Analysis**: "What are the most common bug reports?"
- **PR Review**: "Show me recent pull requests about authentication"
- **Contributor Insights**: "Who are the main contributors?"

## 🛠️ Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `GOOGLE_API_KEY` | Google Gemini API key | Yes (for Gemini) |
| `OPENAI_API_KEY` | OpenAI API key | Yes (for OpenAI) |
| `ANTHROPIC_API_KEY` | Anthropic API key | Yes (for Anthropic) |
| `GITHUB_TOKEN` | GitHub personal access token | No* |
| `GOOGLE_CLOUD_PROJECT` | GCP project (for Vertex AI) | No |
| `GOOGLE_CLOUD_LOCATION` | GCP location (for Vertex AI) | No |

*GitHub token is optional but recommended for higher API rate limits

### Switching LLM Providers

The system supports multiple LLM providers. You can switch between them by modifying the backend configuration:

#### 1. Using Google Gemini (Default)

```python
# In backend/src/api.py, line 25-29:
agent = CodeAgent(
    llm_provider='gemini',
    api_key=os.getenv('GOOGLE_API_KEY'),
    github_token=os.getenv('GITHUB_TOKEN')
)
```

**Required:**
- Set `GOOGLE_API_KEY` environment variable
- Install: `pip install google-generativeai`

#### 2. Using OpenAI

```python
# In backend/src/api.py, line 25-29:
agent = CodeAgent(
    llm_provider='openai',
    api_key=os.getenv('OPENAI_API_KEY'),
    github_token=os.getenv('GITHUB_TOKEN')
)
```

**Required:**
- Set `OPENAI_API_KEY` environment variable
- Install: `pip install openai`

**Supported Models:**
- `gpt-4o-mini` (default)
- `gpt-4o`
- `gpt-4-turbo`
- `gpt-3.5-turbo`

#### 3. Using Anthropic Claude

```python
# In backend/src/api.py, line 25-29:
agent = CodeAgent(
    llm_provider='anthropic',
    api_key=os.getenv('ANTHROPIC_API_KEY'),
    github_token=os.getenv('GITHUB_TOKEN')
)
```

**Required:**
- Set `ANTHROPIC_API_KEY` environment variable
- Install: `pip install anthropic`

**Supported Models:**
- `claude-3-5-sonnet-latest` (default)
- `claude-3-5-haiku-latest`
- `claude-3-opus-latest`

#### 4. Using Together AI (OpenAI Compatible)

```python
# In backend/src/api.py, line 25-29:
agent = CodeAgent(
    llm_provider='together',
    api_key=os.getenv('TOGETHER_API_KEY'),
    github_token=os.getenv('GITHUB_TOKEN')
)
```

**Required:**
- Set `TOGETHER_API_KEY` environment variable
- Install: `pip install openai`

### Custom Model Selection

You can also specify custom models by modifying the `llm_api.py` file or passing model parameters:

```python
# Example: Using a specific OpenAI model
response = self.llm.chat(messages=messages, model='gpt-4o')

# Example: Using a specific Anthropic model
response = self.llm.chat(messages=messages, model='claude-3-opus-latest')

# Example: Using a specific Gemini model
response = self.llm.chat(messages=messages, model='gemini-1.5-pro')
```

### Getting API Keys

#### Google Gemini API Key
1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create a new API key
3. Copy and set as `GOOGLE_API_KEY`

#### OpenAI API Key
1. Go to [OpenAI Platform](https://platform.openai.com/api-keys)
2. Create a new secret key
3. Copy and set as `OPENAI_API_KEY`

#### Anthropic API Key
1. Go to [Anthropic Console](https://console.anthropic.com/settings/keys)
2. Create a new API key
3. Copy and set as `ANTHROPIC_API_KEY`

#### Together AI API Key
1. Go to [Together AI](https://api.together.xyz/settings/api-keys)
2. Create a new API key
3. Copy and set as `TOGETHER_API_KEY`

#### GitHub Token
1. Go to GitHub Settings → Developer settings → Personal access tokens
2. Generate new token with `repo` and `read:org` scopes
3. Copy and set as `GITHUB_TOKEN`

## 🐛 Troubleshooting

### Common Issues

#### "No repository loaded" Error
- **Cause**: Repository URL not provided or failed to load
- **Solution**: Enter a valid GitHub repository URL in the sidebar

#### "GitHub API rate limit exceeded"
- **Cause**: Too many API calls without authentication
- **Solution**: Set `GITHUB_TOKEN` environment variable

#### "Error in Gemini chat" 
- **Cause**: Invalid or missing Google API key
- **Solution**: Verify `GOOGLE_API_KEY` is set correctly

#### "OpenAI API Error"
- **Cause**: Invalid or missing OpenAI API key, or insufficient credits
- **Solution**: Verify `OPENAI_API_KEY` is set and account has credits

#### "Anthropic API Error"
- **Cause**: Invalid or missing Anthropic API key, or rate limits
- **Solution**: Verify `ANTHROPIC_API_KEY` is set correctly

#### "Unsupported provider" Error
- **Cause**: Invalid provider name in configuration
- **Solution**: Use one of: 'gemini', 'openai', 'anthropic', 'together'

#### Slow Response Times
- **Cause**: Large repository or complex analysis
- **Solution**: The system optimizes based on intent; try more specific queries

### Debug Mode

Enable detailed logging:
```bash
# Backend
export LOG_LEVEL=DEBUG
uvicorn api:app --reload --log-level debug

# Check logs for detailed information
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes
4. Add tests if applicable
5. Commit: `git commit -am 'Add feature'`
6. Push: `git push origin feature-name`
7. Create a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Google Gemini 2.5 Pro** for powerful language understanding
- **FastAPI** for the robust backend framework
- **Streamlit** for the intuitive frontend interface
- **GitHub API** for repository integration

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/your-username/code-xplain/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-username/code-xplain/discussions)
- **Documentation**: This README and inline code comments

---

**Happy Code Exploring! 🚀**
