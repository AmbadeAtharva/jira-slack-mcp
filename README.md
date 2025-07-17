# Atlassian & Slack MCP Server

A Model Context Protocol (MCP) server that provides comprehensive CRUD (Create, Read, Update, Delete) operations for Atlassian Jira tickets and Confluence pages, integrated with Slack for natural language interaction.

## 🚀 **Phase 2: Full CRUD Operations with Natural Language Processing**

This phase extends the foundation with complete CRUD functionality for both Jira and Confluence, plus intelligent natural language processing using Llama 3.2.

### ✨ **New Features**

#### **Jira CRUD Operations:**
- **Create** - Create new tickets with custom fields
- **Read** - Retrieve ticket details, status, and assignee
- **Update** - Modify ticket summary, description, status, and assignee
- **Delete** - Remove tickets (moves to trash)

#### **Confluence CRUD Operations:**
- **Create** - Create new pages with custom content
- **Read** - Retrieve page content and metadata
- **Update** - Modify page title and content
- **Delete** - Remove pages

#### **Advanced Features:**
- **Natural Language Processing** - Use Llama 3.2 for intelligent command interpretation
- **Beautiful Formatting** - User-friendly responses with emojis and structured output
- **Mock Mode** - Test functionality without real credentials
- **Live Mode** - Connect to real Jira/Confluence instances with credentials
- **Error Handling** - Robust error handling with clear messages

### Installation

1. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Create a `.env` file (optional for mock mode):
   ```bash
   touch .env
   ```

### Configuration

For live mode, add the following to your `.env` file:
```
# Atlassian Configuration
ATLASSIAN_URL=https://your-domain.atlassian.net
ATLASSIAN_EMAIL=your-email@example.com
ATLASSIAN_TOKEN=your-api-token

# Confluence Configuration (optional, falls back to Jira config)
CONFLUENCE_URL=https://your-domain.atlassian.net
CONFLUENCE_EMAIL=your-email@example.com
CONFLUENCE_TOKEN=your-api-token

# Slack Configuration
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_APP_TOKEN=xapp-your-app-token
```

### Usage

#### **MCP Server (Direct)**
1. **Mock Mode** (default):
   ```bash
   python3 main.py
   ```
   - Works without any credentials
   - Test with ticket ID "PROJ-123"

2. **Live Mode**:
   - Add your Atlassian credentials to `.env`
   - Run the same command: `python3 main.py`

#### **Slack Bot (Recommended)**
```bash
python3 slack_bot.py
```

### Testing

#### **Direct MCP Testing**
```python
from main import get_jira_ticket, create_jira_ticket, update_jira_ticket, delete_jira_ticket
from main import create_confluence_page, get_confluence_page, update_confluence_page, delete_confluence_page

# Jira CRUD
result = get_jira_ticket("PROJ-123")
result = create_jira_ticket("PROJ", "Test Summary", "Test Description", "Task")
result = update_jira_ticket("PROJ-123", status="In Progress", assignee="john.doe")
result = delete_jira_ticket("PROJ-123")

# Confluence CRUD
result = create_confluence_page("TEAM", "Test Page", "Test content")
result = get_confluence_page("12345")
result = update_confluence_page("12345", title="Updated Title", content="Updated content")
result = delete_confluence_page("12345")
```

### Natural Language Examples

#### **Jira Operations**
```
@Bot Get ticket PROJ-123
@Bot Create a bug ticket for login issues
@Bot Update ticket PROJ-123 status to In Progress
@Bot Assign ticket PROJ-123 to john.doe
@Bot Delete ticket PROJ-123
@Bot Search for tickets from last 2 days
```

#### **Confluence Operations**
```
@Bot Create a new Confluence page about API docs
@Bot Get Confluence page 12345
@Bot Update Confluence page 12345 with new content
@Bot Delete Confluence page 12345
@Bot Find API documentation in Confluence
```

### 🛠️ **Available MCP Tools**

#### **Jira Tools:**
- `get_jira_ticket(ticket_id)` - Retrieve ticket details, status, and assignee
- `create_jira_ticket(project_key, summary, description, issue_type)` - Create new tickets
- `update_jira_ticket(ticket_id, summary, description, status, assignee)` - Update existing tickets
- `delete_jira_ticket(ticket_id)` - Delete tickets (moves to trash)
- `search_jira_tickets(jql_query)` - Search tickets using JQL queries

#### **Confluence Tools:**
- `create_confluence_page(space_key, title, content, parent_page_id)` - Create new pages
- `get_confluence_page(page_id)` - Retrieve page content and metadata
- `update_confluence_page(page_id, title, content)` - Update existing pages
- `delete_confluence_page(page_id)` - Delete pages
- `search_confluence_pages(query)` - Search pages by text query

### Development Status

#### **✅ Completed Features:**
- ✅ Basic MCP server structure
- ✅ Jira CRUD operations (Create, Read, Update, Delete)
- ✅ Confluence CRUD operations (Create, Read, Update, Delete)
- ✅ Natural language processing with Llama 3.2
- ✅ Beautiful response formatting with emojis
- ✅ Mock and live modes for all operations
- ✅ Environment variable configuration
- ✅ Robust error handling
- ✅ Slack bot integration
- ✅ Tool listing and help system

#### **🔄 Planned Features:**
- 🔄 Conversation memory across messages
- 🔄 Interactive Slack components (buttons, dropdowns)
- 🔄 Scheduled tasks and notifications
- 🔄 User preferences and defaults
- 🔄 Advanced analytics and insights

### Requirements

- Python 3.8+
- `python-dotenv` for environment variable management
- `requests` for HTTP API calls
- `mcp` for MCP server functionality
- `slack_bolt` for Slack bot integration
- `ollama` for local LLM (Llama 3.2 recommended) 

## 🤖 **Slack Bot Integration**

The Slack bot provides natural language interaction with all Jira and Confluence tools using Llama 3.2 for intelligent command interpretation.

### Setup
1. **Install Ollama** and pull Llama 3.2:
   ```bash
   # Install Ollama from https://ollama.com/
   ollama pull llama3.2
   ollama run llama3.2
   ```

2. **Create a Slack App** and install it to your workspace. Get the `SLACK_BOT_TOKEN` and `SLACK_APP_TOKEN` from your Slack App configuration.

3. **Add credentials to `.env`**:
   ```env
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_APP_TOKEN=xapp-...
   ```

4. **Install dependencies**:
   ```bash
   pip install slack_bolt
   ```

### Running the Bot
```bash
python3 slack_bot.py
```

### Natural Language Usage
The bot understands natural language commands and automatically routes them to the appropriate tools:

#### **Jira Commands:**
```
@Bot Get ticket PROJ-123
@Bot Create a bug ticket for login issues
@Bot Update ticket PROJ-123 status to In Progress
@Bot Assign ticket PROJ-123 to john.doe
@Bot Delete ticket PROJ-123
@Bot Search for tickets from last 2 days
```

#### **Confluence Commands:**
```
@Bot Create a new Confluence page about API docs
@Bot Get Confluence page 12345
@Bot Update Confluence page 12345 with new content
@Bot Delete Confluence page 12345
@Bot Find API documentation in Confluence
```

#### **Help Commands:**
```
@Bot What tools do you have?
@Bot List available tools
@Bot Help
```

### Features
- **Intelligent Parsing**: Uses Llama 3.2 to understand natural language
- **Beautiful Formatting**: Responses include emojis and structured formatting
- **Error Handling**: Clear error messages when things go wrong
- **Tool Discovery**: Built-in help system to list available tools 