from fastmcp import FastMCP

mcp = FastMCP(name="{name}")

@mcp.tool()
def {name}(text: str) -> str:
    '''Describe what this tool does.'''
    return f"{name} tool called with: {text} (stub)"

if __name__ == "__main__":
    mcp.run()
