# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a WeChat API client tool that integrates with 千寻微信框架 (QianXun WeChat Framework) for automated WeChat operations and GLM AI for intelligent data processing. The project is structured into modular components for WeChat communication and AI-powered data transformation.

## Development Environment

This project uses `uv` for Python package management.

### Common Commands

**Install dependencies:**
```bash
uv sync
```

**Run the WeChat debug listener:**
```bash
uv run wechat/debug_websocket.py
```

**Test AI data transformation:**
```bash
uv run ai/test_prompt.py
```

**Development dependencies (linting, testing):**
```bash
uv sync --dev
```

**Code formatting:**
```bash
uv run black .
```

**Linting:**
```bash
uv run flake8
```

## Architecture

### WeChat Module (`wechat/`)
The WeChat integration layer handles communication with the QianXun framework:

- **WeChatAPI.py**: Core API client that interfaces with QianXun HTTP API
  - Handles JSON cleaning for malformed responses with control characters
  - Provides methods for WeChat list, status checking, group info, and member nicknames
  - Manages WebSocket connections for real-time message listening

- **debug_websocket.py**: Debug-focused WebSocket listener
  - Runs message processing in main thread for easier debugging
  - Automatically fetches group names and member nicknames using WeChat API calls
  - Provides detailed message classification and formatting
  - Includes queue-based message handling to prevent blocking

### AI Module (`ai/`)
AI-powered data processing using GLM-4.6 model:

- **glm_agent.py**: GLM AI Agent wrapper around ZhipuAI client
  - Manages conversation history and multiple sessions
  - Supports both sync and streaming chat modes
  - Includes specialized prompts for WeChat chat scenarios
  - Handles error recovery and API key management

- **test_prompt.py**: Specialized test for construction industry data transformation
  - Tests the AI's ability to convert unstructured text into structured JSON
  - Validates output format and data quality metrics
  - Includes markdown cleaning for pure JSON extraction

### Key Integration Points

The WeChat module and AI module are designed to work together:
- WeChat messages can be processed through the AI for intelligent responses
- The AI can handle specialized data transformation tasks (like construction industry talent data)
- Both modules support session management and context preservation

### External Dependencies

The project requires:
- **QianXun WeChat Framework** running on `http://127.0.0.1:7777` (HTTP) and `ws://127.0.0.1:7778` (WebSocket)
- **ZhipuAI API** access with valid API key for GLM-4.6 model
- **websocket-client** for WebSocket communication
- **zai-sdk** for GLM AI integration

### API Configuration

- WeChat API base URL defaults to `http://192.168.31.6:7777` (configurable in WeChatAPI constructor)
- GLM API key is embedded in the test file but should be moved to environment variables for production
- WebSocket connection automatically reconnects on disconnection

## Module Usage Patterns

### WeChat API Usage
```python
from wechat.WeChatAPI import WeChatAPI

api = WeChatAPI(base_url="http://127.0.0.1:7777")
wechat_list = api.get_wechat_list()
group_info = api.query_group(group_wxid, bot_wxid)
member_nick = api.get_member_nick(group_wxid, member_wxid, bot_wxid)
```

### AI Agent Usage
```python
from ai.glm_agent import GLMAgent

agent = GLMAgent(api_key="your-api-key")
response = agent.chat("Hello", session_id="user123")
# For specialized data transformation:
response = agent.chat(prompt_with_instructions, temperature=0.1)
```

Both modules are designed to work together for building intelligent WeChat automation systems with AI-powered data processing capabilities.