# Atlassian & Slack MCP Server

A Model Context Protocol (MCP) server that provides tools for interacting with Atlassian Jira and Slack services.

## Phase 1: Foundation and Jira Proof-of-Concept

This is the initial phase focusing on establishing the foundation and implementing Jira integration.

### Features

- **Jira Ticket Lookup**: Retrieve ticket details by ID
- **Jira Ticket Creation**: Create new tickets in Jira projects
- **Mock Mode**: Test functionality without real credentials
- **Live Mode**: Connect to real Jira instance with proper credentials

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

### MCP Tools

- `get_jira_ticket`: Retrieves summary, status, and assignee for a Jira ticket
- `create_jira_ticket`: Creates a new issue (Task, Bug, Story) in a specified Jira project

### Development Status

- ✅ Basic MCP server structure
- ✅ Jira ticket lookup (mock and live modes)
- ✅ Jira ticket creation (mock and live modes)
- ✅ Environment variable configuration
- ✅ Error handling
- 🔄 Slack integration (planned)
- 🔄 Additional Jira features (planned)

### Requirements

- Python 3.8+
- `python-dotenv` for environment variable management
- `requests` for HTTP API calls
- `mcp` for MCP server functionality 