# slack_bot.py
# This is the client application that connects to Slack and our MCP server.

import os
import asyncio
import subprocess
import json
from dotenv import load_dotenv
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler
from slack_bolt.async_app import AsyncApp
from mcp.client.stdio import stdio_client, StdioServerParameters
import sys
from mcp.client.session import ClientSession
from mcp.types import TextContent
import requests
import re
import ast

# --- 1. Load Configuration ---
load_dotenv()

# It's critical to get these from your Slack App configuration page.
# Add these to your .env file.
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN") # Starts with "xoxb-"
SLACK_APP_TOKEN = os.getenv("SLACK_APP_TOKEN") # Starts with "xapp-"

# --- 2. Initialize the Slack App ---
# We use AsyncApp for compatibility with our async MCP client.
app = AsyncApp(token=SLACK_BOT_TOKEN)

# --- 3. The "Fake AI" Command Parser ---
# In a real app, an LLM would generate the tool name and arguments.
# For our project, we'll parse the command from the Slack message directly.
# Format: @bot <tool_name> <arg1> <arg2> ...
def parse_command(text: str):
    """Parses a command string into a tool name and arguments."""
    parts = text.strip().split()
    if len(parts) < 2:
        return None, None # Not a valid command
    
    tool_name = parts[1]
    raw_args = parts[2:]
    
    # This is a simple parser. A real implementation would be more robust.
    # For now, we assume the arguments are in the correct order.
    arguments = {}
    if tool_name == "get_jira_ticket":
        arguments['ticket_id'] = raw_args[0]
    elif tool_name == "create_jira_ticket":
        arguments['project_key'] = raw_args[0]
        arguments['summary'] = raw_args[1]
        arguments['description'] = raw_args[2]
        arguments['issue_type'] = raw_args[3]
    elif tool_name == "search_jira_tickets":
        arguments['jql_query'] = " ".join(raw_args)
    elif tool_name == "search_confluence_pages":
        arguments['query'] = " ".join(raw_args)
        
    return tool_name, arguments

def get_tool_call_from_llm(user_message):
    tool_list = (
        "get_jira_ticket(ticket_id), "
        "create_jira_ticket(project_key, summary, description, issue_type), "
        "update_jira_ticket(ticket_id, summary, description, status, assignee), "
        "delete_jira_ticket(ticket_id), "
        "search_jira_tickets(jql_query), "
        "create_confluence_page(space_key, title, content, parent_page_id), "
        "get_confluence_page(page_id), "
        "update_confluence_page(page_id, title, content), "
        "delete_confluence_page(page_id), "
        "search_confluence_pages(query)"
    )
    
    # Check if user is asking about available tools
    if any(keyword in user_message.lower() for keyword in ["list", "tools", "available", "what can you do", "help"]):
        return {
            "tool": "list_available_tools",
            "arguments": {}
        }
    
    prompt = (
        f"You are an assistant that helps users interact with Jira and Confluence. "
        f"Available tools:\n{tool_list}\n\n"
        f"User message: '{user_message}'\n\n"
        f"Based on the user's request, determine which tool to call and extract the arguments. "
        f"Respond ONLY with a valid JSON object in this exact format:\n"
        f"{{\"tool\": \"tool_name\", \"arguments\": {{...}}}}\n\n"
        f"Examples:\n"
        f"- For creating a ticket: {{\"tool\": \"create_jira_ticket\", \"arguments\": {{\"project_key\": \"PROJ\", \"summary\": \"Bug title\", \"description\": \"Bug description\", \"issue_type\": \"Bug\"}}}}\n"
        f"- For updating a ticket: {{\"tool\": \"update_jira_ticket\", \"arguments\": {{\"ticket_id\": \"PROJ-123\", \"status\": \"In Progress\", \"assignee\": \"john.doe\"}}}}\n"
        f"- For deleting a ticket: {{\"tool\": \"delete_jira_ticket\", \"arguments\": {{\"ticket_id\": \"PROJ-123\"}}}}\n"
        f"- For searching tickets: {{\"tool\": \"search_jira_tickets\", \"arguments\": {{\"jql_query\": \"created >= -2d\"}}}}\n"
        f"- For getting a ticket: {{\"tool\": \"get_jira_ticket\", \"arguments\": {{\"ticket_id\": \"PROJ-123\"}}}}\n"
        f"- For creating a Confluence page: {{\"tool\": \"create_confluence_page\", \"arguments\": {{\"space_key\": \"TEAM\", \"title\": \"Page Title\", \"content\": \"Page content here\"}}}}\n"
        f"- For updating a Confluence page: {{\"tool\": \"update_confluence_page\", \"arguments\": {{\"page_id\": \"12345\", \"title\": \"New Title\", \"content\": \"Updated content\"}}}}\n"
        f"- For searching Confluence: {{\"tool\": \"search_confluence_pages\", \"arguments\": {{\"query\": \"API documentation\"}}}}\n\n"
        f"Respond with ONLY the JSON object, no other text:"
    )
    response = requests.post(
        "http://localhost:11434/api/generate",
        json={"model": "llama3.2", "prompt": prompt, "stream": False}
    )
    match = re.search(r'\{.*\}', response.json()["response"], re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            print(f"Failed to parse JSON from LLM response: {response.json()['response']}")
            return None
    return None

def format_tool_response(tool_name: str, result_data: dict) -> str:
    """Format tool responses in a user-friendly way."""
    
    if not result_data.get("success", False):
        error_msg = result_data.get("error", "Unknown error occurred")
        return f"❌ **Error in {tool_name}:** {error_msg}"
    
    if tool_name == "get_jira_ticket":
        ticket_id = result_data.get("ticket_id", "Unknown")
        summary = result_data.get("summary", "No summary")
        status = result_data.get("status", "Unknown")
        assignee = result_data.get("assignee", "Unassigned")
        url = result_data.get("url", "")
        
        return f"""✅ **Jira Ticket: {ticket_id}**
        
📋 **Summary:** {summary}
📊 **Status:** {status}
👤 **Assignee:** {assignee}
🔗 **URL:** {url}"""
    
    elif tool_name == "create_jira_ticket":
        ticket_id = result_data.get("ticket_id", "Unknown")
        summary = result_data.get("summary", "No summary")
        url = result_data.get("url", "")
        
        return f"""✅ **Ticket Created Successfully!**
        
🎫 **Ticket ID:** {ticket_id}
📋 **Summary:** {summary}
🔗 **URL:** {url}"""
    
    elif tool_name == "search_jira_tickets":
        tickets = result_data.get("tickets", [])
        if not tickets:
            return "🔍 **Search Results:** No tickets found matching your criteria."
        
        response = f"🔍 **Found {len(tickets)} ticket(s):**\n\n"
        for i, ticket in enumerate(tickets, 1):
            ticket_id = ticket.get("ticket_id", "Unknown")
            summary = ticket.get("summary", "No summary")
            status = ticket.get("status", "Unknown")
            url = ticket.get("url", "")
            
            response += f"{i}. **{ticket_id}** - {summary}\n"
            response += f"   📊 Status: {status}\n"
            response += f"   🔗 {url}\n\n"
        
        return response
    
    elif tool_name == "search_confluence_pages":
        pages = result_data.get("pages", [])
        if not pages:
            return "🔍 **Search Results:** No Confluence pages found matching your criteria."
        
        response = f"🔍 **Found {len(pages)} Confluence page(s):**\n\n"
        for i, page in enumerate(pages, 1):
            title = page.get("title", "Untitled")
            snippet = page.get("snippet", "No description available")
            url = page.get("url", "")
            
            # Truncate snippet if too long
            if len(snippet) > 150:
                snippet = snippet[:147] + "..."
            
            response += f"{i}. **{title}**\n"
            response += f"   📝 {snippet}\n"
            response += f"   🔗 {url}\n\n"
        
        return response
    
    elif tool_name == "update_jira_ticket":
        ticket_id = result_data.get("ticket_id", "Unknown")
        message = result_data.get("message", "Update completed")
        url = result_data.get("url", "")
        
        return f"""✅ **Ticket Updated Successfully!**
        
🎫 **Ticket ID:** {ticket_id}
📝 **Message:** {message}
🔗 **URL:** {url}"""
    
    elif tool_name == "delete_jira_ticket":
        ticket_id = result_data.get("ticket_id", "Unknown")
        message = result_data.get("message", "Deletion completed")
        url = result_data.get("url", "")
        
        return f"""🗑️ **Ticket Deleted Successfully!**
        
🎫 **Ticket ID:** {ticket_id}
📝 **Message:** {message}
🔗 **URL:** {url}"""
    
    elif tool_name == "create_confluence_page":
        page_id = result_data.get("page_id", "Unknown")
        title = result_data.get("title", "Untitled")
        url = result_data.get("url", "")
        
        return f"""✅ **Confluence Page Created Successfully!**
        
📄 **Page ID:** {page_id}
📋 **Title:** {title}
🔗 **URL:** {url}"""
    
    elif tool_name == "get_confluence_page":
        page_id = result_data.get("page_id", "Unknown")
        title = result_data.get("title", "Untitled")
        content = result_data.get("content", "No content available")
        url = result_data.get("url", "")
        
        # Truncate content if too long
        if len(content) > 300:
            content = content[:297] + "..."
        
        return f"""📄 **Confluence Page: {page_id}**
        
📋 **Title:** {title}
📝 **Content:** {content}
🔗 **URL:** {url}"""
    
    elif tool_name == "update_confluence_page":
        page_id = result_data.get("page_id", "Unknown")
        message = result_data.get("message", "Update completed")
        url = result_data.get("url", "")
        
        return f"""✅ **Confluence Page Updated Successfully!**
        
📄 **Page ID:** {page_id}
📝 **Message:** {message}
🔗 **URL:** {url}"""
    
    elif tool_name == "delete_confluence_page":
        page_id = result_data.get("page_id", "Unknown")
        message = result_data.get("message", "Deletion completed")
        url = result_data.get("url", "")
        
        return f"""🗑️ **Confluence Page Deleted Successfully!**
        
📄 **Page ID:** {page_id}
📝 **Message:** {message}
🔗 **URL:** {url}"""
    
    else:
        # Fallback for unknown tools
        return f"✅ **{tool_name} completed successfully:**\n```{json.dumps(result_data, indent=2)}```"

# --- 4. Main Slack Event Handler ---
@app.event("app_mention")
async def handle_app_mention(event, say):
    """
    This function is triggered when the bot is @mentioned in a channel.
    """
    # Get the text from the user's message, removing the bot's mention
    message_text = event["text"].replace(f"<@{event['user']}>", "").strip()
    channel_id = event["channel"]
    
    print(f"Received mention: '{message_text}' in channel {channel_id}")

    tool_call = get_tool_call_from_llm(message_text)
    if tool_call and "tool" in tool_call and "arguments" in tool_call:
        tool_name = tool_call["tool"]
        arguments = tool_call["arguments"]
    else:
        await say(text="Sorry, I didn't understand that command. Please use the format: `<tool_name> <arguments...>`")
        return

    # Handle special case for listing available tools
    if tool_name == "list_available_tools":
        tools_info = """
🤖 **Available Tools:**

**Jira Tools:**
• `get_jira_ticket(ticket_id)` - Get details of a specific Jira ticket
• `create_jira_ticket(project_key, summary, description, issue_type)` - Create a new Jira ticket
• `update_jira_ticket(ticket_id, summary, description, status, assignee)` - Update an existing Jira ticket
• `delete_jira_ticket(ticket_id)` - Delete a Jira ticket
• `search_jira_tickets(jql_query)` - Search Jira tickets using JQL

**Confluence Tools:**
• `create_confluence_page(space_key, title, content, parent_page_id)` - Create a new Confluence page
• `get_confluence_page(page_id)` - Get details of a specific Confluence page
• `update_confluence_page(page_id, title, content)` - Update an existing Confluence page
• `delete_confluence_page(page_id)` - Delete a Confluence page
• `search_confluence_pages(query)` - Search Confluence pages

**Examples:**
• "Get ticket PROJ-123" → `get_jira_ticket`
• "Create a bug ticket for login issues" → `create_jira_ticket`
• "Update ticket PROJ-123 status to In Progress" → `update_jira_ticket`
• "Delete ticket PROJ-123" → `delete_jira_ticket`
• "Search for tickets from last 2 days" → `search_jira_tickets`
• "Create a new Confluence page about API docs" → `create_confluence_page`
• "Update Confluence page 12345 with new content" → `update_confluence_page`
• "Find API documentation" → `search_confluence_pages`
"""
        await say(text=tools_info)
        return

    await say(text=f"Got it! Calling tool `{tool_name}` with arguments: `{arguments}`. Please wait...")

    try:
        # --- MCP Client Logic ---
        # 1 & 2. Launch the MCP server and connect the client in one step using StdioServerParameters
        python_executable = sys.executable
        main_py_path = os.path.abspath("main.py")
        params = StdioServerParameters(command=main_py_path)
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                # 3. Call the tool
                response = await session.call_tool(name=tool_name, arguments=arguments)
                # 4. Format and send the response
                # The response from our server is a TextContent object containing a string
                content_block = response.content[0] if response.content else None
                result_text = None
                if content_block is not None:
                    if isinstance(content_block, TextContent):
                        result_text = content_block.text
                    elif getattr(content_block, 'type', None) == 'image':
                        result_text = '[Image content received]'
                    elif getattr(content_block, 'type', None) == 'audio':
                        result_text = '[Audio content received]'
                    elif getattr(content_block, 'type', None) == 'resource':
                        result_text = '[Embedded resource received]'
                    else:
                        result_text = str(content_block)
                else:
                    result_text = '[No content returned from tool]'
                # Debug print for result_text
                print(f"[DEBUG] result_text before JSON parsing: {result_text}")
                # Try to parse the string as JSON for pretty formatting
                try:
                    result_data = json.loads(result_text)
                    formatted_response = format_tool_response(tool_name, result_data)
                    await say(text=formatted_response)
                except json.JSONDecodeError as e:
                    print(f"[DEBUG] JSONDecodeError: {e}")
                    # Try ast.literal_eval as fallback
                    try:
                        result_data = ast.literal_eval(result_text)
                        formatted_response = format_tool_response(tool_name, result_data)
                        await say(text=formatted_response)
                    except Exception as ast_e:
                        print(f"[DEBUG] ast.literal_eval error: {ast_e}")
                        await say(text=f"Tool `{tool_name}` finished with result:\n{result_text}")

    except Exception as e:
        print(f"An error occurred: {e}")
        await say(text=f"An error occurred while running the tool: {e}")


# --- 5. Main Execution Block ---
async def main():
    print("Starting Slack Bot...")
    # The SocketModeHandler connects to Slack and listens for events.
    handler = AsyncSocketModeHandler(app, SLACK_APP_TOKEN)
    await handler.start_async()

if __name__ == "__main__":
    # Ensure you have the necessary tokens in your .env file
    if not all([SLACK_BOT_TOKEN, SLACK_APP_TOKEN]):
        print("!!! ERROR: SLACK_BOT_TOKEN and SLACK_APP_TOKEN must be set in your .env file.")
    else:
        asyncio.run(main()) 