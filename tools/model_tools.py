"""Model structure and hierarchy tools"""

from mcp.server.fastmcp import Context


def register_model_tools(mcp, revit_get):
    """Register model structure tools"""
    
    @mcp.tool()
    async def list_levels(ctx: Context = None) -> str:
        """Get a list of all levels in the current Revit model"""
        return await revit_get("/list_levels/", ctx)

    @mcp.tool()
    async def list_sheets(ctx: Context = None) -> str:
        """Get a list of all sheets in the current Revit model"""
        return await revit_get("/list_sheets/", ctx)

    @mcp.tool()
    async def get_sheet_info(sheet_number: str, ctx: Context = None) -> str:
        """Get detailed information about a sheet by number"""
        endpoint = f"/sheet_info/{sheet_number}"
        return await revit_get(endpoint, ctx)
