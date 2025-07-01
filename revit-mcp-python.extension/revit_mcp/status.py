# -*- coding: UTF-8 -*-
"""
Status Module for Revit MCP
Handles API status and health check endpoints
"""

from pyrevit import routes
from utils import safe_make_response
import logging

logger = logging.getLogger(__name__)

def register_status_routes(api):
    """Register all status-related routes with the API"""
    
    @api.route('/status/', methods=["GET"])
    def revit_status():
        """
        Health check endpoint that verifies Revit context availability
        
        Returns:
            dict: Health status with Revit document information
        """
        try:
            from pyrevit import revit
            
            doc = revit.doc
            if doc:
                return safe_make_response(data={
                    "status": "active",
                    "health": "healthy",
                    "revit_available": True,
                    "document_title": doc.Title if doc.Title else "Untitled",
                    "api_name": "revit_mcp"
                })
            else:
                return safe_make_response(data={
                    "status": "unhealthy", 
                    "revit_available": False,
                    "error": "No active Revit document",
                    "api_name": "revit_mcp"
                }, status=503)
                
        except Exception as e:
            logger.error("Health check failed:{}".format(str(e)))
            return safe_make_response(data={
                "status": "unhealthy",
                "revit_available": False, 
                "error": str(e),
                "api_name": "revit_mcp"
            }, status=503)
    
    logger.info("Status routes registered successfully")
