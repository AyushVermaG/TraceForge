"""Symbol table and repository-wide entity catalog for resolution."""
import sys
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field

# Python 3.10+ standard library modules set
STDLIB_MODULES: Set[str] = set(sys.stdlib_module_names) if hasattr(sys, "stdlib_module_names") else {
    "os", "sys", "re", "json", "time", "math", "logging", "hashlib",
    "pathlib", "typing", "collections", "itertools", "functools", "shutil",
    "zipfile", "asyncio", "threading", "dataclasses", "enum", "abc"
}

@dataclass
class SymbolDef:
    repo_id: str
    file_path: str
    module_path: str
    qualname: str
    kind: str  # Class, Function
    start_line: int
    end_line: int
    parent_class: Optional[str] = None
    signature: Optional[str] = None
    docstring: Optional[str] = None
    is_async: bool = False
    is_method: bool = False
    bases: List[str] = field(default_factory=list)

@dataclass
class ImportDef:
    module: str
    name: Optional[str] = None
    alias: Optional[str] = None
    line_no: int = 1
    is_from: bool = False

class SymbolCatalog:
    """Indexed catalog of all symbols in a parsed repository."""

    def __init__(self, repo_id: str):
        self.repo_id = repo_id
        # file_path -> list of symbols defined
        self.file_symbols: Dict[str, List[SymbolDef]] = {}
        # file_path -> list of imports
        self.file_imports: Dict[str, List[ImportDef]] = {}
        # module_dot_path -> file_path
        self.module_to_file: Dict[str, str] = {}
        # full qualname (module.class.func or module.func) -> SymbolDef
        self.qualname_to_symbol: Dict[str, SymbolDef] = {}
        # package names detected (e.g. requests, pydantic)
        self.external_packages: Set[str] = set()

    def register_module(self, module_dot_path: str, file_path: str):
        self.module_to_file[module_dot_path] = file_path

    def register_symbol(self, symbol: SymbolDef):
        self.file_symbols.setdefault(symbol.file_path, []).append(symbol)
        full_path = f"{symbol.module_path}.{symbol.qualname}" if symbol.module_path else symbol.qualname
        self.qualname_to_symbol[full_path] = symbol

    def register_import(self, file_path: str, imp: ImportDef):
        self.file_imports.setdefault(file_path, []).append(imp)
        root_pkg = imp.module.split(".")[0]
        if root_pkg in STDLIB_MODULES:
            # Stdlib package
            pass
        elif root_pkg in self.module_to_file:
            # Internal module
            pass
        else:
            # External 3rd party package
            self.external_packages.add(root_pkg)

    def find_local_symbol(self, file_path: str, name: str, parent_class: Optional[str] = None) -> Optional[SymbolDef]:
        """Find a symbol within the same file."""
        symbols = self.file_symbols.get(file_path, [])
        if parent_class:
            for s in symbols:
                if s.parent_class == parent_class and s.qualname.split(".")[-1] == name:
                    return s
        for s in symbols:
            if s.qualname == name or s.qualname.endswith(f".{name}"):
                return s
        return None
