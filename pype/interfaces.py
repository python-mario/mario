import types

from typing import Dict
from typing import Any

import attr

from . import plug


@attr.dataclass
class Traversal:
    """Traversal"""

    # ...
    "pype --no-autocall"
    global_invocation_options: Dict[str, Any]
    "pype map --special reversed"
    specific_invocation_params: Dict[str, Any]
    "stack, items"
    runtime_parameters: Dict[str, Any] = attr.ib(default=None)
    "the actual traversal function"
    plugin_object: plug.PluginObject = attr.ib(default=None)
