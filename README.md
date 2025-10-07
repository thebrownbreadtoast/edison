# edison
Moshi-Moshi, I am Edison. Stella is unavailable right now so I will be dealing with all Your queries.

## 🚀 FastAPI ChatGPT-like Interface

A modern, responsive chat interface built with FastAPI, featuring a ChatGPT-like UI for conversational interactions.

### Features

- 🎨 Modern, responsive ChatGPT-inspired UI
- 💬 Real-time chat interface
- 📝 Message history tracking per session
- 🔄 Clear chat functionality
- ⚡ Fast and lightweight with FastAPI
- 🎯 Easy to extend with AI integrations

### Quick Start

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the Application**
   ```bash
   python main.py
   ```
   
   Or using uvicorn directly:
   ```bash
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

3. **Open Your Browser**
   
   Navigate to: `http://localhost:8000`

### API Endpoints

- `GET /` - Main chat interface (HTML)
- `POST /api/chat` - Send a chat message
- `POST /api/chat/clear` - Clear chat history
- `GET /api/chat/history/{session_id}` - Get chat history
- `GET /health` - Health check endpoint

### Architecture

```
edison/
├── main.py              # FastAPI application with embedded HTML UI
├── requirements.txt     # Python dependencies
└── README.md           # This file
```

### Extending with AI

The current implementation includes a placeholder `generate_response()` function. To add real AI capabilities, integrate with:

- **OpenAI API**: For GPT-3.5/GPT-4 models
- **Anthropic Claude**: For Claude models
- **Local Models**: Using Ollama, LM Studio, etc.
- **Other APIs**: Cohere, Google PaLM, etc.

Example OpenAI integration:
```python
import openai

def generate_response(user_message: str, history: List[dict]) -> str:
    messages = [{"role": msg["role"], "content": msg["content"]} for msg in history]
    messages.append({"role": "user", "content": user_message})
    
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=messages
    )
    
    return response.choices[0].message.content
```

### Configuration

- **Host**: Default `0.0.0.0` (all interfaces)
- **Port**: Default `8000`
- **Session Management**: In-memory (for production, use Redis or a database)

### Development

```bash
# Install in development mode
pip install -r requirements.txt

# Run with auto-reload
uvicorn main:app --reload
```

### Production Deployment

For production, consider:

1. Using a production ASGI server (Gunicorn + Uvicorn workers)
2. Adding authentication and authorization
3. Implementing rate limiting
4. Using a proper database for session storage
5. Adding HTTPS/SSL certificates
6. Containerizing with Docker

### License

MIT License - see LICENSE file for details
