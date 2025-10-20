# Save this file as /pycalcs/utils.py

import inspect
import re
import importlib

def get_documentation(module_name, func_name_str):
    """
    Parses the docstring of a given function from a specific module.
    
    This function is called by JavaScript to get all UI text,
    ensuring a single source of truth.
    """
    try:
        module = importlib.import_module(module_name)
        func = getattr(module, func_name_str)
        docstring = inspect.getdoc(func)

        if not docstring:
            return {'error': 'No docstring found.'}

        parts = re.split(r'---(\w+)---', docstring)
        
        doc_data = {}
        doc_data['description'] = parts[0].strip()
        
        for i in range(1, len(parts), 2):
            key = parts[i].lower()
            content = parts[i+1].strip()
            
            if key == 'parameters' or key == 'returns':
                # *** NEW, CORRECTED PARSING LOGIC ***
                parsed_items = {}
                current_var_name = None
                
                for line in content.split('\n'):
                    line_stripped = line.strip()
                    
                    # Check if the line is a new variable (not indented and has a colon)
                    if ':' in line and (line_stripped == line):
                        var_name = line.split(':', 1)[0].strip()
                        parsed_items[var_name] = ""  # Initialize empty description
                        current_var_name = var_name
                    
                    # Check if the line is a description (indented)
                    elif current_var_name and (line_stripped != line):
                        parsed_items[current_var_name] += line_stripped + " " # Append the description
                
                # Clean up any trailing whitespace from descriptions
                for var_name, description in parsed_items.items():
                    parsed_items[var_name] = description.strip()
                
                doc_data[key] = parsed_items
                # *** END OF NEW LOGIC ***
            else:
                doc_data[key] = content

        return doc_data

    except ModuleNotFoundError:
        return {'error': f'Module "{module_name}" not found. Did you import it?'}
    except AttributeError:
        return {'error': f'Function "{func_name_str}" not found in {module_name}.'}
    except Exception as e:
        return {'error': str(e)}