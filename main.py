from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import os

app = FastAPI(title="Edison - ChatGPT-like Interface")

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
    """Handle chat messages and return responses"""
    session_id = request.session_id
    
    # Initialize session if it doesn't exist
    if session_id not in chat_sessions:
        chat_sessions[session_id] = []
    
    # Add user message to history
    timestamp = datetime.now().isoformat()
    user_message = Message(role="user", content=request.message, timestamp=timestamp)
    chat_sessions[session_id].append(user_message.dict())
    
    # Generate a simple response (placeholder for actual AI integration)
    response_text = generate_response(request.message, chat_sessions[session_id])
    
    # Add assistant response to history
    assistant_message = Message(role="assistant", content=response_text, timestamp=timestamp)
    chat_sessions[session_id].append(assistant_message.dict())
    
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


def generate_response(user_message: str, history: List[dict]) -> str:
    """
    Generate a response to the user message.
    This is a placeholder function. In a real implementation, you would:
    - Integrate with OpenAI API, Anthropic, or other LLM providers
    - Use the conversation history for context
    - Implement more sophisticated response generation
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
        return "I can help you with various tasks such as:\n- Answering questions\n- Providing information\n- Having conversations\n- And much more!\n\nNote: This is a boilerplate implementation. To get full AI capabilities, you'll need to integrate with an AI API provider like OpenAI, Anthropic, or others."
    
    elif "?" in user_message:
        return f"That's an interesting question! In a production environment, I would process your query using advanced AI models. For now, I'm acknowledging your question: '{user_message}'"
    
    else:
        return f"I understand you said: '{user_message}'. This is a demonstration interface. To provide intelligent responses, please integrate with an AI API provider (OpenAI, Anthropic, etc.) in the generate_response function."


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "Edison ChatGPT Interface"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
