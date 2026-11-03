"""Unit tests for Python AST parsing."""
from pathlib import Path
from app.parser.ast_extractor import parse_python_file

def test_ast_extractor_sample_engine(tmp_path: Path):
    sample_code = '''"""Test Module Docstring."""
import time
from typing import Dict

class Worker:
    """Worker class."""
    def __init__(self, name: str):
        self.name = name

    def process(self, data: Dict) -> bool:
        """Process data."""
        self.log(data)
        return True

    def log(self, msg):
        pass

def standalone_task(x: int) -> int:
    return x * 2
'''
    py_file = tmp_path / "worker.py"
    py_file.write_text(sample_code, encoding="utf-8")

    result = parse_python_file(py_file, tmp_path)
    assert result.syntax_error is None
    assert result.docstring == "Test Module Docstring."
    assert len(result.classes) == 1
    
    cls = result.classes[0]
    assert cls.name == "Worker"
    assert len(cls.methods) == 3
    method_names = [m.name for m in cls.methods]
    assert "process" in method_names
    assert "log" in method_names

    process_method = next(m for m in cls.methods if m.name == "process")
    assert process_method.is_method is True
    assert len(process_method.calls) >= 1
    assert any(c.attribute_name == "log" for c in process_method.calls)

    assert len(result.functions) == 1
    assert result.functions[0].name == "standalone_task"

def test_ast_extractor_handles_syntax_error(tmp_path: Path):
    broken_code = '''def broken_syntax(x:
    return x +
'''
    py_file = tmp_path / "broken.py"
    py_file.write_text(broken_code, encoding="utf-8")

    result = parse_python_file(py_file, tmp_path)
    assert result.syntax_error is not None
    assert "SyntaxError" in result.syntax_error
