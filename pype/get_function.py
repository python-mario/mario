import sys
import importlib


def get_function(fullname):
    # TODO use identifier regex to avoid problems with HOFs like map(json.dumps)
    name_parts = fullname.split('.')
    try_names = []
    for idx in range(len(name_parts)):
        try_names.insert(0, '.'.join(name_parts[:idx + 1]))

    for name in try_names:
        if hasattr(sys.modules['builtins'], name):
            obj = getattr(sys.modules['builtins'], name)
            break
        try:
            obj = importlib.import_module(name)
            break
        except ImportError:
            pass
    else:
        raise RuntimeError('could not find %s' % fullname)

    remainder = fullname[len(name) + 1:]
    if remainder:
        for remainder_part in remainder.split('.'):
            obj = getattr(obj, remainder_part)

    return obj


print(get_function('str.upper'))
print(get_function('os.path.join'))
print(get_function('map'))
print(get_function('collections.Counter'))
print(get_function('urllib.parse.urlparse'))
