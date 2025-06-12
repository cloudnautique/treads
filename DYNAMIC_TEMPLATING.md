# Dynamic Templating in Treads

Treads now supports dynamic templating based on a `response_type` field in agent responses. This allows agents to control how their responses are rendered in the UI by specifying different templates.

## How It Works

1. **Agent Response**: Your agent returns a structured response (JSON) that includes a `response_type` field
2. **Template Lookup**: The system looks for a template at `ui://{agent}/{response_type}`
3. **Fallback**: If no agent-specific template is found, it falls back to `ui://app/{response_type}`
4. **Default**: If no template is found, it uses the built-in default template for that response type

## Example Usage

### In Your Agent Tool

```python
@mcp.tool()
async def get_user_data(ctx: Context) -> str:
    """Returns user data in a table format."""
    data = {
        "response_type": "table_response",
        "headers": ["Name", "Email", "Status"],
        "rows": [
            ["Alice Johnson", "alice@example.com", "Active"],
            ["Bob Smith", "bob@example.com", "Inactive"],
        ]
    }
    return json.dumps(data)
```

### In Your Agent Tool (Code Response)

```python
@mcp.tool()
async def generate_code(language: str, ctx: Context) -> str:
    """Generates code in the specified language."""
    data = {
        "response_type": "code_response",
        "language": language,
        "code": "def hello_world():\n    print('Hello, World!')"
    }
    return json.dumps(data)
```

## Built-in Response Types

### `chat_response` (Default)
- Simple text or structured data display
- Used when no `response_type` is specified

### `table_response` 
- Displays data in a table format
- Expected fields: `headers` (array), `rows` (array of arrays)

### `code_response`
- Displays code with syntax highlighting
- Expected fields: `code` (string), `language` (optional string)

### `list_response`
- Displays data as a bulleted list
- Expected fields: `items` (array of objects with `name`/`title` properties)

### `error_response`
- Used automatically for error conditions
- Expected fields: `error` (string)

### `json_response`
- Displays raw JSON with formatting
- Any structured data will be pretty-printed

### `image_response`
- Displays images
- Expected fields: `url`/`src` (string), `alt` (optional string)

## Creating Custom Templates

You can create custom templates for your agents by adding resources to your agent's `resources.py`:

```python
@mcp.resource("ui://{name}/custom_response", mime_type="application/json",
              description="Custom response template for {name} agent")
def {name}_custom_response():
    return {
        "content": {
            "text": '''<div class="chat-bubble chat-bubble-bot bg-yellow-50 border-l-4 border-yellow-400 p-3 rounded-r-lg">
  <div class="flex items-center gap-2 mb-1">
    <span class="text-yellow-600 font-semibold text-xs uppercase">{name} Agent - Custom</span>
    <span class="text-xs text-gray-500">{{ timestamp }}</span>
  </div>
  <div class="text-gray-800">
    <h3 class="font-bold">{{ response.title }}</h3>
    <p>{{ response.description }}</p>
  </div>
</div>'''
        }
    }
```

Then use it in your tool:

```python
@mcp.tool()
async def custom_tool(ctx: Context) -> str:
    """Returns custom formatted data."""
    data = {
        "response_type": "custom_response",
        "title": "Custom Response",
        "description": "This is a custom formatted response!"
    }
    return json.dumps(data)
```

## Template Variables

All templates have access to these variables:

- `response`: The response data (with `response_type` removed)
- `response_formatted`: Pretty-printed JSON version of the response
- `agent`: The agent name
- `prompt`: The original user prompt
- `timestamp`: ISO timestamp of the response
- `response_type`: The response type used

## Template Syntax

Templates use Jinja2 syntax and support:

- Variable substitution: `{{ variable }}`
- Conditionals: `{% if condition %}...{% endif %}`
- Loops: `{% for item in items %}...{% endfor %}`
- Filters: `{{ variable | filter }}`

## Fallback Chain

1. `ui://{agent}/{response_type}` - Agent-specific template
2. `ui://app/{response_type}` - App-level template (if agent ≠ "app")
3. Built-in default template for the response type
4. Generic `<div class="chat-bubble chat-bubble-bot">{{ response }}</div>`

This allows you to:
- Override specific response types per agent
- Share common templates across agents
- Have sensible defaults for all response types
