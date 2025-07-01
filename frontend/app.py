import streamlit as st
import requests
import uuid
from typing import List, Dict
import json
import time
import asyncio
import aiohttp
from sseclient import SSEClient

# API configuration
API_URL = "http://localhost:8000"

def initialize_session_state():
    """Initialize session state variables"""
    if "session_id" not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "repo_url" not in st.session_state:
        st.session_state.repo_url = ""
    if "is_loading" not in st.session_state:
        st.session_state.is_loading = False
    if "repo_loaded" not in st.session_state:
        st.session_state.repo_loaded = False

def reset_chat():
    """Reset the chat session"""
    response = requests.delete(f"{API_URL}/chat/{st.session_state.session_id}")
    if response.status_code == 200:
        st.session_state.messages = []
        st.session_state.session_id = str(uuid.uuid4())
        st.success("Chat session reset successfully!")

def handle_stream_message(message_data: Dict, placeholder, thinking_placeholder):
    """Handle different types of streaming messages"""
    try:
        msg_type = message_data.get("type")
        data = message_data.get("data")
        
        if not msg_type or data is None:
            st.warning("Received invalid message format from server")
            return
        
        # Initialize session state for this placeholder if not exists
        placeholder_id = str(id(placeholder))
        if f"thinking_text_{placeholder_id}" not in st.session_state:
            st.session_state[f"thinking_text_{placeholder_id}"] = ""
        if f"response_text_{placeholder_id}" not in st.session_state:
            st.session_state[f"response_text_{placeholder_id}"] = ""
        
        # Handle different message types
        if msg_type in ["intent", "status", "pr_metadata", "test_results", "review", 
                       "summary", "code_analysis", "test_suite", "coverage", "suggestions",
                       "issue_search_results", "issue_details_data"]:
            # Add to thinking process
            if msg_type == "intent":
                new_text = f"🤔 Understanding request... ({data.get('intent_type', 'unknown')})\n"
            elif msg_type == "status":
                new_text = f"⏳ {data}\n"
            elif msg_type == "pr_metadata":
                new_text = "📝 Generated PR metadata\n"
            elif msg_type == "test_results":
                new_text = "🧪 Generated test results\n"
            elif msg_type == "review":
                new_text = "👀 Completed code review\n"
            elif msg_type == "summary":
                new_text = "📊 Generated summary\n"
            elif msg_type == "code_analysis":
                new_text = "🔍 Completed code analysis\n"
            elif msg_type == "test_suite":
                new_text = "🧪 Generated test suite\n"
            elif msg_type == "coverage":
                new_text = "📊 Generated coverage report\n"
            elif msg_type == "suggestions":
                new_text = "💡 Generated improvement suggestions\n"
            elif msg_type == "issue_search_results":
                new_text = "🔍 Found matching issues\n"
            elif msg_type == "issue_details_data":
                new_text = "📋 Retrieved issue details\n"
            
            # Update thinking text
            st.session_state[f"thinking_text_{placeholder_id}"] += new_text
            thinking_placeholder.markdown(f"### 🤔 Thinking and Executing\n{st.session_state[f'thinking_text_{placeholder_id}']}")
            

            print(data)
            # Show detailed data in an expander if available
            if msg_type not in ["intent", "status"] and data:
                expander_title = {
                    "issue_search_results": "🔍 Search Results",
                    "issue_details_data": "📋 Issue Details",
                }.get(msg_type, f"Details for {msg_type}")
                
                with st.expander(expander_title, expanded=False):
                    
                    st.markdown(data)
        
        elif msg_type == "token":
            # Update response text
            st.session_state[f"response_text_{placeholder_id}"] += data
            placeholder.markdown(st.session_state[f"response_text_{placeholder_id}"])
        
        elif msg_type == "response":
            # For final response
            placeholder.markdown(data)
            st.session_state[f"response_text_{placeholder_id}"] = data
        
        elif msg_type == "error":
            st.error(f"Error: {data}")
        
        else:
            st.warning(f"Unknown message type: {msg_type}")
                
    except Exception as e:
        st.error(f"Error displaying message: {str(e)}")

async def send_message_stream(message: str):
    """Send a message to the API and handle streaming response"""
    if not message:
        return
    
    st.session_state.is_loading = True
    response_content = ""
    
    try:
        # Add user message to chat
        st.session_state.messages.append({"role": "user", "content": message})
        
        # Create placeholders for thinking process and response
        with st.chat_message("assistant"):
            thinking_placeholder = st.empty()
            response_placeholder = st.empty()
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{API_URL}/chat/{st.session_state.session_id}/stream",
                    json={"role": "user", "content": message},
                    timeout=aiohttp.ClientTimeout(total=300)  # 5 minutes timeout
                ) as response:
                    
                    if response.status != 200:
                        error_text = await response.text()
                        st.error(f"Error from server: {error_text}")
                        return
                    
                    # Handle streaming response
                    async for line in response.content:
                        if line:
                            try:
                                message_data = json.loads(line.decode().strip())
                                handle_stream_message(message_data, response_placeholder, thinking_placeholder)
                                
                                # Accumulate response content
                                if message_data.get("type") == "response":
                                    response_content = message_data.get("data", "")
                                elif message_data.get("type") == "token":
                                    response_content += message_data.get("data", "")
                                elif message_data.get("type") == "error":
                                    st.error(message_data.get("data", "Unknown error"))
                                    return
                            except json.JSONDecodeError as e:
                                st.warning(f"Failed to parse server message: {line.decode()}")
                                continue
                            except Exception as e:
                                st.error(f"Error processing message: {str(e)}")
                                continue
                    
                    # Add final response to messages if we got one
                    if response_content:
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": response_content
                        })
                    
    except aiohttp.ClientError as e:
        st.error(f"Network error: {str(e)}")
    except asyncio.TimeoutError:
        st.error("Request timed out. Please try again.")
    except Exception as e:
        st.error(f"Error: {str(e)}")
    finally:
        st.session_state.is_loading = False

def load_repo(repo_url: str):
    """Load a repository for analysis"""
    if not repo_url:
        st.error("Please enter a repository URL")
        return
    
    st.session_state.is_loading = True
    
    try:
        with st.spinner("Loading repository..."):
            response = requests.post(
                f"{API_URL}/load-repo",
                json={"repo_url": repo_url}
            )
            if response.status_code == 200:
                st.success(f"Repository loaded successfully: {repo_url}")
                st.session_state.repo_url = repo_url
                st.session_state.repo_loaded = True
                # Reset chat after loading new repository
                reset_chat()
            else:
                st.error(f"Error loading repository: {response.text}")
                st.session_state.repo_loaded = False
    except Exception as e:
        st.error(f"Error: {str(e)}")
        st.session_state.repo_loaded = False
    finally:
        st.session_state.is_loading = False

def check_repo_status():
    """Check if a repository is currently loaded"""
    try:
        response = requests.get(f"{API_URL}/repo-status")
        if response.status_code == 200:
            data = response.json()
            if data["loaded"]:
                st.session_state.repo_url = data["repo_url"]
                st.session_state.repo_loaded = True
            else:
                st.session_state.repo_loaded = False
            return data["loaded"]
    except Exception:
        st.session_state.repo_loaded = False
    return False

def main():
    st.set_page_config(
        page_title="Code QA",
        page_icon="💻",
        layout="wide"
    )
    
    initialize_session_state()
    
    # Check repository status
    check_repo_status()
    
    # Sidebar
    with st.sidebar:
        st.title("⚙️ Settings")
        
        # Repository URL input section
        st.subheader("📁 Repository")
        repo_url_input = st.text_input(
            "GitHub Repository URL",
            placeholder="https://github.com/owner/repo.git",
            help="Enter a GitHub repository URL to analyze"
        )
        
        # Load repository button
        col1, col2 = st.columns([2, 1])
        with col1:
            load_button = st.button(
                "🚀 Load Repository",
                disabled=st.session_state.is_loading or not repo_url_input.strip(),
                help="Click to load the repository for analysis"
            )
        with col2:
            if st.button("🔄", help="Refresh status"):
                check_repo_status()
                st.rerun()
        
        # Handle repository loading
        if load_button and repo_url_input.strip():
            load_repo(repo_url_input.strip())
        
        st.divider()
        
        # Chat controls section
        st.subheader("💬 Chat Controls")
        
        # Reset chat button
        if st.button("🗑️ Reset Chat", help="Clear chat history and start fresh"):
            reset_chat()
            st.rerun()
        
        st.divider()
        
        # Status section
        st.subheader("📊 Status")
        
        # Display repository status
        if st.session_state.repo_loaded:
            st.success("✅ Repository Loaded")
            st.info(f"**Current Repository:**\n{st.session_state.repo_url}")
        else:
            st.warning("⚠️ No Repository Loaded")
            st.info("Load a repository to start analyzing code")
        
        # Session info
        with st.expander("🔍 Session Info"):
            st.text(f"Session ID: {st.session_state.session_id}")
            st.text(f"Messages: {len(st.session_state.messages)}")
            st.text(f"Loading: {st.session_state.is_loading}")
    
    # Main chat interface
    st.title("💻 Code QA")
    
    # Welcome message when no repository is loaded
    if not st.session_state.repo_loaded:
        st.info("""
        👋 **Welcome to Code-Xplain!**
        
        To get started:
        1. Enter a GitHub repository URL in the sidebar
        2. Click "🚀 Load Repository" 
        3. Start asking questions about the codebase!
        
        **Example repositories to try:**
        - `https://github.com/fastapi/fastapi.git`
        - `https://github.com/streamlit/streamlit.git`
        - `https://github.com/microsoft/vscode.git`
        """)
    
    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Chat input
    if prompt := st.chat_input(
        placeholder="Ask about the code...",
        disabled=not st.session_state.repo_loaded or st.session_state.is_loading
    ):
        # Use asyncio to handle streaming
        asyncio.run(send_message_stream(prompt))
    
    # Loading indicator
    if st.session_state.is_loading:
        with st.spinner("Processing..."):
            time.sleep(0.1)  # Small delay to show spinner

if __name__ == "__main__":
    main() 