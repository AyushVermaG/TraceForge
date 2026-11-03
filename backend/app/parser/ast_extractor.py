"""Python AST parser extracting modules, classes, functions, and call sites."""
import ast
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger("TraceForge.ASTExtractor")

@dataclass
class ExtractedCall:
    caller_qualname: str
    call_expr: str
    func_identifier: str
    attribute_name: Optional[str] = None
    receiver: Optional[str] = None
    line_no: int = 1
    col_offset: int = 0

@dataclass
class ExtractedFunction:
    name: str
    qualname: str
    start_line: int
    end_line: int
    signature: str
    docstring: Optional[str] = None
    is_async: bool = False
    is_method: bool = False
    parent_class: Optional[str] = None
    calls: List[ExtractedCall] = field(default_factory=list)

@dataclass
class ExtractedClass:
    name: str
    qualname: str
    start_line: int
    end_line: int
    docstring: Optional[str] = None
    bases: List[str] = field(default_factory=list)
    methods: List[ExtractedFunction] = field(default_factory=list)

@dataclass
class ExtractedImport:
    module: str
    name: Optional[str] = None
    alias: Optional[str] = None
    line_no: int = 1
    is_from: bool = False

@dataclass
class ParsedFileResult:
    relative_path: str
    module_dot_path: str
    line_count: int
    docstring: Optional[str] = None
    classes: List[ExtractedClass] = field(default_factory=list)
    functions: List[ExtractedFunction] = field(default_factory=list)
    imports: List[ExtractedImport] = field(default_factory=list)
    syntax_error: Optional[str] = None

def get_signature_str(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    """Format function parameter signature safely."""
    try:
        args_parts = []
        for a in node.args.posonlyargs:
            args_parts.append(a.arg)
        if node.args.posonlyargs:
            args_parts.append("/")
        for a in node.args.args:
            annotation = f": {ast.unparse(a.annotation)}" if a.annotation else ""
            args_parts.append(f"{a.arg}{annotation}")
        if node.args.vararg:
            args_parts.append(f"*{node.args.vararg.arg}")
        for a in node.args.kwonlyargs:
            annotation = f": {ast.unparse(a.annotation)}" if a.annotation else ""
            args_parts.append(f"{a.arg}{annotation}")
        if node.args.kwarg:
            args_parts.append(f"**{node.args.kwarg.arg}")
        
        ret_annotation = f" -> {ast.unparse(node.returns)}" if node.returns else ""
        return f"({', '.join(args_parts)}){ret_annotation}"
    except Exception:
        return "()"

class ASTVisitor(ast.NodeVisitor):
    """Walks the AST of a single Python file to extract symbols and calls."""

    def __init__(self, relative_path: str, module_dot_path: str):
        self.relative_path = relative_path
        self.module_dot_path = module_dot_path
        self.classes: List[ExtractedClass] = []
        self.functions: List[ExtractedFunction] = []
        self.imports: List[ExtractedImport] = []
        
        # Scopes tracking
        self.current_class: Optional[str] = None
        self.current_function: Optional[ExtractedFunction] = None

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            self.imports.append(ExtractedImport(
                module=alias.name,
                alias=alias.asname,
                line_no=node.lineno,
                is_from=False
            ))
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        mod = node.module or ""
        # Handle relative imports (e.g. from .core import engine)
        if node.level > 0:
            prefix = "." * node.level
            mod = f"{prefix}{mod}" if mod else prefix

        for alias in node.names:
            self.imports.append(ExtractedImport(
                module=mod,
                name=alias.name,
                alias=alias.asname,
                line_no=node.lineno,
                is_from=True
            ))
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef):
        prev_class = self.current_class
        self.current_class = node.name
        
        bases = []
        for b in node.bases:
            try:
                bases.append(ast.unparse(b))
            except Exception:
                pass

        cls_obj = ExtractedClass(
            name=node.name,
            qualname=node.name if not prev_class else f"{prev_class}.{node.name}",
            start_line=node.lineno,
            end_line=getattr(node, 'end_lineno', node.lineno),
            docstring=ast.get_docstring(node),
            bases=bases
        )

        # Visit class body to collect methods
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                method = self._parse_function(item, parent_class=node.name)
                cls_obj.methods.append(method)
            else:
                self.visit(item)

        self.classes.append(cls_obj)
        self.current_class = prev_class

    def visit_FunctionDef(self, node: ast.FunctionDef):
        if not self.current_class:
            fn = self._parse_function(node, parent_class=None)
            self.functions.append(fn)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        if not self.current_class:
            fn = self._parse_function(node, parent_class=None)
            self.functions.append(fn)

    def _parse_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef, parent_class: Optional[str]) -> ExtractedFunction:
        qualname = f"{parent_class}.{node.name}" if parent_class else node.name
        signature = get_signature_str(node)
        
        fn_obj = ExtractedFunction(
            name=node.name,
            qualname=qualname,
            start_line=node.lineno,
            end_line=getattr(node, 'end_lineno', node.lineno),
            signature=signature,
            docstring=ast.get_docstring(node),
            is_async=isinstance(node, ast.AsyncFunctionDef),
            is_method=parent_class is not None,
            parent_class=parent_class
        )

        prev_fn = self.current_function
        self.current_function = fn_obj

        # Collect internal calls inside this function body
        for body_item in node.body:
            self._find_calls(body_item, fn_obj)

        self.current_function = prev_fn
        return fn_obj

    def _find_calls(self, node: ast.AST, fn_obj: ExtractedFunction):
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                try:
                    call_expr = ast.unparse(child)
                except Exception:
                    call_expr = "call()"

                func_node = child.func
                # Case 1: Simple function call: foo(...)
                if isinstance(func_node, ast.Name):
                    fn_obj.calls.append(ExtractedCall(
                        caller_qualname=fn_obj.qualname,
                        call_expr=call_expr,
                        func_identifier=func_node.id,
                        receiver=None,
                        attribute_name=None,
                        line_no=child.lineno,
                        col_offset=child.col_offset
                    ))
                # Case 2: Attribute call: receiver.method(...) or self.method(...)
                elif isinstance(func_node, ast.Attribute):
                    receiver = None
                    try:
                        receiver = ast.unparse(func_node.value)
                    except Exception:
                        pass
                    
                    fn_obj.calls.append(ExtractedCall(
                        caller_qualname=fn_obj.qualname,
                        call_expr=call_expr,
                        func_identifier=f"{receiver}.{func_node.attr}" if receiver else func_node.attr,
                        receiver=receiver,
                        attribute_name=func_node.attr,
                        line_no=child.lineno,
                        col_offset=child.col_offset
                    ))

def file_path_to_module_dot_path(rel_path: Path) -> str:
    """Convert relative Path('sample_project/core/engine.py') -> 'sample_project.core.engine'."""
    parts = list(rel_path.parts)
    if parts and parts[-1].endswith(".py"):
        parts[-1] = parts[-1][:-3]
    if parts and parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)

def parse_python_file(file_path: Path, root_dir: Path) -> ParsedFileResult:
    """Parse a single Python file into structured AST results."""
    rel_path = file_path.relative_to(root_dir)
    rel_path_str = rel_path.as_posix()
    module_dot_path = file_path_to_module_dot_path(rel_path)

    try:
        content = file_path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return ParsedFileResult(
            relative_path=rel_path_str,
            module_dot_path=module_dot_path,
            line_count=0,
            syntax_error=f"File read error: {str(e)}"
        )

    lines = content.splitlines()
    line_count = len(lines)

    try:
        tree = ast.parse(content, filename=rel_path_str)
    except SyntaxError as e:
        logger.warning(f"Syntax error parsing {rel_path_str} at line {e.lineno}: {e.msg}")
        return ParsedFileResult(
            relative_path=rel_path_str,
            module_dot_path=module_dot_path,
            line_count=line_count,
            syntax_error=f"SyntaxError at line {e.lineno}: {e.msg}"
        )

    visitor = ASTVisitor(relative_path=rel_path_str, module_dot_path=module_dot_path)
    visitor.visit(tree)

    return ParsedFileResult(
        relative_path=rel_path_str,
        module_dot_path=module_dot_path,
        line_count=line_count,
        docstring=ast.get_docstring(tree),
        classes=visitor.classes,
        functions=visitor.functions,
        imports=visitor.imports,
        syntax_error=None
    )
