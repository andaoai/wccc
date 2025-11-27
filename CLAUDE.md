# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a WeChat API client tool that integrates with 千寻微信框架 (QianXun WeChat Framework) for automated WeChat operations and GLM AI for intelligent data processing. The project specializes in construction industry certificate trading data extraction and transformation from WeChat group messages.

## Development Environment

This project uses `uv` for Python package management.

### Common Commands

**Install dependencies:**
```bash
uv sync
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

**Run tests:**
```bash
uv run pytest
```

**Run the WeChat debug listener:**
```bash
uv run wechat/debug_websocket.py
```

**Test WeChat API group list:**
```bash
uv run wechat/test_get_group_list.py
```

**Test AI certificate splitting:**
```bash
uv run ai/test_cert_split_prompt.py
```

**Test AI WeChat message parsing:**
```bash
uv run ai/test_wechat_msg_prompt.py
```

## Architecture

### WeChat Module (`wechat/`)
The WeChat integration layer handles communication with the QianXun framework:

- **WeChatAPI.py**: Core API client that interfaces with QianXun HTTP API
  - Handles JSON cleaning for malformed responses with control characters
  - Provides methods for WeChat list, status checking, group info, and member nicknames
  - Manages WebSocket connections for real-time message listening
  - Default connection to `http://192.168.1.12:7777`

- **debug_websocket.py**: Debug-focused WebSocket listener
  - Runs message processing in main thread for easier debugging
  - Automatically fetches group names and member nicknames using WeChat API calls
  - Provides detailed message classification and formatting
  - Includes queue-based message handling to prevent blocking

- **test_get_group_list.py**: Test script for group list API functionality

### AI Module (`ai/`)
AI-powered data processing using GLM-4.6 model:

- **glm_agent.py**: GLM AI Agent wrapper around ZhipuAI client
  - Manages conversation history and multiple sessions
  - Supports both sync and streaming chat modes
  - Includes specialized prompts for WeChat chat scenarios
  - Handles error recovery and API key management

- **test_cert_split_prompt.py**: Specialized test for construction industry certificate splitting
  - Uses `cert_split_prompt.md` for AI instructions
  - Tests the AI's ability to normalize certificate names and combinations
  - Handles certificate aliases like "一建" → "一级建造师"

- **test_wechat_msg_prompt.py**: WeChat message parsing test
  - Uses `wechat_msg_prompt.md` for extracting structured data from messages
  - Transforms WeChat group messages into JSON for database import
  - Extracts fields like transaction type, certificates, pricing, location

- **cert_split_prompt.md**: AI prompt for certificate text normalization and splitting

- **wechat_msg_prompt.md**: AI prompt for extracting construction industry trading data from WeChat messages

### Bot Module (`bot/`)
- **wechat_data_collector.py**: (Empty placeholder) Intended for automated data collection functionality

### Data Storage (`data/`)
- **postgres/**: PostgreSQL database storage directory with pgdata

## Key Integration Points

The WeChat module and AI module work together for:
1. **Real-time Message Processing**: WeChat messages are captured via WebSocket and processed through AI for intelligent response generation
2. **Data Transformation**: Unstructured WeChat messages about construction certificate trading are converted to structured JSON format
3. **Certificate Normalization**: AI processes various certificate name formats (aliases, abbreviations) into standardized forms

## Specialized Features

### Construction Industry Focus
- Certificate name normalization (e.g., "一建" → "一级建造师", "二建" → "二级建造师")
- Professional category mapping (e.g., "房建" → "建筑工程", "市政" → "市政公用工程")
- Trading data extraction with pricing, location, and social security status
- Structured JSON output ready for PostgreSQL database import

### AI Prompt System
- Modular prompt files for different AI tasks
- Certificate splitting prompts handle multi-certificate combinations with connectors
- WeChat message parsing prompts extract structured trading information
- Prompts designed for pure JSON output without markdown formatting

## External Dependencies

The project requires:
- **QianXun WeChat Framework** running on `http://192.168.1.12:7777` (HTTP) and `ws://192.168.1.12:7778` (WebSocket)
- **ZhipuAI API** access with valid API key for GLM-4.6 model
- **PostgreSQL** database for data storage (optional but recommended)
- Key Python packages: `zai-sdk`, `websocket-client`, `requests`, `sentence-transformers`, `torch`, `pymilvus`

## Configuration

- WeChat API base URL configurable in WeChatAPI constructor
- GLM API key should be set via `ZHIPUAI_API_KEY` environment variable
- WebSocket connection automatically reconnects on disconnection
- AI conversation history limited to 20 rounds (40 messages) per session

## Module Usage Patterns

### WeChat API Usage
```python
from wechat.WeChatAPI import WeChatAPI

api = WeChatAPI(base_url="http://192.168.1.12:7777")
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

Both modules are designed to work together for building intelligent WeChat automation systems with AI-powered data processing capabilities, specifically optimized for construction industry certificate trading scenarios.