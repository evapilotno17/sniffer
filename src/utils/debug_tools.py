import inspect

def srcd(obj):
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
            docstring = inspect.getdoc(member)
            
            try:
                sig = inspect.signature(member)
                args_info = []
                
                for param_name, param in sig.parameters.items():
                    arg_str = param_name
                    
                    if param.annotation != inspect.Parameter.empty:
                        arg_str += f": {param.annotation}"
                    
                    if param.default != inspect.Parameter.empty:
                        arg_str += f" = {param.default}"
                    
                    args_info.append(arg_str)
                
                if args_info:
                    args_section = f"\n\nArguments:\n" + "\n".join(f"  {arg}" for arg in args_info)
                else:
                    args_section = "\n\nArguments: None"
                
                base_docstring = docstring if docstring else "No docstring available"
                res[name] = base_docstring + args_section
                
            except (ValueError, TypeError):
                res[name] = docstring if docstring else "No docstring available"
    
    for key, value in res.items():
        print(f"FUNCTION_NAME: {key}")
        for line in value.split('\n'):
            print(f'    {line}')
        print('-' * 80)