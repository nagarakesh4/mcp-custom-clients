from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv
import math
import os

class MathematicalServer:
    """
    A class that encapsulates a Mathematical MCP server with various
    calculation functions and server operation methods.
    """
    
    def __init__(self, server_name="MathematicalTools", server_host="127.0.0.1", server_port=9123):
        """
        Initialize the MCP server with configurable settings.
        
        Args:
            server_name: The name of the MCP server
            server_host: The host address for SSE transport
            server_port: The port number for SSE transport
        """
        # Load environment variables
        load_dotenv("../.env")
        
        # Create an MCP server instance
        self.mcp = FastMCP(
            name=server_name,
            host=server_host,
            port=server_port,
        )
        
        # Register all tool functions
        self._register_tools()
    
    def _register_tools(self):
        """Register all mathematical tool functions with the MCP server."""
        self.mcp.tool()(self.calculate_geometric_mean)
        
    def calculate_geometric_mean(self, values: list[float]) -> float:
        """
        Calculate the geometric mean of a list of values.
        
        Args:
            values: A list of positive numbers
            
        Returns:
            The geometric mean of the input values
        """
        if not values:
            raise ValueError("Input list cannot be empty")
        
        if any(v <= 0 for v in values):
            raise ValueError("All values must be positive for geometric mean calculation")
            
        product = 1.0
        for value in values:
            product *= value
            
        return math.pow(product, 1/len(values))
    
    def run(self, connection_type="stdio"):
        """
        Start the MCP server with the specified connection type.
        
        Args:
            connection_type: The transport mechanism ("stdio" or "sse")
        """
        if connection_type == "stdio":
            print(f"Launching {self.mcp.name} server with stdio transport")
            self.mcp.run(transport="stdio")
        elif connection_type == "sse":
            print(f"Launching {self.mcp.name} server with SSE transport on port {self.mcp.port}")
            self.mcp.run(transport="sse")
        else:
            raise ValueError(f"Unsupported connection type: {connection_type}")


# Run the server when the script is executed directly
if __name__ == "__main__":
    # Get connection type from environment variable or use default
    connection_type = os.getenv("MCP_CONNECTION_TYPE", "stdio")
    
    # Create and run the server
    math_server = MathematicalServer()
    math_server.run(connection_type)
