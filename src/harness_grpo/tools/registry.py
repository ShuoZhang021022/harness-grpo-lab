"""Stable callable interfaces and JSON-serializable capability descriptions."""

import inspect
import json
from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class Tool:
    name: str
    domain: str
    function: Callable
    example: dict
    expected: object

    def describe(self):
        signature = inspect.signature(self.function)
        return {
            "name": self.name,
            "domain": self.domain,
            "description": inspect.getdoc(self.function),
            "parameters": [
                {"name": p.name, "required": p.default is inspect.Parameter.empty,
                 **({} if p.default is inspect.Parameter.empty else {"default": p.default})}
                for p in signature.parameters.values()
            ],
            "example_input": self.example,
            "example_output": self.expected,
            "invokes_llm": False,
        }


REGISTRY: dict[str, Tool] = {}


def register(domain, example, expected):
    def decorate(function):
        if function.__name__ in REGISTRY:
            raise ValueError("Duplicate tool name")
        REGISTRY[function.__name__] = Tool(function.__name__, domain, function, example, expected)
        return function
    return decorate


def catalog():
    return [REGISTRY[name].describe() for name in sorted(REGISTRY)]


def call_tool(name: str, arguments: dict):
    """Call one registered tool with JSON arguments. Does not execute arbitrary code."""
    function = REGISTRY[name].function
    inspect.signature(function).bind(**arguments)
    result = function(**arguments)
    json.dumps(result, allow_nan=False)
    return result
