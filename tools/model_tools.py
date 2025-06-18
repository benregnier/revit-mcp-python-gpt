"""Model structure and hierarchy tools"""

from mcp.server.fastmcp import Context


def register_model_tools(mcp, revit_get):
    """Register model structure tools"""
    
    @mcp.tool()
    async def list_levels(ctx: Context = None) -> str:
        """Get a list of all levels in the current Revit model"""
        return await revit_get("/list_levels/", ctx)
