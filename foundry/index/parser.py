"""tree-sitter Python parser for Foundry code index (FR-020, FR-021, FR-026)."""
from __future__ import annotations
import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

try:
    import tree_sitter_python as tspython
    from tree_sitter import Language, Parser
    _PYTHON_LANG = Language(tspython.language())
    _PARSER = Parser(_PYTHON_LANG)
    HAS_TREE_SITTER = True
except Exception:
    HAS_TREE_SITTER = False
    _PARSER = None


@dataclass
class FunctionRecord:
    file_path: str
    symbol_name: str
    symbol_type: str  # 'function' | 'method'
    start_line: int
    end_line: int
    body: str


@dataclass
class CallEdge:
    caller_path: str
    caller_symbol: str
    callee_path: str  # empty if unresolved
    callee_symbol: str


def file_hash(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def index_file(path: str | Path) -> list[FunctionRecord]:
    """Extract all function/method definitions from a Python file."""
    path = Path(path)
    source = path.read_bytes()
    if HAS_TREE_SITTER and _PARSER:
        return _parse_tree_sitter(str(path), source)
    return _parse_fallback(str(path), source)


def _parse_tree_sitter(file_path: str, source: bytes) -> list[FunctionRecord]:
    tree = _PARSER.parse(source)
    records: list[FunctionRecord] = []
    lines = source.decode("utf-8", errors="replace").splitlines()

    def walk(node, class_name: str | None = None) -> None:
        if node.type in ("function_definition", "async_function_definition"):
            name_node = node.child_by_field_name("name")
            sym = name_node.text.decode() if name_node else "<unknown>"
            sym = f"{class_name}.{sym}" if class_name else sym
            start = node.start_point[0]
            end = node.end_point[0]
            body = "\n".join(lines[start: end + 1])
            records.append(FunctionRecord(
                file_path=file_path,
                symbol_name=sym,
                symbol_type="method" if class_name else "function",
                start_line=start + 1,
                end_line=end + 1,
                body=body,
            ))
        elif node.type == "class_definition":
            name_node = node.child_by_field_name("name")
            cname = name_node.text.decode() if name_node else None
            for child in node.children:
                walk(child, class_name=cname)
            return
        for child in node.children:
            walk(child, class_name=class_name)

    walk(tree.root_node)
    return records


def _parse_fallback(file_path: str, source: bytes) -> list[FunctionRecord]:
    """Simple regex-based fallback when tree-sitter is unavailable."""
    import re
    records: list[FunctionRecord] = []
    text = source.decode("utf-8", errors="replace")
    lines = text.splitlines()
    pattern = re.compile(r"^\s*(async\s+)?def\s+(\w+)\s*\(")
    for i, line in enumerate(lines):
        m = pattern.match(line)
        if m:
            sym = m.group(2)
            end = i
            indent = len(line) - len(line.lstrip())
            for j in range(i + 1, min(i + 500, len(lines))):
                stripped = lines[j].strip()
                if stripped and (len(lines[j]) - len(lines[j].lstrip())) <= indent:
                    break
                end = j
            body = "\n".join(lines[i: end + 1])
            records.append(FunctionRecord(
                file_path=file_path,
                symbol_name=sym,
                symbol_type="function",
                start_line=i + 1,
                end_line=end + 1,
                body=body,
            ))
    return records


def extract_calls(file_path: str, source: bytes, known_symbols: set[str]) -> list[CallEdge]:
    """Extract call graph edges from a file (FR-021, direct static calls)."""
    if not HAS_TREE_SITTER or _PARSER is None:
        return []
    tree = _PARSER.parse(source)
    edges: list[CallEdge] = []
    current_func = [None]

    def walk(node, func_ctx: Optional[str] = None) -> None:
        if node.type in ("function_definition", "async_function_definition"):
            name_node = node.child_by_field_name("name")
            sym = name_node.text.decode() if name_node else None
            for child in node.children:
                walk(child, func_ctx=sym)
            return
        if node.type == "call" and func_ctx:
            func_node = node.child_by_field_name("function")
            if func_node:
                callee = func_node.text.decode().split(".")[-1]
                edges.append(CallEdge(
                    caller_path=file_path,
                    caller_symbol=func_ctx,
                    callee_path="",  # cross-file resolution happens in query.py
                    callee_symbol=callee,
                ))
        for child in node.children:
            walk(child, func_ctx=func_ctx)

    walk(tree.root_node)
    return edges
