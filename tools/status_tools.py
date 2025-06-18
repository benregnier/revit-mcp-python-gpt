"""Status and model information tools"""

from mcp.server.fastmcp import Context


def register_status_tools(mcp, revit_get):
    """Register status-related tools"""
    
    @mcp.tool()
    async def get_revit_status(ctx: Context) -> str:
        """Check if the Revit MCP API is active and responding"""
        return await revit_get("/status/", ctx, timeout=10.0)

    @mcp.tool()
    async def get_revit_model_info(ctx: Context) -> str:
        """Get comprehensive information about the current Revit model"""
        return await revit_get("/model_info/", ctx)
