"""Unit tests for static call resolution and confidence scoring."""
from pathlib import Path
from app.parser.ast_extractor import parse_python_file
from app.parser.symbol_table import SymbolCatalog, SymbolDef, ImportDef
from app.parser.call_resolver import StaticCallResolver

def test_static_call_resolution_local_and_method(tmp_path: Path):
    code = '''
def helper(x):
    return x + 1

class Calculator:
    def add(self, a, b):
        return helper(a) + self.internal_sum(b)

    def internal_sum(self, n):
        return n
'''
    py_file = tmp_path / "calc.py"
    py_file.write_text(code, encoding="utf-8")

    parsed = parse_python_file(py_file, tmp_path)
    catalog = SymbolCatalog(repo_id="test_repo")
    
    # Register symbols in catalog
    catalog.register_symbol(SymbolDef(
        repo_id="test_repo",
        file_path="calc.py",
        module_path="calc",
        qualname="helper",
        kind="Function",
        start_line=2,
        end_line=3
    ))
    catalog.register_symbol(SymbolDef(
        repo_id="test_repo",
        file_path="calc.py",
        module_path="calc",
        qualname="Calculator.internal_sum",
        kind="Function",
        parent_class="Calculator",
        start_line=9,
        end_line=10,
        is_method=True
    ))

    resolver = StaticCallResolver(repo_id="test_repo", catalog=catalog)
    edges = resolver.resolve_file_calls(parsed)

    assert len(edges) >= 2
    # Verify local call to helper
    helper_edge = next(e for e in edges if e.target_name == "helper")
    assert helper_edge.confidence == "exact"
    assert helper_edge.resolution_type == "local"

    # Verify method call to internal_sum
    method_edge = next(e for e in edges if e.target_name == "internal_sum")
    assert method_edge.confidence == "exact"
    assert method_edge.resolution_type == "method"
