import importlib
libs = ['openpyxl', 'docx', 'xlsxwriter', 'reportlab', 'pandas', 'PIL']
for lib in libs:
    try:
        m = importlib.import_module(lib)
        print(f'{lib}: OK')
    except ImportError as e:
        print(f'{lib}: MISSING')
