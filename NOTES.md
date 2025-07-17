# Project Notes & FAQ

---

## Q: How and when is the main MCP server (`main.py`) called from the Slack bot?

**A:**

### Where in the Code?
- In `slack_bot.py`, after the bot receives a mention and parses the command, it prepares to call the corresponding tool (like `get_jira_ticket`) by launching the MCP server (`main.py`).

### How is it Called?
```python
main_py_path = os.path.abspath("main.py")
params = StdioServerParameters(command=main_py_path)

async with stdio_client(params) as (read, write):
    async with ClientSession(read, write) as session:
        await session.initialize()
        response = await session.call_tool(name=tool_name, arguments=arguments)
```
- `stdio_client(params)` launches `main.py` and connects to it via standard input/output.
- `ClientSession` wraps the connection, allowing you to call tools exposed by the MCP server.
- The bot calls the tool (e.g., `get_jira_ticket`) by sending a request to the running `main.py` process.
- The MCP server executes the tool and returns the result.
- The bot receives the result, formats it, and posts it back to Slack.

### When is the MCP Server Called?
- **Every time a user mentions the bot with a valid command in Slack,** the bot:
  1. Parses the command and arguments.
  2. Launches a new instance of `main.py` (the MCP server) as a subprocess.
  3. Connects to it, calls the requested tool, gets the result, and then closes the connection.

**This means:**
- The MCP server (`main.py`) is not running persistently in the background.
- It is started on-demand for each tool call, ensuring a fresh environment and stateless operation for each request.

### Summary Table

| Event in Slack         | What Happens in Code?                                 | What Happens to main.py?         |
|------------------------|------------------------------------------------------|----------------------------------|
| User mentions bot      | Bot parses command                                   |                                  |
| Valid tool command     | Bot sets up StdioServerParameters with main.py path  | main.py launched as subprocess   |
| Tool call made         | Bot connects via stdio_client and ClientSession      | main.py runs, executes tool      |
| Tool returns result    | Bot formats and posts result to Slack                | main.py subprocess exits         |

**If you want to make the MCP server persistent (always running), or optimize for multiple requests, you can change this design. Otherwise, this on-demand approach is simple and robust for learning and prototyping.**

---

## Q: How and where does the Ollama LLM integration take place in the Slack bot?

**A:**

### Where in the Code?
- In `slack_bot.py`, the function `get_tool_call_from_llm(user_message)` sends the user's message to the Ollama LLM (Llama 3.2) running locally.
- The function constructs a prompt listing all available tools and asks the LLM to return a JSON object specifying the tool and arguments to use.
- The Slack event handler uses this function to interpret natural language commands and route them to the correct MCP tool.

**Relevant code snippet:**
```python
import requests
import re
import json

def get_tool_call_from_llm(user_message):
    tool_list = (
        "get_jira_ticket(ticket_id), "
        "search_jira_tickets(jql_query), "
        "create_jira_ticket(project_key, summary, description, issue_type), "
        "search_confluence_pages(query)"
    )
    prompt = (
        f"You are an assistant that helps users interact with Jira and Confluence. "
        f"Available tools:\n{tool_list}\n\n"
        f"User message: '{user_message}'\n\n"
        f"Based on the user's request, determine which tool to call and extract the arguments. "
        f"Respond ONLY with a valid JSON object in this exact format:\n"
        f"{{\"tool\": \"tool_name\", \"arguments\": {{...}}}}\n\n"
        f"Examples:\n"
        f"- For creating a ticket: {{\"tool\": \"create_jira_ticket\", \"arguments\": {{\"project_key\": \"PROJ\", \"summary\": \"Bug title\", \"description\": \"Bug description\", \"issue_type\": \"Bug\"}}}}\n"
        f"- For searching tickets: {{\"tool\": \"search_jira_tickets\", \"arguments\": {{\"jql_query\": \"created >= -2d\"}}}}\n"
        f"- For getting a ticket: {{\"tool\": \"get_jira_ticket\", \"arguments\": {{\"ticket_id\": \"PROJ-123\"}}}}\n"
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
```
- In the Slack event handler, instead of parsing the tool name directly, the bot now calls this function and uses the returned tool and arguments to call the MCP server.

### How to Set Up Ollama for Your Project

1. **Install Ollama**  
   Download and install from: [https://ollama.com/](https://ollama.com/)

2. **Pull and Run a Model (e.g., Llama 3.2)**
   ```sh
   ollama pull llama3.2
   ollama run llama3.2
   ```
   This will start the Ollama server at `http://localhost:11434`.

3. **Test the API**  
   You can use the included Python code or:
   ```sh
   curl http://localhost:11434/api/generate -d '{"model": "llama3.2", "prompt": "Say hello!", "stream": false}'
   ```

4. **Run your Slack bot as usual!**  
   The bot will now use Ollama to interpret user messages and route them to the correct tool.

### What to Expect
- You can now use natural language in Slack, e.g.:
  ```
  @Atlassian MCP Bot give me all the past 2 days tickets
  ```
  and the bot will use LLM reasoning to call the right tool with the right arguments.

### Model Performance Notes
- **Llama 3.2** is lighter and faster than Llama 2, making it ideal for local development
- The updated prompt is more specific and provides clear examples, leading to better JSON parsing
- Error handling has been improved to catch JSON parsing failures

---

## Q: How and why was the `format_tool_response` function implemented?

**A:**

### Why It Was Needed
The original Slack bot was returning raw JSON responses like:
```
{'success': True, 'pages': [{'title': 'How to set up the VPN', 'snippet': 'Step-by-step guide to configure VPN access...', 'url': 'https://mock-confluence.com/pages/viewpage.action?pageId=12345'}]}
```

This was **hard to read** and **not user-friendly** in Slack. Users needed a more readable, formatted output.

### How It Was Implemented

**1. Created a dedicated formatting function:**
```python
def format_tool_response(tool_name: str, result_data: dict) -> str:
    """Format tool responses in a user-friendly way."""
    
    if not result_data.get("success", False):
        error_msg = result_data.get("error", "Unknown error occurred")
        return f"❌ **Error in {tool_name}:** {error_msg}"
    
    # Tool-specific formatting...
```

**2. Added tool-specific formatting:**
- **Jira Ticket Details:** Shows ticket ID, summary, status, assignee, and URL
- **Created Tickets:** Shows success message with ticket ID and URL
- **Search Results:** Lists multiple tickets/pages with numbered formatting
- **Confluence Pages:** Shows page titles, snippets, and URLs

**3. Improved JSON parsing:**
The MCP server returns Python-style dicts (with single quotes) instead of valid JSON. We implemented a two-step parsing approach:

```python
try:
    result_data = json.loads(result_text)  # Try standard JSON first
    formatted_response = format_tool_response(tool_name, result_data)
    await say(text=formatted_response)
except json.JSONDecodeError as e:
    # Fallback to ast.literal_eval for Python-style dicts
    try:
        result_data = ast.literal_eval(result_text)
        formatted_response = format_tool_response(tool_name, result_data)
        await say(text=formatted_response)
    except Exception as ast_e:
        # Final fallback to raw text
        await say(text=f"Tool `{tool_name}` finished with result:\n{result_text}")
```

### Example Output Comparison

**Before (Raw JSON):**
```
{'success': True, 'pages': [{'title': 'How to set up the VPN', 'snippet': 'Step-by-step guide to configure VPN access...', 'url': 'https://mock-confluence.com/pages/viewpage.action?pageId=12345'}]}
```

**After (Formatted):**
```
🔍 Found 1 Confluence page(s):

1. **How to set up the VPN**
   📝 Step-by-step guide to configure VPN access...
   🔗 https://mock-confluence.com/pages/viewpage.action?pageId=12345
```

### Benefits
- **Readability:** Much easier to read and understand
- **User Experience:** Professional-looking responses with emojis and formatting
- **Error Handling:** Clear error messages when things go wrong
- **Consistency:** All tool responses follow the same formatting pattern

---

_Add more questions and answers here as you learn and build!_ 