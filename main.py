#!/usr/bin/env python3
# main.py
# This is the main file for our Atlassian & Slack MCP Server.
# Phase 2: Added 'create_jira_ticket' tool.

# --- 1. Import Necessary Libraries ---
import os
import requests
from dotenv import load_dotenv
import asyncio
import json
from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.lowlevel import NotificationOptions
from mcp.server.stdio import stdio_server
from mcp.types import ServerCapabilities, Tool, TextContent

# --- 2. Load Configuration ---
load_dotenv()
ATLASSIAN_URL = os.getenv("ATLASSIAN_URL")
ATLASSIAN_EMAIL = os.getenv("ATLASSIAN_EMAIL")
ATLASSIAN_TOKEN = os.getenv("ATLASSIAN_TOKEN")

# --- 3. Define Core Tool Functions ---

def get_jira_ticket(ticket_id: str) -> dict:
    """Fetches details for a specific Jira ticket."""
    print(f"Tool 'get_jira_ticket' called with ID: {ticket_id}")
    if not all([ATLASSIAN_URL, ATLASSIAN_EMAIL, ATLASSIAN_TOKEN]):
        print("--> Running in MOCK MODE.")
        if ticket_id == "PROJ-123":
            return {"success": True, "ticket_id": ticket_id, "summary": "This is a sample ticket summary.", "status": "In Progress", "assignee": "Mock User", "url": f"https://mock-jira.com/browse/{ticket_id}"}
        else:
            return {"success": False, "error": f"Ticket '{ticket_id}' not found in mock data."}
    
    print("--> Running in LIVE MODE.")
    try:
        api_url = f"{ATLASSIAN_URL}/rest/api/3/issue/{ticket_id}"
        auth = requests.auth.HTTPBasicAuth(ATLASSIAN_EMAIL, ATLASSIAN_TOKEN)
        headers = {"Accept": "application/json"}
        response = requests.get(api_url, headers=headers, auth=auth)
        if response.status_code == 200:
            data = response.json()
            fields = data.get("fields", {})
            status = fields.get("status", {}).get("name", "N/A")
            assignee = fields.get("assignee", {}).get("displayName", "Unassigned")
            return {"success": True, "ticket_id": data.get("key"), "summary": fields.get("summary"), "status": status, "assignee": assignee, "url": f"{ATLASSIAN_URL}/browse/{data.get('key')}"}
        else:
            return {"success": False, "error": f"Jira API error: {response.status_code} - {response.text}"}
    except Exception as e:
        return {"success": False, "error": f"An unexpected error occurred: {str(e)}"}

# NEW FUNCTION: create_jira_ticket
def create_jira_ticket(project_key: str, summary: str, description: str, issue_type: str) -> dict:
    """Creates a new ticket in a Jira project."""
    print(f"Tool 'create_jira_ticket' called for project: {project_key}")

    # --- MOCK MODE ---
    if not all([ATLASSIAN_URL, ATLASSIAN_EMAIL, ATLASSIAN_TOKEN]):
        print("--> Running in MOCK MODE.")
        new_ticket_id = f"{project_key}-999" # Create a fake new ticket ID
        return {
            "success": True,
            "ticket_id": new_ticket_id,
            "summary": summary,
            "url": f"https://mock-jira.com/browse/{new_ticket_id}"
        }

    # --- LIVE MODE ---
    print("--> Running in LIVE MODE.")
    try:
        api_url = f"{ATLASSIAN_URL}/rest/api/3/issue"
        auth = requests.auth.HTTPBasicAuth(ATLASSIAN_EMAIL, ATLASSIAN_TOKEN)
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        
        # This is the standard payload structure for creating a Jira issue
        payload = json.dumps({
            "fields": {
                "project": {"key": project_key},
                "summary": summary,
                "description": {
                    "type": "doc",
                    "version": 1,
                    "content": [{"type": "paragraph", "content": [{"type": "text", "text": description}]}]
                },
                "issuetype": {"name": issue_type}
            }
        })

        response = requests.post(api_url, data=payload, headers=headers, auth=auth)

        if response.status_code == 201: # 201 Created is the success code for POST
            data = response.json()
            return {
                "success": True,
                "ticket_id": data.get("key"),
                "summary": summary,
                "url": f"{ATLASSIAN_URL}/browse/{data.get('key')}"
            }
        else:
            return {"success": False, "error": f"Jira API error: {response.status_code} - {response.text}"}
    except Exception as e:
        return {"success": False, "error": f"An unexpected error occurred: {str(e)}"}

# NEW FUNCTION: search_jira_tickets

def search_jira_tickets(jql_query: str) -> dict:
    """Search Jira tickets using a JQL query."""
    print(f"Tool 'search_jira_tickets' called with JQL: {jql_query}")
    if not all([ATLASSIAN_URL, ATLASSIAN_EMAIL, ATLASSIAN_TOKEN]):
        print("--> Running in MOCK MODE.")
        # Return a sample list of tickets
        return {
            "success": True,
            "tickets": [
                {
                    "ticket_id": "PROJ-101",
                    "summary": "Fix login bug",
                    "status": "To Do",
                    "url": "https://mock-jira.com/browse/PROJ-101"
                },
                {
                    "ticket_id": "PROJ-102",
                    "summary": "Update documentation",
                    "status": "In Progress",
                    "url": "https://mock-jira.com/browse/PROJ-102"
                }
            ]
        }
    print("--> Running in LIVE MODE.")
    try:
        api_url = f"{ATLASSIAN_URL}/rest/api/3/search"
        auth = requests.auth.HTTPBasicAuth(ATLASSIAN_EMAIL, ATLASSIAN_TOKEN)
        headers = {"Accept": "application/json"}
        params = {"jql": jql_query, "maxResults": 10}
        response = requests.get(api_url, headers=headers, auth=auth, params=params)
        if response.status_code == 200:
            data = response.json()
            tickets = []
            for issue in data.get("issues", []):
                fields = issue.get("fields", {})
                tickets.append({
                    "ticket_id": issue.get("key"),
                    "summary": fields.get("summary"),
                    "status": fields.get("status", {}).get("name", "N/A"),
                    "url": f"{ATLASSIAN_URL}/browse/{issue.get('key')}"
                })
            return {"success": True, "tickets": tickets}
        else:
            return {"success": False, "error": f"Jira API error: {response.status_code} - {response.text}"}
    except Exception as e:
        return {"success": False, "error": f"An unexpected error occurred: {str(e)}"}

# NEW FUNCTION: search_confluence_pages

def search_confluence_pages(query: str) -> dict:
    """Search Confluence pages using a text query."""
    print(f"Tool 'search_confluence_pages' called with query: {query}")
    # We'll use a separate set of env vars for Confluence, but fallback to Jira if not set
    confluence_url = os.getenv("CONFLUENCE_URL", ATLASSIAN_URL)
    confluence_email = os.getenv("CONFLUENCE_EMAIL", ATLASSIAN_EMAIL)
    confluence_token = os.getenv("CONFLUENCE_TOKEN", ATLASSIAN_TOKEN)
    if not all([confluence_url, confluence_email, confluence_token]):
        print("--> Running in MOCK MODE.")
        return {
            "success": True,
            "pages": [
                {
                    "title": "How to set up the VPN",
                    "snippet": "Step-by-step guide to configure VPN access...",
                    "url": "https://mock-confluence.com/pages/viewpage.action?pageId=12345"
                },
                {
                    "title": "Q3 marketing plan",
                    "snippet": "This page outlines the marketing plan for Q3...",
                    "url": "https://mock-confluence.com/pages/viewpage.action?pageId=67890"
                }
            ]
        }
    print("--> Running in LIVE MODE.")
    try:
        api_url = f"{confluence_url}/wiki/rest/api/search"
        auth = requests.auth.HTTPBasicAuth(confluence_email, confluence_token)
        headers = {"Accept": "application/json"}
        params = {"cql": f"text ~ '{query}'", "limit": 10}
        response = requests.get(api_url, headers=headers, auth=auth, params=params)
        if response.status_code == 200:
            data = response.json()
            pages = []
            for result in data.get("results", []):
                title = result.get("title", "Untitled")
                snippet = result.get("excerpt", "")
                # Build the URL to the page
                page_id = result.get("content", {}).get("id") or result.get("_id") or result.get("id")
                url = f"{confluence_url}/wiki/pages/viewpage.action?pageId={page_id}" if page_id else confluence_url
                pages.append({
                    "title": title,
                    "snippet": snippet,
                    "url": url
                })
            return {"success": True, "pages": pages}
        else:
            return {"success": False, "error": f"Confluence API error: {response.status_code} - {response.text}"}
    except Exception as e:
        return {"success": False, "error": f"An unexpected error occurred: {str(e)}"}

# --- 4. Main Server Execution Block ---
if __name__ == "__main__":
    server = Server("atlassian-mcp-server")

    @server.list_tools()
    async def handle_list_tools():
        """Return the list of available tools."""
        return [
            Tool(
                name="get_jira_ticket",
                description="Retrieves the summary, status, and assignee for a specific Jira ticket by its ID.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "ticket_id": {"type": "string", "description": "The ID of the Jira ticket (e.g., 'PROJ-123')"}
                    },
                    "required": ["ticket_id"]
                }
            ),
            # NEW TOOL DEFINITION
            Tool(
                name="create_jira_ticket",
                description="Creates a new issue (e.g., Task, Bug, Story) in a specified Jira project.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_key": {"type": "string", "description": "The key for the Jira project (e.g., 'PROJ')."},
                        "summary": {"type": "string", "description": "The title or summary of the new issue."},
                        "description": {"type": "string", "description": "The detailed description for the issue."},
                        "issue_type": {"type": "string", "description": "The type of issue to create (e.g., 'Task', 'Bug', 'Story')."}
                    },
                    "required": ["project_key", "summary", "description", "issue_type"]
                }
            ),
            Tool(
                name="search_jira_tickets",
                description="Searches for Jira tickets using a JQL query and returns a list of matching tickets (ID, summary, status, URL).",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "jql_query": {"type": "string", "description": "A Jira Query Language (JQL) string to search for tickets."}
                    },
                    "required": ["jql_query"]
                }
            ),
            Tool(
                name="search_confluence_pages",
                description="Searches Confluence for pages matching a text query and returns a list of relevant pages (title, snippet, URL).",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "A text query to search for Confluence pages."}
                    },
                    "required": ["query"]
                }
            )
        ]

    @server.call_tool()
    async def handle_call_tool(name: str, arguments: dict):
        """Handle tool calls."""
        result = {}
        if name == "get_jira_ticket":
            ticket_id = arguments.get("ticket_id")
            if not ticket_id:
                result = {"success": False, "error": "ticket_id is required"}
            else:
                result = get_jira_ticket(ticket_id)

        # NEW TOOL HANDLER
        elif name == "create_jira_ticket":
            # Extract arguments using .get() to avoid errors if one is missing
            project_key = arguments.get("project_key")
            summary = arguments.get("summary")
            description = arguments.get("description")
            issue_type = arguments.get("issue_type")
            
            if not all([project_key, summary, description, issue_type]):
                result = {"success": False, "error": "Missing one or more required arguments: project_key, summary, description, issue_type"}
            else:
                # Type safety: ensure all values are strings
                result = create_jira_ticket(
                    str(project_key), 
                    str(summary), 
                    str(description), 
                    str(issue_type)
                )
        elif name == "search_jira_tickets":
            jql_query = arguments.get("jql_query")
            if not jql_query:
                result = {"success": False, "error": "jql_query is required"}
            else:
                result = search_jira_tickets(str(jql_query))
        elif name == "search_confluence_pages":
            query = arguments.get("query")
            if not query:
                result = {"success": False, "error": "query is required"}
            else:
                result = search_confluence_pages(str(query))
        else:
            result = {"success": False, "error": f"Unknown tool: {name}"}
        
        return [TextContent(type="text", text=str(result))]

    async def main():
        async with stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="atlassian-mcp-server",
                    server_version="1.0.0",
                    capabilities=server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={},
                    ),
                ),
            )

    print("=============================================")
    print("  Atlassian MCP Server - Phase 2 Started   ")
    print("  Mode: Mock (unless .env is configured)   ")
    print("  Tools Registered: get_jira_ticket, create_jira_ticket")
    print("=============================================")
    print("\nServer is listening for requests. Connect with an MCP client.")
    
    asyncio.run(main())
