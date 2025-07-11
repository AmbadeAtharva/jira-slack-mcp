# main.py
# This is the main file for our Atlassian & Slack MCP Server.
# Phase 1: Foundation and Jira Proof-of-Concept

# --- 1. Import Necessary Libraries ---
# We need 'os' and 'dotenv' to handle environment variables for API keys.
# 'requests' is a popular library for making HTTP requests to APIs like Jira's.
# 'mcp_sdk' is the official library for building our MCP server.
import os
import requests
from dotenv import load_dotenv
from mcp import Tool
from mcp.server import Server
from mcp.server.stdio import stdio_server

# --- 2. Load Configuration ---
# This line loads the variables from a file named '.env' in the same directory.
# This is a best practice for keeping secrets like API keys out of your code.
load_dotenv()

# We retrieve the Atlassian credentials from the environment variables.
# If they aren't found, they will default to None.
ATLASSIAN_URL = os.getenv("ATLASSIAN_URL")  # e.g., "https://your-domain.atlassian.net"
ATLASSIAN_EMAIL = os.getenv("ATLASSIAN_EMAIL") # Your email for the Atlassian account
ATLASSIAN_TOKEN = os.getenv("ATLASSIAN_TOKEN") # The API token you generate in Atlassian

# --- 3. Define The Core Function (Our First Tool) ---
# This function contains the actual logic for getting a Jira ticket.
# It's designed to work even if you don't have real credentials yet.

def get_jira_ticket(ticket_id: str) -> dict:
    """
    Fetches details for a specific Jira ticket.

    Args:
        ticket_id: The ID of the Jira ticket (e.g., "PROJ-123").

    Returns:
        A dictionary containing the ticket's details or an error message.
    """
    print(f"Tool 'get_jira_ticket' called with ID: {ticket_id}")

    # --- MOCK MODE ---
    # If we don't have Atlassian credentials, we'll return a sample response.
    # This allows us to test the server without a real Atlassian account.
    if not all([ATLASSIAN_URL, ATLASSIAN_EMAIL, ATLASSIAN_TOKEN]):
        print("--> Running in MOCK MODE (no Atlassian credentials found).")
        # You can test with a known "fake" ticket ID
        if ticket_id == "PROJ-123":
            return {
                "success": True,
                "ticket_id": ticket_id,
                "summary": "This is a sample ticket summary from mock mode.",
                "status": "In Progress",
                "assignee": "Mock User",
                "url": f"https://mock-jira.com/browse/{ticket_id}"
            }
        else:
            return {
                "success": False,
                "error": f"Ticket '{ticket_id}' not found in mock data."
            }

    # --- LIVE MODE ---
    # This part will run only if you provide credentials in your .env file.
    print("--> Running in LIVE MODE.")
    try:
        # Construct the full URL for the Jira API endpoint
        api_url = f"{ATLASSIAN_URL}/rest/api/3/issue/{ticket_id}"

        # Set up authentication using your email and API token
        auth = requests.auth.HTTPBasicAuth(ATLASSIAN_EMAIL, ATLASSIAN_TOKEN)

        # Set headers to indicate we're sending and accepting JSON data
        headers = {
            "Accept": "application/json"
        }

        # Make the GET request to the Jira API
        response = requests.get(api_url, headers=headers, auth=auth)

        # Check if the request was successful
        if response.status_code == 200:
            data = response.json()
            # Extract the relevant fields from the response
            fields = data.get("fields", {})
            status = fields.get("status", {}).get("name", "N/A")
            assignee = fields.get("assignee")
            assignee_name = assignee.get("displayName", "Unassigned") if assignee else "Unassigned"

            return {
                "success": True,
                "ticket_id": data.get("key"),
                "summary": fields.get("summary"),
                "status": status,
                "assignee": assignee_name,
                "url": f"{ATLASSIAN_URL}/browse/{data.get('key')}"
            }
        elif response.status_code == 404:
            return {"success": False, "error": f"Ticket '{ticket_id}' not found."}
        else:
            # Handle other potential errors (e.g., permissions)
            return {"success": False, "error": f"Jira API error: {response.status_code} - {response.text}"}

    except Exception as e:
        print(f"An exception occurred: {e}")
        return {"success": False, "error": f"An unexpected error occurred: {str(e)}"}


# --- 4. Main Server Execution Block ---
# This code runs when you execute the script directly (e.g., `python main.py`).
if __name__ == "__main__":
    import asyncio
    from mcp.server.models import InitializationOptions
    from mcp.server.lowlevel import NotificationOptions
    from mcp.server.stdio import stdio_server
    from mcp.types import ServerCapabilities, Tool, TextContent

    # Create an instance of the MCP server
    server = Server("atlassian-mcp-server")

    # Define the tool handler using the decorator pattern
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
                        "ticket_id": {
                            "type": "string",
                            "description": "The ID of the Jira ticket (e.g., 'PROJ-123')"
                        }
                    },
                    "required": ["ticket_id"]
                }
            )
        ]

    @server.call_tool()
    async def handle_call_tool(name: str, arguments: dict):
        """Handle tool calls."""
        if name == "get_jira_ticket":
            ticket_id = arguments.get("ticket_id")
            if not ticket_id:
                return [TextContent(type="text", text="Error: ticket_id is required")]
            
            result = get_jira_ticket(ticket_id)
            return [TextContent(type="text", text=str(result))]
        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]

    # Main async function to run the server
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

    # Start the server and have it listen for requests
    print("=============================================")
    print("  Atlassian MCP Server - Phase 1 Started   ")
    print("  Mode: Mock (unless .env is configured)   ")
    print("  Tool Registered: get_jira_ticket         ")
    print("=============================================")
    print("\nServer is listening for requests. Connect with an MCP client.")
    
    asyncio.run(main())
