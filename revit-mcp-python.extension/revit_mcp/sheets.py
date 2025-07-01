# -*- coding: UTF-8 -*-
"""
Sheets Module for Revit MCP
Provides sheet listing functionality
"""

from pyrevit import routes, revit, DB
import logging

from utils import get_element_name_safe

logger = logging.getLogger(__name__)


def register_sheet_routes(api):
    """Register sheet-related routes with the API"""

    @api.route('/list_sheets/', methods=["GET"])
    def list_sheets(doc):
        """Get a list of all sheets in the current Revit model"""
        try:
            if not doc:
                return routes.make_response(
                    data={"error": "No active Revit document"},
                    status=503
                )

            logger.info("Listing all sheets")

            sheets = (
                DB.FilteredElementCollector(doc)
                .OfCategory(DB.BuiltInCategory.OST_Sheets)
                .WhereElementIsNotElementType()
                .ToElements()
            )

            sheets_info = []
            for sheet in sheets:
                try:
                    sheet_number = sheet.SheetNumber
                    sheet_name = get_element_name_safe(sheet)
                    sheets_info.append({
                        "number": sheet_number,
                        "name": sheet_name,
                        "id": sheet.Id.IntegerValue
                    })
                except Exception as e:
                    logger.warning("Could not process sheet: {}".format(str(e)))
                    continue

            sheets_info.sort(key=lambda x: (x["number"], x["name"]))

            return routes.make_response(data={
                "sheets": sheets_info,
                "total_sheets": len(sheets_info),
                "status": "success"
            })

        except Exception as e:
            logger.error("Failed to list sheets: {}".format(str(e)))
            return routes.make_response(
                data={"error": "Failed to list sheets: {}".format(str(e))},
                status=500
            )

    logger.info("Sheets routes registered successfully")

    @api.route('/sheet_info/<sheet_number>', methods=["GET"])
    def sheet_info(doc, sheet_number):
        """Get detailed information about a single sheet by sheet number"""
        try:
            if not doc:
                return routes.make_response(
                    data={"error": "No active Revit document"},
                    status=503,
                )

            logger.info("Getting info for sheet %s", sheet_number)

            sheet = None
            sheets = (
                DB.FilteredElementCollector(doc)
                .OfCategory(DB.BuiltInCategory.OST_Sheets)
                .WhereElementIsNotElementType()
                .ToElements()
            )
            for sh in sheets:
                try:
                    if sh.SheetNumber == sheet_number:
                        sheet = sh
                        break
                except Exception:
                    continue

            if not sheet:
                return routes.make_response(
                    data={"error": "Sheet {} not found".format(sheet_number)},
                    status=404,
                )

            # Get placed views on the sheet
            placed_views = []
            try:
                view_ids = sheet.GetAllPlacedViews()
                for vid in view_ids:
                    view = doc.GetElement(vid)
                    if view:
                        placed_views.append(
                            {
                                "id": view.Id.IntegerValue,
                                "name": get_element_name_safe(view),
                                "type": str(view.ViewType),
                            }
                        )
            except Exception as e:
                logger.warning("Failed to collect views: %s", str(e))

            # Text notes and other elements
            text_notes = []
            other_elements = []
            try:
                collector = DB.FilteredElementCollector(doc, sheet.Id)
                for el in collector.WhereElementIsNotElementType().ToElements():
                    if isinstance(el, DB.TextNote):
                        text_notes.append(el.Text)
                    elif not isinstance(el, DB.Viewport):
                        cat = el.Category.Name if el.Category else "Unknown"
                        other_elements.append(
                            {
                                "id": el.Id.IntegerValue,
                                "name": get_element_name_safe(el),
                                "category": cat,
                            }
                        )
            except Exception as e:
                logger.warning("Failed to collect sheet elements: %s", str(e))

            return routes.make_response(
                data={
                    "sheet_number": sheet.SheetNumber,
                    "sheet_name": get_element_name_safe(sheet),
                    "views": placed_views,
                    "text_notes": text_notes,
                    "elements": other_elements,
                    "status": "success",
                }
            )

        except Exception as e:
            logger.error("Failed to get sheet info: %s", str(e))
            return routes.make_response(
                data={"error": "Failed to get sheet info: {}".format(str(e))},
                status=500,
            )
