# -*- coding: UTF-8 -*-
"""
Sheets Module for Revit MCP
Provides sheet listing functionality
"""

from pyrevit import routes, revit, DB
import logging
import json
import tempfile
import os
import base64
from System.Collections.Generic import List

from utils import get_element_name_safe, safe_make_response

logger = logging.getLogger(__name__)


def register_sheet_routes(api):
    """Register sheet-related routes with the API"""

    @api.route('/list_sheets/', methods=["GET"])
    def list_sheets(doc):
        """Get a list of all sheets in the current Revit model"""
        try:
            if not doc:
                return safe_make_response(
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

            return safe_make_response(data={
                "sheets": sheets_info,
                "total_sheets": len(sheets_info),
                "status": "success"
            })

        except Exception as e:
            logger.error("Failed to list sheets: {}".format(str(e)))
            return safe_make_response(
                data={"error": "Failed to list sheets: {}".format(str(e))},
                status=500
            )

    logger.info("Sheets routes registered successfully")

    @api.route('/sheet_info/<sheet_number>', methods=["GET"])
    def sheet_info(doc, sheet_number):
        """Get detailed information about a single sheet by sheet number"""
        try:
            if not doc:
                return safe_make_response(
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
                return safe_make_response(
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

            return safe_make_response(
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
            return safe_make_response(
                data={"error": "Failed to get sheet info: {}".format(str(e))},
                status=500,
            )

    @api.route('/export_sheets_pdf/', methods=["POST"])
    def export_sheets_pdf(doc, request):
        """Export specified sheets to a combined PDF and return the data."""

        try:
            if not doc:
                return routes.make_response(
                    data={"error": "No active Revit document"},
                    status=503,
                )

            if not request or not request.data:
                return routes.make_response(
                    data={"error": "No data provided"},
                    status=400,
                )

            data = request.data
            if isinstance(data, str):
                try:
                    data = json.loads(data)
                except Exception as json_err:
                    return routes.make_response(
                        data={"error": "Invalid JSON format: {}".format(str(json_err))},
                        status=400,
                    )

            if not isinstance(data, dict):
                return routes.make_response(
                    data={"error": "Invalid data format"},
                    status=400,
                )

            sheet_entries = data.get("sheets") or []
            if not isinstance(sheet_entries, list) or not sheet_entries:
                return routes.make_response(
                    data={"error": "No sheets specified"},
                    status=400,
                )

            # Collect sheets
            all_sheets = (
                DB.FilteredElementCollector(doc)
                .OfCategory(DB.BuiltInCategory.OST_Sheets)
                .WhereElementIsNotElementType()
                .ToElements()
            )

            sheets_by_number = {s.SheetNumber: s for s in all_sheets}
            sheets_by_id = {s.Id.IntegerValue: s for s in all_sheets}

            target_sheets = []
            for entry in sheet_entries:
                sheet = None
                if isinstance(entry, int) or (isinstance(entry, str) and str(entry).isdigit()):
                    try:
                        sheet_id = int(entry)
                        sheet = sheets_by_id.get(sheet_id)
                    except Exception:
                        sheet = None
                else:
                    sheet = sheets_by_number.get(str(entry))

                if sheet:
                    target_sheets.append(sheet)

            if not target_sheets:
                return routes.make_response(
                    data={"error": "No matching sheets found"},
                    status=404,
                )

            logger.info("Exporting %s sheets to PDF", len(target_sheets))

            pm = doc.PrintManager
            pm.PrintRange = DB.PrintRange.Select
            pm.PrintToFile = True
            pm.CombinedFile = True

            vss = pm.ViewSheetSetting
            view_ids = List[DB.ElementId]()
            for sheet in target_sheets:
                view_ids.Add(sheet.Id)
            vss.CurrentViewSheetSet.Views = view_ids

            output_folder = tempfile.gettempdir()
            output_path = os.path.join(output_folder, "MCP_Sheets.pdf")
            pm.PrintToFileName = output_path

            pm.Apply()
            pm.SubmitPrint()

            if not os.path.exists(output_path):
                return routes.make_response(
                    data={"error": "PDF was not created"},
                    status=500,
                )

            with open(output_path, "rb") as f:
                pdf_data = f.read()

            encoded_data = base64.b64encode(pdf_data).decode("utf-8")

            try:
                os.remove(output_path)
            except Exception:
                pass

            return routes.make_response(
                data={
                    "pdf_data": encoded_data,
                    "sheets_exported": len(target_sheets),
                    "status": "success",
                }
            )

        except Exception as e:
            logger.error("Failed to export sheets to PDF: %s", str(e))
            return routes.make_response(
                data={"error": "Failed to export sheets: {}".format(str(e))},
                status=500,
            )
