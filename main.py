from fastmcp import FastMCP
import random
import json

# Create teh FastMCP instance
mcp = FastMCP(name="Simple Calculator Server")

# Tool: Add two numbers
@mcp.tool
def add(a: float, b: float) -> float:
    """Add two numbers."""
    return a + b


# tool: Generate a random number
@mcp.tool
def random_number(min: float = 1, max: float = 100) -> float:
    """Generate a random number within a specified range."""
    return random.randint(min, max)


# Resource: Server information
@mcp.resource("info://server")
def server_info() -> str:
    """Get information about this server."""
    info = {
        "name": "Simple Calculator Server",
        "version": "1.0.0",
        "description": "A basic MCP server with math tools",
        "tools": ["add", "random_number"],
        "authors": "Shashank",
    }
    return json.dumps(info, indent=2)

if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=8080)