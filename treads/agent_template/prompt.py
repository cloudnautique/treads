from fastmcp import FastMCP

def register_prompts(mcp: FastMCP):
    @mcp.prompt()
    def {name}_prompt(text: str) -> str:
        '''Describe what this prompt does.'''
        return f"Prompt for {name}: {text} (stub)"
