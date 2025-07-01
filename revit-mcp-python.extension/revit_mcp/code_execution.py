# -*- coding: UTF-8 -*-
"""
Code Execution Module for Revit MCP
Handles direct execution of IronPython code in Revit context.
"""
from pyrevit import routes, revit, DB
from utils import safe_make_response
import json
import logging
import sys
import traceback
from StringIO import StringIO

# Standard logger setup
logger = logging.getLogger(__name__)


def register_code_execution_routes(api):
    """Register code execution routes with the API."""

    @api.route("/execute_code/", methods=["POST"])
    def execute_code(doc, request):
        """
        Execute IronPython code in Revit context.

        Expected payload:
        {
            "code": "python code as string",
            "description": "optional description of what the code does"
        }
        """
        try:
            # Parse the request data
            data = (
                json.loads(request.data)
                if isinstance(request.data, str)
                else request.data
            )
            code_to_execute = data.get("code", "")
            description = data.get("description", "Code execution")

            if not code_to_execute:
                return safe_make_response(
                    data={"error": "No code provided"}, status=400
                )

            logger.info("Executing code: {}".format(description))

            # Create a transaction for any model modifications
            t = DB.Transaction(doc, "MCP Code Execution: {}".format(description))
            t.Start()

            try:
                # Capture stdout to return any print statements
                old_stdout = sys.stdout
                captured_output = StringIO()
                sys.stdout = captured_output

                # Create a namespace with common Revit objects available
                namespace = {
                    "doc": doc,
                    "DB": DB,
                    "revit": revit,
                    "__builtins__": __builtins__,
                    "print": lambda *args: captured_output.write(
                        " ".join(str(arg) for arg in args) + "\n"
                    ),
                }

                # Execute the code
                exec(code_to_execute, namespace)

                # Restore stdout
                sys.stdout = old_stdout

                # Get any printed output
                output = captured_output.getvalue()
                captured_output.close()

                # Commit the transaction
                t.Commit()

                return safe_make_response(
                    data={
                        "status": "success",
                        "description": description,
                        "output": (
                            output
                            if output
                            else "Code executed successfully (no output)"
                        ),
                        "code_executed": code_to_execute,
                    }
                )

            except Exception as exec_error:
                # Restore stdout if something went wrong
                sys.stdout = old_stdout

                # Rollback transaction if it's still active
                if t.HasStarted() and not t.HasEnded():
                    t.RollBack()

                # Get the full traceback
                error_traceback = traceback.format_exc()

                logger.error("Code execution failed: {}".format(str(exec_error)))
                logger.error("Traceback: {}".format(error_traceback))

                return safe_make_response(
                    data={
                        "status": "error",
                        "error": str(exec_error),
                        "traceback": error_traceback,
                        "code_attempted": code_to_execute,
                    },
                    status=500,
                )

        except Exception as e:
            logger.error("Execute code request failed: {}".format(str(e)))
            return safe_make_response(data={"error": str(e)}, status=500)

    logger.info("Code execution routes registered successfully.")
