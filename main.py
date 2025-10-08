from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get OpenAI API key from environment variable
if not os.getenv("OPENAI_API_KEY"):
    raise ValueError("OPENAI_API_KEY not found in environment variables. Please check your .env file.")
    
print(f"✅ Set OPENAI_API_KEY environment variable for ChatKit trace export")

# Verify the environment variable is set
if os.getenv("OPENAI_API_KEY"):
    print(f"✅ OPENAI_API_KEY is available for ChatKit agents")
else:
    print("⚠️  Warning: OPENAI_API_KEY not found - may cause trace export issues")

# OpenAI ChatKit imports
from openai import AsyncOpenAI
from types import SimpleNamespace
from agents import RunContextWrapper, Agent, ModelSettings, TResponseInputItem, Runner, RunConfig
from openai.types.shared.reasoning import Reasoning

app = FastAPI(title="Edison - ChatGPT-like Interface")

# Shared client for guardrails and file search - use environment variable for consistency
client = AsyncOpenAI()  # Will automatically use OPENAI_API_KEY environment variable
ctx = SimpleNamespace(guardrail_llm=client)

# In-memory storage for chat sessions
chat_sessions = {}


class Message(BaseModel):
    role: str  # "user" or "assistant"
    content: str
    timestamp: Optional[str] = None


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = "default"


class ChatResponse(BaseModel):
    response: str
    session_id: str
    timestamp: str


# OpenAI ChatKit Agent Classes and Configuration
class AgentContext:
    def __init__(self, input_result: str, workflow_input_as_text: str):
        self.input_result = input_result
        self.workflow_input_as_text = workflow_input_as_text


def agent_instructions(run_context: RunContextWrapper[AgentContext], _agent: Agent[AgentContext]):
    input_result = run_context.context.input_result
    workflow_input_as_text = run_context.context.workflow_input_as_text
    return f"""You are a personal assistant who knows about me and responds only if User asks something related to Akshay Dadwal, use info in Knowledge.

Knowledge:  {input_result}
User query: {workflow_input_as_text}"""


# Initialize main agent with error handling for trace export
try:
    agent = Agent(
        name="Agent",
        instructions=agent_instructions,
        model="gpt-5-nano",
        model_settings=ModelSettings(
            store=True,
            reasoning=Reasoning(
                effort="low"
            )
        )
    )
    print("✅ Main agent initialized successfully")
except Exception as e:
    print(f"⚠️  Warning during agent initialization: {e}")
    # Continue anyway - the agent might still work
    agent = Agent(
        name="Agent",
        instructions=agent_instructions,
        model="gpt-5-nano",
        model_settings=ModelSettings(
            store=True,
            reasoning=Reasoning(
                effort="low"
            )
        )
    )


class WorkflowInput(BaseModel):
    input_as_text: str


# Main OpenAI ChatKit workflow entrypoint
async def run_workflow(workflow_input: WorkflowInput):
    """
    Main workflow using OpenAI ChatKit agents with the specified workflow ID
    """
    print(f"🚀 Starting ChatKit workflow for: {workflow_input.input_as_text[:50]}...")
    
    state = {}
    workflow = workflow_input.model_dump()
    conversation_history: list[TResponseInputItem] = [
        {
            "role": "user",
            "content": [
                {
                    "type": "input_text",
                    "text": workflow["input_as_text"]
                }
            ]
        }
    ]
    
    # File search for relevant knowledge using vector store
    try:
        print("🔍 Searching vector store...")
        # Search vector store and handle response format
        search_response = await client.vector_stores.search(
            vector_store_id=os.getenv("VECTOR_STORE_ID", "vs_68e644eb49808191a3f7743ee399449e"), 
            query=workflow["input_as_text"], 
            max_num_results=2
        )
        
        # Handle the actual OpenAI API response structure
        filesearch_result = {"results": []}
        if hasattr(search_response, 'data') and search_response.data:
            for result in search_response.data:
                filesearch_result["results"].append({
                    "id": getattr(result, 'file_id', getattr(result, 'id', 'unknown')),
                    "filename": getattr(result, 'filename', getattr(result, 'name', 'unknown')),
                    "score": getattr(result, 'score', getattr(result, 'relevance_score', 0.0)),
                    "content": getattr(result, 'content', 'No content available')
                })
        
        # Extract content safely
        if filesearch_result["results"]:
            transform_result = {"result": filesearch_result["results"][0]["content"]}
        else:
            transform_result = {"result": "No relevant knowledge found"}
        print("✅ Vector search completed")
    except Exception as e:
        print(f"⚠️  Vector search failed (using fallback): {e}")
        # Fallback if vector store is not available
        transform_result = {"result": None}
    
    # Run main agent with context and knowledge if we have results
    if transform_result["result"]:
        try:
            print("🤖 Running main agent...")
            agent_result_temp = await Runner.run(
                agent,
                input=[
                    *conversation_history
                ],
                run_config=RunConfig(trace_metadata={
                    "__trace_source__": "agent-builder",
                    "workflow_id": os.getenv("WORKFLOW_ID", "wf_68e563885c7481909af54f1286d1a22a05adf05500389df0")
                }),
                context=AgentContext(
                    input_result=transform_result["result"],
                    workflow_input_as_text=workflow["input_as_text"]
                )
            )
            print("✅ Main agent completed")

            conversation_history.extend([item.to_input_item() for item in agent_result_temp.new_items])

            agent_result = {
                "output_text": agent_result_temp.final_output_as(str)
            }
            end_result = {
                "output_text": agent_result["output_text"]
            }
            
            print(f"✅ ChatKit workflow completed: {end_result['output_text'][:50]}...")
            return end_result
            
        except Exception as e:
            print(f"⚠️  Main agent warning (using fallback): {e}")
            # Fallback response
            return {
                "output_text": f"I'm Edison, your AI assistant. I encountered an issue with the ChatKit workflow: {str(e)}. How can I help you today?"
            }
    else:
        # No knowledge found
        end_result = {
            "output_text": "Sorry, I can't help."
        }
        return end_result


async def generate_response(user_message: str, history: List[dict]) -> str:
    """
    Generate a response using the OpenAI ChatKit workflow.
    """
    try:
        # Create workflow input
        workflow_input = WorkflowInput(input_as_text=user_message)
        
        # Run the ChatKit agent workflow
        result = await run_workflow(workflow_input)
        
        return result["output_text"]
    
    except Exception as e:
        # Fallback response if agent workflow fails
        return f"I'm Edison, your AI assistant. I encountered an issue processing your request: {str(e)}. Please try again."


def generate_response_sync(user_message: str, history: List[dict]) -> str:
    """
    Synchronous fallback function for simple responses.
    Used when the async agent workflow is not available.
    """
    message_lower = user_message.lower()
    
    # Simple rule-based responses for demonstration
    if any(greeting in message_lower for greeting in ["hello", "hi", "hey", "moshi"]):
        return "Hello! I'm Edison, here to help you. What would you like to know?"
    
    elif "stella" in message_lower:
        return "Stella is currently unavailable, but I'm here to assist you with whatever you need!"
    
    elif any(word in message_lower for word in ["who are you", "what are you", "introduce"]):
        return "I am Edison, an AI assistant. Stella is unavailable right now, so I will be handling all your queries. I'm here to help answer questions, provide information, and assist you with various tasks!"
    
    elif any(word in message_lower for word in ["help", "what can you do", "capabilities"]):
        return "I can help you with various tasks such as:\n- Answering questions\n- Providing information\n- Having conversations\n- And much more!\n\nNote: I'm now powered by OpenAI's ChatKit agents for intelligent responses."
    
    elif "?" in user_message:
        return f"That's an interesting question! Let me think about that: '{user_message}'. I'm processing this with my AI capabilities."
    
    else:
        return f"I understand you said: '{user_message}'. I'm Edison, your AI assistant powered by OpenAI ChatKit, ready to help with any questions or tasks you have."


@app.get("/", response_class=HTMLResponse)
async def read_root():
    """Serve the main chat interface"""
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Edison - ChatGPT Interface</title>
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }
            
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
                background: #343541;
                color: #ececf1;
                height: 100vh;
                display: flex;
                flex-direction: column;
            }
            
            .header {
                background: #202123;
                padding: 1rem 2rem;
                border-bottom: 1px solid #565869;
                display: flex;
                align-items: center;
                justify-content: space-between;
            }
            
            .header h1 {
                font-size: 1.25rem;
                font-weight: 600;
            }
            
            .chat-container {
                flex: 1;
                overflow-y: auto;
                padding: 2rem;
                display: flex;
                flex-direction: column;
                gap: 1rem;
            }
            
            .message {
                display: flex;
                gap: 1rem;
                padding: 1.5rem;
                animation: fadeIn 0.3s ease-in;
            }
            
            @keyframes fadeIn {
                from { opacity: 0; transform: translateY(10px); }
                to { opacity: 1; transform: translateY(0); }
            }
            
            .message.user {
                background: #343541;
            }
            
            .message.assistant {
                background: #444654;
            }
            
            .message-avatar {
                width: 40px;
                height: 40px;
                border-radius: 4px;
                display: flex;
                align-items: center;
                justify-content: center;
                font-weight: 600;
                flex-shrink: 0;
            }
            
            .message.user .message-avatar {
                background: #5436da;
            }
            
            .message.assistant .message-avatar {
                background: #19c37d;
            }
            
            .message-content {
                flex: 1;
                line-height: 1.6;
                white-space: pre-wrap;
                word-wrap: break-word;
            }
            
            .input-container {
                padding: 1.5rem 2rem;
                background: #343541;
                border-top: 1px solid #565869;
            }
            
            .input-wrapper {
                max-width: 800px;
                margin: 0 auto;
                position: relative;
            }
            
            .input-box {
                width: 100%;
                background: #40414f;
                border: 1px solid #565869;
                border-radius: 8px;
                padding: 1rem 3rem 1rem 1rem;
                color: #ececf1;
                font-size: 1rem;
                font-family: inherit;
                resize: none;
                outline: none;
                max-height: 200px;
                min-height: 52px;
            }
            
            .input-box:focus {
                border-color: #ececf1;
            }
            
            .send-button {
                position: absolute;
                right: 0.75rem;
                bottom: 0.75rem;
                background: #19c37d;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 0.5rem 1rem;
                cursor: pointer;
                font-weight: 600;
                transition: background 0.2s;
            }
            
            .send-button:hover:not(:disabled) {
                background: #1a9f6a;
            }
            
            .send-button:disabled {
                opacity: 0.5;
                cursor: not-allowed;
            }
            
            .loading {
                display: none;
                padding: 1.5rem;
                gap: 0.5rem;
                align-items: center;
            }
            
            .loading.active {
                display: flex;
            }
            
            .loading-dots {
                display: flex;
                gap: 0.25rem;
            }
            
            .loading-dot {
                width: 8px;
                height: 8px;
                background: #ececf1;
                border-radius: 50%;
                animation: pulse 1.4s infinite;
            }
            
            .loading-dot:nth-child(2) {
                animation-delay: 0.2s;
            }
            
            .loading-dot:nth-child(3) {
                animation-delay: 0.4s;
            }
            
            @keyframes pulse {
                0%, 60%, 100% { opacity: 0.3; }
                30% { opacity: 1; }
            }
            
            .clear-button {
                background: #40414f;
                color: #ececf1;
                border: 1px solid #565869;
                border-radius: 4px;
                padding: 0.5rem 1rem;
                cursor: pointer;
                font-weight: 500;
                transition: background 0.2s;
            }
            
            .clear-button:hover {
                background: #4f5058;
            }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🔆 Edison - ChatGPT Interface</h1>
            <button class="clear-button" onclick="clearChat()">Clear Chat</button>
        </div>
        
        <div class="chat-container" id="chatContainer">
            <div class="message assistant">
                <div class="message-avatar">E</div>
                <div class="message-content">Moshi-Moshi, I am Edison. Stella is unavailable right now so I will be dealing with all your queries. How can I help you today?</div>
            </div>
        </div>
        
        <div class="loading" id="loading">
            <div class="message-avatar" style="background: #19c37d;">E</div>
            <div class="loading-dots">
                <div class="loading-dot"></div>
                <div class="loading-dot"></div>
                <div class="loading-dot"></div>
            </div>
        </div>
        
        <div class="input-container">
            <div class="input-wrapper">
                <textarea 
                    id="messageInput" 
                    class="input-box" 
                    placeholder="Send a message..."
                    rows="1"
                    onkeydown="handleKeyPress(event)"
                    oninput="autoResize(this)"
                ></textarea>
                <button class="send-button" id="sendButton" onclick="sendMessage()">Send</button>
            </div>
        </div>
        
        <script>
            const chatContainer = document.getElementById('chatContainer');
            const messageInput = document.getElementById('messageInput');
            const sendButton = document.getElementById('sendButton');
            const loading = document.getElementById('loading');
            
            function autoResize(textarea) {
                textarea.style.height = 'auto';
                textarea.style.height = Math.min(textarea.scrollHeight, 200) + 'px';
            }
            
            function handleKeyPress(event) {
                if (event.key === 'Enter' && !event.shiftKey) {
                    event.preventDefault();
                    sendMessage();
                }
            }
            
            function addMessage(role, content) {
                const messageDiv = document.createElement('div');
                messageDiv.className = `message ${role}`;
                
                const avatar = document.createElement('div');
                avatar.className = 'message-avatar';
                avatar.textContent = role === 'user' ? 'U' : 'E';
                
                const contentDiv = document.createElement('div');
                contentDiv.className = 'message-content';
                contentDiv.textContent = content;
                
                messageDiv.appendChild(avatar);
                messageDiv.appendChild(contentDiv);
                
                chatContainer.appendChild(messageDiv);
                chatContainer.scrollTop = chatContainer.scrollHeight;
            }
            
            async function sendMessage() {
                const message = messageInput.value.trim();
                if (!message) return;
                
                // Add user message
                addMessage('user', message);
                
                // Clear input
                messageInput.value = '';
                messageInput.style.height = 'auto';
                
                // Disable send button and show loading
                sendButton.disabled = true;
                loading.classList.add('active');
                chatContainer.scrollTop = chatContainer.scrollHeight;
                
                try {
                    const response = await fetch('/api/chat', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({
                            message: message,
                            session_id: 'default'
                        })
                    });
                    
                    const data = await response.json();
                    
                    // Hide loading and add assistant message
                    loading.classList.remove('active');
                    addMessage('assistant', data.response);
                } catch (error) {
                    loading.classList.remove('active');
                    addMessage('assistant', 'Sorry, I encountered an error. Please try again.');
                    console.error('Error:', error);
                } finally {
                    sendButton.disabled = false;
                    messageInput.focus();
                }
            }
            
            function clearChat() {
                chatContainer.innerHTML = `
                    <div class="message assistant">
                        <div class="message-avatar">E</div>
                        <div class="message-content">Moshi-Moshi, I am Edison. Stella is unavailable right now so I will be dealing with all your queries. How can I help you today?</div>
                    </div>
                `;
                
                // Clear server-side history
                fetch('/api/chat/clear', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ session_id: 'default' })
                });
            }
            
            // Focus on input when page loads
            messageInput.focus();
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Handle chat messages and return responses using OpenAI ChatKit"""
    session_id = request.session_id
    
    # Initialize session if it doesn't exist
    if session_id not in chat_sessions:
        chat_sessions[session_id] = []
    
    # Add user message to history
    timestamp = datetime.now().isoformat()
    user_message = Message(role="user", content=request.message, timestamp=timestamp)
    chat_sessions[session_id].append(user_message.content)
    
    # Generate response using the OpenAI ChatKit workflow
    try:
        response_text = await generate_response(user_message.content, chat_sessions[session_id])
    except Exception as e:
        # Fallback to sync response if ChatKit workflow fails
        response_text = generate_response_sync(user_message.content, chat_sessions[session_id])
    
    # Add assistant response to history
    assistant_message = Message(role="assistant", content=response_text, timestamp=timestamp)
    chat_sessions[session_id].append(assistant_message.content)
    
    return ChatResponse(
        response=response_text,
        session_id=session_id,
        timestamp=timestamp
    )


@app.post("/api/chat/clear")
async def clear_chat(request: dict):
    """Clear chat history for a session"""
    session_id = request.get("session_id", "default")
    if session_id in chat_sessions:
        chat_sessions[session_id] = []
    return {"status": "success", "message": "Chat history cleared"}


@app.get("/api/chat/history/{session_id}")
async def get_history(session_id: str):
    """Get chat history for a session"""
    return {
        "session_id": session_id,
        "messages": chat_sessions.get(session_id, [])
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "Edison ChatGPT Interface"}


if __name__ == "__main__":
    import uvicorn
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host=host, port=port)
