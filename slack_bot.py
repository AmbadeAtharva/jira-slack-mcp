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

    tool_name, arguments = parse_command(message_text)

    if not tool_name:
        await say(text="Sorry, I didn't understand that command. Please use the format: `<tool_name> <arguments...>`")
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
                # Try to parse the string as JSON for pretty formatting
                try:
                    result_data = json.loads(result_text.replace("'", '"')) # Basic string to JSON conversion
                    pretty_response = json.dumps(result_data, indent=2)
                    await say(
                        text=f"""Tool `{tool_name}` finished with result:
```
{pretty_response}
```"""
                    )
                except json.JSONDecodeError:
                    # If it's not JSON, just send the raw text
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