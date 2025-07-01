from pyrevit import DB
import traceback
import logging

logger = logging.getLogger(__name__)


def normalize_string(text):
    """Safely normalize string values"""
    if text is None:
        return "Unnamed"
    return str(text).strip()

def get_element_name_safe(element):
    """
    Safely get element name (typically Type Name for FamilySymbol)
    using parameter approach with fallback to .Name.
    """
    if not element:
        return "Unnamed"
    try:
        # Try common parameter for Type Name
        param = element.get_Parameter(DB.BuiltInParameter.ALL_MODEL_TYPE_NAME)
        if param and param.HasValue:
            name_from_param = param.AsString()
            if name_from_param is not None and str(name_from_param).strip():
                return str(name_from_param).strip()

        # Fallback to direct .Name access
        if hasattr(element, 'Name'):
            name_prop = element.Name
            if name_prop is not None and str(name_prop).strip():
                return str(name_prop).strip()
                
        return "Unnamed" # Default if no name found
    except Exception as e:
        logger.debug("Error getting element name for ID {}: {}. Falling back to 'Unnamed'".format(
            element.Id.IntegerValue if hasattr(element, 'Id') else 'N/A', str(e)
        ))
        return "Unnamed"

def get_family_name_safe(family_symbol):
    """
    Safely get family name from a FamilySymbol.
    It prioritizes Family.Name and falls back to a parameter.
    """
    if not family_symbol:
        return "Unknown Family"

    try:
        family_obj = family_symbol.Family
        if not family_obj:

            return "Unknown Family"

        retrieved_name = None

        if hasattr(family_obj, 'Name'):
            name_prop = family_obj.Name
            if name_prop is not None:
                name_str = str(name_prop) 
                if name_str.strip(): 
                    retrieved_name = name_str.strip()

            return retrieved_name


    except Exception as e:
        symbol_id_str = "N/A"
        # Safely get symbol ID for logging
        if hasattr(family_symbol, 'Id') and family_symbol.Id is not None:
            try: 
                symbol_id_str = str(family_symbol.Id.IntegerValue)
            except: 
                symbol_id_str = "Valid FamilySymbol, ID retrieval failed"
        
        logger.error(
            "Exception in get_family_name_safe for FamilySymbol (ID: {}): {}. Trace: {}".format(
                symbol_id_str, str(e), traceback.format_exc() # Added traceback for better debugging
            )
        )
        return "Unknown Family"
    

def find_family_symbol_safely(doc, target_family_name, target_type_name=None, category=None):
    """
    Safely find a family symbol using parameter-based approach
    (Now uses the improved get_family_name_safe and get_element_name_safe)
    """
    try:
        collector = DB.FilteredElementCollector(doc).OfClass(DB.FamilySymbol)
        
        if category: # Note: category should be DB.BuiltInCategory enum if used
            collector = collector.OfCategory(category)
            
        symbols = collector.ToElements()
        
        for symbol in symbols:
            try:
                family_name = get_family_name_safe(symbol)
                
                type_name = get_element_name_safe(symbol)
                
                if target_type_name:
                    if family_name == target_family_name and type_name == target_type_name:
                        return symbol
                else:
                    if family_name == target_family_name:
                        return symbol
                        
            except Exception as inner_ex: # Changed from param_error to inner_ex for clarity
                logger.warning("Error processing symbol ID {} during find: {}".format(
                    symbol.Id.IntegerValue if hasattr(symbol, 'Id') else 'N/A', 
                    str(inner_ex)
                ))
                continue
        
        return None # No match found
        
    except Exception as e:
        logger.error("Error in find_family_symbol_safely: {}. Trace: {}".format(
            str(e), traceback.format_exc()
        ))
        return None


# ---- Response Sanitization Helpers ----

try:
    basestring  # type: ignore
except NameError:  # Python 3
    basestring = (str, bytes)  # type: ignore

try:
    unicode  # type: ignore
except NameError:  # Python 3
    unicode = str  # type: ignore


def _sanitize_text(text):
    """Return a Unicode string stripped of non-ASCII characters."""
    if text is None:
        return u""
    try:
        if isinstance(text, bytes):
            try:
                text = text.decode("utf-8")
            except Exception:
                text = text.decode("cp1252", "ignore")
        elif not isinstance(text, unicode):
            text = unicode(text)
    except Exception:
        try:
            text = unicode(str(text), "utf-8", "ignore")
        except Exception:
            text = unicode(str(text))

    import re
    cleaned = re.sub(u"[^\x20-\x7E]", u"", text)
    return cleaned.strip()


def sanitize_data(data):
    """Recursively sanitize data structures for JSON serialization."""
    if isinstance(data, dict):
        return {sanitize_data(k): sanitize_data(v) for k, v in data.items()}
    elif isinstance(data, (list, tuple, set)):
        return [sanitize_data(i) for i in data]
    elif isinstance(data, basestring) or isinstance(data, bytes):
        return _sanitize_text(data)
    else:
        return data


def safe_make_response(*args, **kwargs):
    """Wrapper around routes.make_response that sanitizes response data."""
    if "data" in kwargs:
        kwargs["data"] = sanitize_data(kwargs["data"])
    elif args:
        args = (sanitize_data(args[0]),) + args[1:]
    return routes.make_response(*args, **kwargs)
