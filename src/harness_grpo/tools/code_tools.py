"""Source analysis and transformation only. These tools never run submitted Python."""

import ast
import difflib
import io
import json
import sys
import token
import tokenize

from .registry import register


@register("code", {"source": "x = 1\n"}, {"valid": True, "top_level_nodes": ["Assign"]})
def parse_python(source):
    """Parse Python syntax and return top-level AST node types, or syntax error details."""
    try:
        tree = ast.parse(source)
        return {"valid": True, "top_level_nodes": [type(n).__name__ for n in tree.body]}
    except SyntaxError as error:
        return {"valid": False, "line": error.lineno, "offset": error.offset, "message": error.msg}


@register("code", {"source": "x = 1"}, "Module(body=[Assign(targets=[Name(id='x', ctx=Store())], value=Constant(value=1))], type_ignores=[])")
def ast_structure(source):
    """Return the complete Python AST as a structural string without source locations; never execute it."""
    options = {"show_empty": True} if sys.version_info >= (3, 13) else {}
    return ast.dump(ast.parse(source), include_attributes=False, **options)


@register("code", {"source": "def f(x):\n    return x\n"}, [{"name": "f", "kind": "FunctionDef", "line": 1, "end_line": 2}])
def find_definitions(source):
    """List class, function and async-function definitions, including nested definitions and line ranges."""
    return [{"name": n.name, "kind": type(n).__name__, "line": n.lineno, "end_line": n.end_lineno}
            for n in ast.walk(ast.parse(source)) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))]


@register("code", {"source": "print(len(x))"}, [{"callee": "print", "line": 1}, {"callee": "len", "line": 1}])
def find_calls(source):
    """List syntactic call expressions and line numbers; does not prove which calls execute at runtime."""
    return [{"callee": ast.unparse(n.func), "line": n.lineno}
            for n in ast.walk(ast.parse(source)) if isinstance(n, ast.Call)]


@register("code", {"source": "import math\nfrom os import path"}, ["import math", "from os import path"])
def find_imports(source):
    """List import statements syntactically without loading the referenced modules."""
    return [ast.unparse(n) for n in ast.walk(ast.parse(source)) if isinstance(n, (ast.Import, ast.ImportFrom))]


@register("code", {"source": "y = x + x"}, {"x": {"load": 2, "store": 0, "delete": 0}, "y": {"load": 0, "store": 1, "delete": 0}})
def name_usage(source):
    """Count AST Name loads/stores/deletes by spelling; does not resolve lexical scopes or attributes."""
    result = {}
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Name):
            counts = result.setdefault(node.id, {"load": 0, "store": 0, "delete": 0})
            counts[{ast.Load: "load", ast.Store: "store", ast.Del: "delete"}[type(node.ctx)]] += 1
    return result


@register("code", {"source": "x = 12"}, [{"literal": "12", "line": 1}])
def list_literals(source):
    """List Python constant literals as repr strings and line numbers, including bytes and complex values."""
    return [{"literal": repr(n.value), "line": n.lineno}
            for n in ast.walk(ast.parse(source)) if isinstance(n, ast.Constant)]


@register("code", {"source": "a\nb\nc\n", "start_line": 2, "end_line": 3}, "b\nc\n")
def extract_lines(source, start_line, end_line):
    """Extract an inclusive one-based line range, preserving line endings; reject out-of-range requests."""
    lines = source.splitlines(keepends=True)
    if not 1 <= start_line <= end_line <= len(lines):
        raise ValueError("Invalid line range")
    return "".join(lines[start_line - 1:end_line])


@register("code", {"source": "x+x", "old": "x", "new": "y", "expected_count": 2}, "y+y")
def replace_text_exact(source, old, new, expected_count):
    """Replace all literal occurrences only if their number exactly matches expected_count; fail otherwise."""
    if not old or expected_count < 0 or source.count(old) != expected_count:
        raise ValueError("Replacement count mismatch or empty search")
    return source.replace(old, new)


@register("code", {"source": "a\nb\nc\n", "start_line": 2, "end_line": 2, "replacement": "B\n"}, "a\nB\nc\n")
def replace_lines(source, start_line, end_line, replacement):
    """Replace an inclusive one-based line range verbatim; caller supplies replacement newlines."""
    extract_lines(source, start_line, end_line)
    lines = source.splitlines(keepends=True)
    return "".join(lines[:start_line - 1]) + replacement + "".join(lines[end_line:])


@register("code", {"before": "a\n", "after": "b\n"}, "--- before\n+++ after\n@@ -1 +1 @@\n-a\n+b\n")
def unified_diff(before, after):
    """Produce a unified diff of two in-memory texts using fixed before/after filenames."""
    return "".join(difflib.unified_diff(before.splitlines(True), after.splitlines(True), fromfile="before", tofile="after"))


@register("code", {"source": "x = x + 1", "old": "x", "new": "y"}, "y = y + 1")
def rename_name_nodes(source, old, new):
    """Rename matching AST Name nodes only; NOT scope-aware, and does not rename parameters or attributes. Reformats code."""
    import keyword
    if not new.isidentifier() or keyword.iskeyword(new):
        raise ValueError("new must be a non-keyword identifier")
    class Rename(ast.NodeTransformer):
        def visit_Name(self, node):
            if node.id == old:
                node.id = new
            return node
    return ast.unparse(Rename().visit(ast.parse(source)))


@register("code", {"source": "x = 2 + 2", "old": 2, "new": 3, "expected_count": 2}, "x = 3 + 3")
def replace_number_literals(source, old, new, expected_count):
    """Replace numeric AST constants, excluding booleans; validate count. Negative signs are separate AST nodes. Reformats code."""
    if type(old) not in (int, float) or type(new) not in (int, float):
        raise ValueError("Require numeric values, excluding booleans")
    tree = ast.parse(source)
    nodes = [n for n in ast.walk(tree) if isinstance(n, ast.Constant) and type(n.value) in (int, float) and n.value == old]
    if len(nodes) != expected_count:
        raise ValueError("Literal count mismatch")
    for node in nodes:
        node.value = new
    return ast.unparse(tree)


@register("code", {"text": "{\"b\": 1, \"a\": 2}"}, '{"a":2,"b":1}')
def canonical_json(text):
    """Parse JSON and serialize with sorted keys, UTF-8 characters, and compact separators; rejects NaN/Infinity."""
    return json.dumps(json.loads(text), ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


@register("code", {"left": {"x": 1}, "right": {"x": 2}}, [{"path": ["x"], "kind": "changed", "left": 1, "right": 2}])
def compare_json(left, right):
    """Recursively compare JSON values; distinguish types and return changed, added or removed paths."""
    changes = []
    def visit(a, b, path):
        if type(a) != type(b):
            changes.append({"path": path, "kind": "changed", "left": a, "right": b})
        elif isinstance(a, dict):
            for key in sorted(a.keys() | b.keys()):
                if key not in a:
                    changes.append({"path": path + [key], "kind": "added", "right": b[key]})
                elif key not in b:
                    changes.append({"path": path + [key], "kind": "removed", "left": a[key]})
                else:
                    visit(a[key], b[key], path + [key])
        elif isinstance(a, list):
            for i in range(max(len(a), len(b))):
                if i >= len(a):
                    changes.append({"path": path + [i], "kind": "added", "right": b[i]})
                elif i >= len(b):
                    changes.append({"path": path + [i], "kind": "removed", "left": a[i]})
                else:
                    visit(a[i], b[i], path + [i])
        elif a != b:
            changes.append({"path": path, "kind": "changed", "left": a, "right": b})
    visit(left, right, [])
    return changes


@register("code", {"source": "x=1"}, [{"type": "NAME", "text": "x", "line": 1, "column": 0}, {"type": "OP", "text": "=", "line": 1, "column": 1}, {"type": "NUMBER", "text": "1", "line": 1, "column": 2}])
def python_tokens(source):
    """Tokenize Python source, retaining comments but omitting newline, indentation and end-marker tokens."""
    excluded = {tokenize.NEWLINE, tokenize.NL, tokenize.INDENT, tokenize.DEDENT, tokenize.ENDMARKER}
    return [{"type": token.tok_name[t.type], "text": t.string, "line": t.start[0], "column": t.start[1]}
            for t in tokenize.generate_tokens(io.StringIO(source).readline) if t.type not in excluded]


@register("code", {"source": "return 1"}, {"valid": False, "line": 1, "message": "'return' outside function"})
def compile_check(source):
    """Compile Python without executing it; catches syntax and context errors such as return outside function."""
    try:
        compile(source, "<tool-input>", "exec", dont_inherit=True)
        return {"valid": True}
    except SyntaxError as error:
        return {"valid": False, "line": error.lineno, "message": error.msg}
