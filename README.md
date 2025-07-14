# Atlassian & Slack MCP Server

A Model Context Protocol (MCP) server that provides tools for interacting with Atlassian Jira and Slack services.

## Phase 1: Foundation and Jira Proof-of-Concept

This is the initial phase focusing on establishing the foundation and implementing Jira integration.

### Features

- **Jira Ticket Lookup**: Retrieve ticket details by ID
- **Jira Ticket Creation**: Create new tickets in Jira projects
- **Jira Ticket Search**: Find tickets using flexible JQL queries
- **Confluence Page Search**: Find Confluence pages by text query
- **Mock Mode**: Test functionality without real credentials
- **Live Mode**: Connect to real Jira/Confluence instances with credentials

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
ATLASSIAN_URL=https://your-domain.atlassian.net
ATLASSIAN_EMAIL=your-email@example.com
ATLASSIAN_TOKEN=your-api-token
```

### Usage

1. **Mock Mode** (default):
   ```bash
   python main.py
   ```
   - Works without any credentials
   - Test with ticket ID "PROJ-123"

2. **Live Mode**:
   - Add your Atlassian credentials to `.env`
   - Run the same command: `python main.py`

### Testing

Test the Jira ticket lookup function:
```python
from main import get_jira_ticket
result = get_jira_ticket("PROJ-123")
print(result)
```

Test the Jira ticket creation function:
```python
from main import create_jira_ticket
result = create_jira_ticket("PROJ", "Test Summary", "Test Description", "Task")
print(result)
```

### Usage Examples

#### Search Jira Tickets
```python
from main import search_jira_tickets
result = search_jira_tickets("project = PROJ AND status = 'In Progress'")
print(result)
```

#### Search Confluence Pages
```python
from main import search_confluence_pages
result = search_confluence_pages("How to set up the VPN")
print(result)
```

### MCP Tools

- `get_jira_ticket`: Retrieves summary, status, and assignee for a Jira ticket
- `create_jira_ticket`: Creates a new issue (Task, Bug, Story) in a specified Jira project
- `search_jira_tickets`: Searches for Jira tickets using a JQL query and returns a list of matching tickets (ID, summary, status, URL)
- `search_confluence_pages`: Searches Confluence for pages matching a text query and returns a list of relevant pages (title, snippet, URL)

### Development Status

- ✅ Basic MCP server structure
- ✅ Jira ticket lookup (mock and live modes)
- ✅ Jira ticket creation (mock and live modes)
- ✅ Jira ticket search (mock and live modes)
- ✅ Confluence page search (mock and live modes)
- ✅ Environment variable configuration
- ✅ Error handling
- 🔄 Slack integration (planned)
- 🔄 Additional Jira/Confluence features (planned)

### Requirements

- Python 3.8+
- `python-dotenv` for environment variable management
- `requests` for HTTP API calls
- `mcp` for MCP server functionality 