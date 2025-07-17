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

# NEW CRUD FUNCTIONS FOR JIRA

def update_jira_ticket(ticket_id: str, summary: str = None, description: str = None, status: str = None, assignee: str = None) -> dict:
    """Updates an existing Jira ticket with new information."""
    print(f"Tool 'update_jira_ticket' called for ticket: {ticket_id}")
    
    if not all([ATLASSIAN_URL, ATLASSIAN_EMAIL, ATLASSIAN_TOKEN]):
        print("--> Running in MOCK MODE.")
        return {
            "success": True,
            "ticket_id": ticket_id,
            "message": f"Mock update completed for {ticket_id}",
            "url": f"https://mock-jira.com/browse/{ticket_id}"
        }
    
    print("--> Running in LIVE MODE.")
    try:
        api_url = f"{ATLASSIAN_URL}/rest/api/3/issue/{ticket_id}"
        auth = requests.auth.HTTPBasicAuth(ATLASSIAN_EMAIL, ATLASSIAN_TOKEN)
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        
        # Build update payload
        fields = {}
        if summary:
            fields["summary"] = summary
        if description:
            fields["description"] = {
                "type": "doc",
                "version": 1,
                "content": [{"type": "paragraph", "content": [{"type": "text", "text": description}]}]
            }
        if assignee:
            fields["assignee"] = {"name": assignee}
        
        payload = {"fields": fields}
        
        # Handle status transition if provided
        if status:
            # First, get available transitions
            transitions_url = f"{ATLASSIAN_URL}/rest/api/3/issue/{ticket_id}/transitions"
            transitions_response = requests.get(transitions_url, headers={"Accept": "application/json"}, auth=auth)
            if transitions_response.status_code == 200:
                transitions = transitions_response.json().get("transitions", [])
                for transition in transitions:
                    if transition.get("to", {}).get("name", "").lower() == status.lower():
                        # Execute the transition
                        transition_payload = {"transition": {"id": transition["id"]}}
                        transition_response = requests.post(
                            f"{ATLASSIAN_URL}/rest/api/3/issue/{ticket_id}/transitions",
                            data=json.dumps(transition_payload),
                            headers=headers,
                            auth=auth
                        )
                        if transition_response.status_code != 204:
                            return {"success": False, "error": f"Failed to update status: {transition_response.text}"}
                        break
        
        # Update other fields
        response = requests.put(api_url, data=json.dumps(payload), headers=headers, auth=auth)
        
        if response.status_code == 204:  # 204 No Content is success for PUT
            return {
                "success": True,
                "ticket_id": ticket_id,
                "message": f"Successfully updated {ticket_id}",
                "url": f"{ATLASSIAN_URL}/browse/{ticket_id}"
            }
        else:
            return {"success": False, "error": f"Jira API error: {response.status_code} - {response.text}"}
    except Exception as e:
        return {"success": False, "error": f"An unexpected error occurred: {str(e)}"}

def delete_jira_ticket(ticket_id: str) -> dict:
    """Deletes a Jira ticket (moves it to trash)."""
    print(f"Tool 'delete_jira_ticket' called for ticket: {ticket_id}")
    
    if not all([ATLASSIAN_URL, ATLASSIAN_EMAIL, ATLASSIAN_TOKEN]):
        print("--> Running in MOCK MODE.")
        return {
            "success": True,
            "ticket_id": ticket_id,
            "message": f"Mock deletion completed for {ticket_id}",
            "url": f"https://mock-jira.com/browse/{ticket_id}"
        }
    
    print("--> Running in LIVE MODE.")
    try:
        api_url = f"{ATLASSIAN_URL}/rest/api/3/issue/{ticket_id}"
        auth = requests.auth.HTTPBasicAuth(ATLASSIAN_EMAIL, ATLASSIAN_TOKEN)
        headers = {"Accept": "application/json"}
        
        response = requests.delete(api_url, headers=headers, auth=auth)
        
        if response.status_code == 204:  # 204 No Content is success for DELETE
            return {
                "success": True,
                "ticket_id": ticket_id,
                "message": f"Successfully deleted {ticket_id}",
                "url": f"{ATLASSIAN_URL}/browse/{ticket_id}"
            }
        else:
            return {"success": False, "error": f"Jira API error: {response.status_code} - {response.text}"}
    except Exception as e:
        return {"success": False, "error": f"An unexpected error occurred: {str(e)}"}

# NEW CRUD FUNCTIONS FOR CONFLUENCE

def create_confluence_page(space_key: str, title: str, content: str, parent_page_id: str = None) -> dict:
    """Creates a new Confluence page."""
    print(f"Tool 'create_confluence_page' called for space: {space_key}")
    
    confluence_url = os.getenv("CONFLUENCE_URL", ATLASSIAN_URL)
    confluence_email = os.getenv("CONFLUENCE_EMAIL", ATLASSIAN_EMAIL)
    confluence_token = os.getenv("CONFLUENCE_TOKEN", ATLASSIAN_TOKEN)
    
    if not all([confluence_url, confluence_email, confluence_token]):
        print("--> Running in MOCK MODE.")
        page_id = "12345"
        return {
            "success": True,
            "page_id": page_id,
            "title": title,
            "url": f"https://mock-confluence.com/pages/viewpage.action?pageId={page_id}"
        }
    
    print("--> Running in LIVE MODE.")
    try:
        api_url = f"{confluence_url}/wiki/rest/api/content"
        auth = requests.auth.HTTPBasicAuth(confluence_email, confluence_token)
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        
        payload = {
            "type": "page",
            "title": title,
            "space": {"key": space_key},
            "body": {
                "storage": {
                    "value": content,
                    "representation": "storage"
                }
            }
        }
        
        if parent_page_id:
            payload["ancestors"] = [{"id": parent_page_id}]
        
        response = requests.post(api_url, data=json.dumps(payload), headers=headers, auth=auth)
        
        if response.status_code == 200:
            data = response.json()
            return {
                "success": True,
                "page_id": data.get("id"),
                "title": title,
                "url": f"{confluence_url}/wiki/pages/viewpage.action?pageId={data.get('id')}"
            }
        else:
            return {"success": False, "error": f"Confluence API error: {response.status_code} - {response.text}"}
    except Exception as e:
        return {"success": False, "error": f"An unexpected error occurred: {str(e)}"}

def get_confluence_page(page_id: str) -> dict:
    """Retrieves a specific Confluence page by its ID."""
    print(f"Tool 'get_confluence_page' called for page: {page_id}")
    
    confluence_url = os.getenv("CONFLUENCE_URL", ATLASSIAN_URL)
    confluence_email = os.getenv("CONFLUENCE_EMAIL", ATLASSIAN_EMAIL)
    confluence_token = os.getenv("CONFLUENCE_TOKEN", ATLASSIAN_TOKEN)
    
    if not all([confluence_url, confluence_email, confluence_token]):
        print("--> Running in MOCK MODE.")
        return {
            "success": True,
            "page_id": page_id,
            "title": "Sample Confluence Page",
            "content": "This is sample content for the page...",
            "url": f"https://mock-confluence.com/pages/viewpage.action?pageId={page_id}"
        }
    
    print("--> Running in LIVE MODE.")
    try:
        api_url = f"{confluence_url}/wiki/rest/api/content/{page_id}?expand=body.storage"
        auth = requests.auth.HTTPBasicAuth(confluence_email, confluence_token)
        headers = {"Accept": "application/json"}
        
        response = requests.get(api_url, headers=headers, auth=auth)
        
        if response.status_code == 200:
            data = response.json()
            return {
                "success": True,
                "page_id": data.get("id"),
                "title": data.get("title"),
                "content": data.get("body", {}).get("storage", {}).get("value", ""),
                "url": f"{confluence_url}/wiki/pages/viewpage.action?pageId={data.get('id')}"
            }
        else:
            return {"success": False, "error": f"Confluence API error: {response.status_code} - {response.text}"}
    except Exception as e:
        return {"success": False, "error": f"An unexpected error occurred: {str(e)}"}

def update_confluence_page(page_id: str, title: str = None, content: str = None) -> dict:
    """Updates an existing Confluence page."""
    print(f"Tool 'update_confluence_page' called for page: {page_id}")
    
    confluence_url = os.getenv("CONFLUENCE_URL", ATLASSIAN_URL)
    confluence_email = os.getenv("CONFLUENCE_EMAIL", ATLASSIAN_EMAIL)
    confluence_token = os.getenv("CONFLUENCE_TOKEN", ATLASSIAN_TOKEN)
    
    if not all([confluence_url, confluence_email, confluence_token]):
        print("--> Running in MOCK MODE.")
        return {
            "success": True,
            "page_id": page_id,
            "message": f"Mock update completed for page {page_id}",
            "url": f"https://mock-confluence.com/pages/viewpage.action?pageId={page_id}"
        }
    
    print("--> Running in LIVE MODE.")
    try:
        # First get the current page to get the version
        get_url = f"{confluence_url}/wiki/rest/api/content/{page_id}"
        auth = requests.auth.HTTPBasicAuth(confluence_email, confluence_token)
        headers = {"Accept": "application/json"}
        
        get_response = requests.get(get_url, headers=headers, auth=auth)
        if get_response.status_code != 200:
            return {"success": False, "error": f"Failed to get page: {get_response.text}"}
        
        current_data = get_response.json()
        version = current_data.get("version", {}).get("number", 1)
        
        # Build update payload
        payload = {
            "version": {"number": version + 1}
        }
        
        if title:
            payload["title"] = title
        if content:
            payload["body"] = {
                "storage": {
                    "value": content,
                    "representation": "storage"
                }
            }
        
        # Update the page
        update_url = f"{confluence_url}/wiki/rest/api/content/{page_id}"
        headers["Content-Type"] = "application/json"
        response = requests.put(update_url, data=json.dumps(payload), headers=headers, auth=auth)
        
        if response.status_code == 200:
            return {
                "success": True,
                "page_id": page_id,
                "message": f"Successfully updated page {page_id}",
                "url": f"{confluence_url}/wiki/pages/viewpage.action?pageId={page_id}"
            }
        else:
            return {"success": False, "error": f"Confluence API error: {response.status_code} - {response.text}"}
    except Exception as e:
        return {"success": False, "error": f"An unexpected error occurred: {str(e)}"}

def delete_confluence_page(page_id: str) -> dict:
    """Deletes a Confluence page."""
    print(f"Tool 'delete_confluence_page' called for page: {page_id}")
    
    confluence_url = os.getenv("CONFLUENCE_URL", ATLASSIAN_URL)
    confluence_email = os.getenv("CONFLUENCE_EMAIL", ATLASSIAN_EMAIL)
    confluence_token = os.getenv("CONFLUENCE_TOKEN", ATLASSIAN_TOKEN)
    
    if not all([confluence_url, confluence_email, confluence_token]):
        print("--> Running in MOCK MODE.")
        return {
            "success": True,
            "page_id": page_id,
            "message": f"Mock deletion completed for page {page_id}",
            "url": f"https://mock-confluence.com/pages/viewpage.action?pageId={page_id}"
        }
    
    print("--> Running in LIVE MODE.")
    try:
        api_url = f"{confluence_url}/wiki/rest/api/content/{page_id}"
        auth = requests.auth.HTTPBasicAuth(confluence_email, confluence_token)
        headers = {"Accept": "application/json"}
        
        response = requests.delete(api_url, headers=headers, auth=auth)
        
        if response.status_code == 204:  # 204 No Content is success for DELETE
            return {
                "success": True,
                "page_id": page_id,
                "message": f"Successfully deleted page {page_id}",
                "url": f"{confluence_url}/wiki/pages/viewpage.action?pageId={page_id}"
            }
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
            ),
            # NEW JIRA CRUD TOOLS
            Tool(
                name="update_jira_ticket",
                description="Updates an existing Jira ticket with new summary, description, status, or assignee.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "ticket_id": {"type": "string", "description": "The ID of the Jira ticket to update (e.g., 'PROJ-123')"},
                        "summary": {"type": "string", "description": "New summary/title for the ticket (optional)"},
                        "description": {"type": "string", "description": "New description for the ticket (optional)"},
                        "status": {"type": "string", "description": "New status for the ticket (e.g., 'In Progress', 'Done') (optional)"},
                        "assignee": {"type": "string", "description": "Username of the new assignee (optional)"}
                    },
                    "required": ["ticket_id"]
                }
            ),
            Tool(
                name="delete_jira_ticket",
                description="Deletes a Jira ticket (moves it to trash).",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "ticket_id": {"type": "string", "description": "The ID of the Jira ticket to delete (e.g., 'PROJ-123')"}
                    },
                    "required": ["ticket_id"]
                }
            ),
            # NEW CONFLUENCE CRUD TOOLS
            Tool(
                name="create_confluence_page",
                description="Creates a new Confluence page in a specified space.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "space_key": {"type": "string", "description": "The key of the Confluence space (e.g., 'TEAM')"},
                        "title": {"type": "string", "description": "The title of the new page"},
                        "content": {"type": "string", "description": "The content of the page (can include Confluence markup)"},
                        "parent_page_id": {"type": "string", "description": "ID of the parent page (optional, for creating sub-pages)"}
                    },
                    "required": ["space_key", "title", "content"]
                }
            ),
            Tool(
                name="get_confluence_page",
                description="Retrieves a specific Confluence page by its ID.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "page_id": {"type": "string", "description": "The ID of the Confluence page to retrieve"}
                    },
                    "required": ["page_id"]
                }
            ),
            Tool(
                name="update_confluence_page",
                description="Updates an existing Confluence page with new title and/or content.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "page_id": {"type": "string", "description": "The ID of the Confluence page to update"},
                        "title": {"type": "string", "description": "New title for the page (optional)"},
                        "content": {"type": "string", "description": "New content for the page (optional)"}
                    },
                    "required": ["page_id"]
                }
            ),
            Tool(
                name="delete_confluence_page",
                description="Deletes a Confluence page.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "page_id": {"type": "string", "description": "The ID of the Confluence page to delete"}
                    },
                    "required": ["page_id"]
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
        # NEW JIRA CRUD HANDLERS
        elif name == "update_jira_ticket":
            ticket_id = arguments.get("ticket_id")
            if not ticket_id:
                result = {"success": False, "error": "ticket_id is required"}
            else:
                summary = arguments.get("summary")
                description = arguments.get("description")
                status = arguments.get("status")
                assignee = arguments.get("assignee")
                result = update_jira_ticket(str(ticket_id), summary, description, status, assignee)
        elif name == "delete_jira_ticket":
            ticket_id = arguments.get("ticket_id")
            if not ticket_id:
                result = {"success": False, "error": "ticket_id is required"}
            else:
                result = delete_jira_ticket(str(ticket_id))
        # NEW CONFLUENCE CRUD HANDLERS
        elif name == "create_confluence_page":
            space_key = arguments.get("space_key")
            title = arguments.get("title")
            content = arguments.get("content")
            parent_page_id = arguments.get("parent_page_id")
            
            if not all([space_key, title, content]):
                result = {"success": False, "error": "Missing required arguments: space_key, title, content"}
            else:
                result = create_confluence_page(str(space_key), str(title), str(content), parent_page_id)
        elif name == "get_confluence_page":
            page_id = arguments.get("page_id")
            if not page_id:
                result = {"success": False, "error": "page_id is required"}
            else:
                result = get_confluence_page(str(page_id))
        elif name == "update_confluence_page":
            page_id = arguments.get("page_id")
            if not page_id:
                result = {"success": False, "error": "page_id is required"}
            else:
                title = arguments.get("title")
                content = arguments.get("content")
                result = update_confluence_page(str(page_id), title, content)
        elif name == "delete_confluence_page":
            page_id = arguments.get("page_id")
            if not page_id:
                result = {"success": False, "error": "page_id is required"}
            else:
                result = delete_confluence_page(str(page_id))
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
