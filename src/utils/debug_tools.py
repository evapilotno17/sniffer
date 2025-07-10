import inspect

def src(obj):
   print(inspect.getsource(obj))

def methods(obj, ignore=None, include=None):
    if ignore is None:
        ignore = ['__']
    res = {}
    for name, member in inspect.getmembers(obj):
        if not inspect.isroutine(member):
            continue
        good = True
        for z in ignore:
            if z in name:
                good = False
        if include is not None:
            for z in include:
                if z not in name:
                    good = False
        if good:
            # Get the docstring using inspect
            docstring = inspect.getdoc(member)
            
            # Get function signature
            try:
                sig = inspect.signature(member)
                args_info = []
                
                for param_name, param in sig.parameters.items():
                    arg_str = param_name
                    
                    # Add type annotation if available
                    if param.annotation != inspect.Parameter.empty:
                        arg_str += f": {param.annotation}"
                    
                    # Add default value if available
                    if param.default != inspect.Parameter.empty:
                        arg_str += f" = {param.default}"
                    
                    args_info.append(arg_str)
                
                # Format arguments section
                if args_info:
                    args_section = f"\n\nArguments:\n" + "\n".join(f"  {arg}" for arg in args_info)
                else:
                    args_section = "\n\nArguments: None"
                
                # Combine docstring with arguments
                base_docstring = docstring if docstring else "No docstring available"
                res[name] = base_docstring + args_section
                
            except (ValueError, TypeError):
                # Fallback if signature inspection fails
                res[name] = docstring if docstring else "No docstring available"
    
    return res