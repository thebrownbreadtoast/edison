# Edison - AI-Powered ChatGPT Interface

Moshi-Moshi, I am Edison. Stella is unavailable right now so I will be dealing with all your queries.

## 🚀 Features

A sophisticated AI chat interface powered by OpenAI's ChatKit agents, featuring:

- 🤖 **OpenAI ChatKit Integration** - Advanced AI agent workflows
- 🔍 **Vector Store Search** - Knowledge-based responses using OpenAI vector stores
- 🎨 **Modern ChatGPT-like UI** - Responsive, dark-themed interface
- 💬 **Real-time Chat** - Seamless conversation experience
- 🔐 **Secure Configuration** - Environment-based secrets management
- 📝 **Session Management** - Per-session message history
- ⚡ **FastAPI Backend** - High-performance async API
- 🛡️ **Error Handling** - Robust fallback mechanisms

## 🏗️ Architecture

```
edison/
├── main.py              # FastAPI app with OpenAI ChatKit integration
├── requirements.txt     # Python dependencies
├── .env                 # Environment variables (not in git)
├── .env.example         # Template for environment setup
└── README.md           # This documentation
```

## 🚀 Quick Start

### 1. Environment Setup

```bash
# Clone and navigate to project
cd edison

# Copy environment template
cp .env.example .env

# Edit .env with your configuration
# Add your OpenAI API key and other settings
```

### 2. Configure Environment Variables

Edit `.env` file with your settings:

```env
# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here

# OpenAI ChatKit Configuration  
VECTOR_STORE_ID=your_vector_store_id_here
WORKFLOW_ID=your_workflow_id_here

# Server Configuration
HOST=0.0.0.0
PORT=8000
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the Application

```bash
python main.py
```

Or using uvicorn directly:
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 5. Access the Interface

Navigate to: `http://localhost:8000`

##  License

MIT License - see LICENSE file for details
