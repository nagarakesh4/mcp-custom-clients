import asyncio
from typing import Optional
from mcp import StdioServerParameters, ClientSession
from mcp.client.stdio import stdio_client
from mcp.client.sse import sse_client
from openai import AzureOpenAI
from contextlib import AsyncExitStack
import json

class MCPClient:

    async def connect_to_stdio_server(self, server_script_path: str):
        """Connect to an MCP stdio server"""
        is_python = server_script_path.endswith('.py')
        is_js = server_script_path.endswith('.js')
        if not (is_python or is_js):
            raise ValueError("Server script must be a .py or .js file")

        command = "python" if is_python else "node"
        server_params = StdioServerParameters(
            command=command,
            args=[server_script_path],
            env=None
        )

        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        self.stdio, self.write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))

        await self.session.initialize()
        print("Initialized stdio client...")

    async def connect_to_sse_server(self, server_url: str):
        """Connect to an MCP server running with SSE transport"""
        # Store the context managers so they stay alive
        self._streams_context = sse_client(url=server_url)
        streams = await self._streams_context.__aenter__()

        self._session_context = ClientSession(*streams)
        self.session: ClientSession = await self._session_context.__aenter__()

        # Initialize
        await self.session.initialize()
        print("Initialized SSE client...")

    async def list_tools(self):
        """List available tools"""
        print("Listing available tools...")
        mcp_tools = await self.session.list_tools()
        if not mcp_tools:
            print("No tools available.")
            return
        else:
            return self.transform_tools(mcp_tools)

    def transform_tools(self, mcp_tools):
        """
        Transform the available tools to the required format.
        """
        return [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.inputSchema,
                },
            }
            for tool in mcp_tools.tools
        ]

    async def process_user_query(self, available_tools: any, user_query: str, tool_session_map: dict):
        """
        Process the user query and return the response.
        """
        endpoint = "PASTE_YOUR_OPENAI_URL"
        model_name = "gpt-35-turbo"

        subscription_key = "PASTE_YOUR_OPENAI_KEY"
        api_version = "2022-12-01-preview"

        # On first user query, initialize messages if empty
        self.messages = [
            {
                "role": "user",
                "content": user_query
            }
        ]

        # Initialize the Azure OpenAI client
        openai_client = AzureOpenAI(
            api_version=api_version,
            azure_endpoint=endpoint,
            api_key=subscription_key,
        )

        # send the user query to the Azure OpenAI model along with the available tools
        response = openai_client.chat.completions.create(
            messages=self.messages,
            model=model_name,
            tools=available_tools,
            tool_choice="auto"
        )

        azure_response = response.choices[0].message

        # append response to messages
        self.messages.append({
            "role": "user",
            "content": user_query
        })
        self.messages.append(azure_response)

        # Process response and handle tool calls
        while True:
            if azure_response.tool_calls:
                # process all tool calls suggested by LLM , usually limit this to one
                for tool_call in azure_response.tool_calls:
                    result = await tool_session_map[tool_call.function.name].call_tool(
                        tool_call.function.name,
                        json.loads(tool_call.function.arguments)
                    )
                    self.messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": result.content[0].text
                    })
                  
                # call openai with tool results
                azure_response = openai_client.chat.completions.create(
                    messages=self.messages,
                    model=deployment,
                    tools=available_tools,
                    tool_choice="auto"
                ).choices[0].message
      return azure_response.content
    
    async def close(self):
        """Close the MCP client"""
        await self.exit_stack.aclose()

async def main():
    client = MCPClient()
    try:
        available_tools = []
        tool_session_map = {}

        # connect to STDIO server
        server_script_path = "PATH_TO_YOUR_NODE_SCRIPT"
        await client.connect_to_stdio_server(server_script_path)
        stdio_tools = await client.list_tools()
        stdio_session = client.session
        # process recieved tools and store them in the session map

        # connect to SSE server
        await client.connect_to_sse_server("http://localhost:8000/sse")
        sse_tools = await client.list_tools()
        sse_session = client.session
        # process received tools and store them in the session map
        print("Available tools:", available_tools)
        await client.process_user_query(available_tools, user_query, tool_session_map)
    finally:
        print("Closing client...")
        await client.close()

if __name__ == "__main__":
    asyncio.run(main())
