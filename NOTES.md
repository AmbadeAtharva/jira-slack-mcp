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

_Add more questions and answers here as you learn and build!_ 