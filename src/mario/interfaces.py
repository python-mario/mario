from typing import Any
from typing import Dict

import attr

from . import plug


@attr.dataclass(init=False)
class Context:
    global_options: Dict[str, Any] = attr.ib(factory=dict)

    def __init__(self, global_options=attr.NOTHING):
        if global_options is attr.NOTHING:
            self.global_options = {}
        else:
            self.global_options = global_options


@attr.dataclass
class Traversal:
    """Traversal"""

    # ...
    # "mario --max-concurrent"
    global_invocation_options: Context
    "mario map --special reversed"
    specific_invocation_params: Dict[str, Any]
    "stack, items"
    runtime_parameters: Dict[str, Any] = attr.ib(default=None)
    "the actual traversal function"
    plugin_object: plug.PluginObject = attr.ib(default=None)
