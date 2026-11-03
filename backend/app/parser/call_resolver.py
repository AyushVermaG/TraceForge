"""Static function call inference engine with confidence scoring."""
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from app.parser.symbol_table import SymbolCatalog, STDLIB_MODULES
from app.parser.ast_extractor import ParsedFileResult, ExtractedCall

logger = logging.getLogger("TraceForge.CallResolver")

@dataclass
class ResolvedCallEdge:
    source_id: str
    target_id: str
    call_expr: str
    line_no: int
    confidence: str        # "exact" | "approximate"
    resolution_type: str   # "local" | "method" | "imported" | "external"
    target_name: str
    details: str

class StaticCallResolver:
    """Infers function-to-function and function-to-package calls from AST calls."""

    def __init__(self, repo_id: str, catalog: SymbolCatalog):
        self.repo_id = repo_id
        self.catalog = catalog

    def resolve_file_calls(self, parsed: ParsedFileResult) -> List[ResolvedCallEdge]:
        resolved_edges: List[ResolvedCallEdge] = []
        file_path = parsed.relative_path
        imports = self.catalog.file_imports.get(file_path, [])

        # Build local import map for this file: local_name -> (module, original_name)
        import_map: Dict[str, tuple[str, str]] = {}
        for imp in imports:
            if imp.is_from:
                # from x import y [as z]
                bound_name = imp.alias or imp.name or ""
                original_name = imp.name or ""
                import_map[bound_name] = (imp.module, original_name)
            else:
                # import x [as z]
                bound_name = imp.alias or imp.module.split(".")[0]
                import_map[bound_name] = (imp.module, "")

        # Process all functions (both top-level and class methods)
        all_functions = list(parsed.functions)
        for cls in parsed.classes:
            all_functions.extend(cls.methods)

        for fn in all_functions:
            source_id = f"func:{self.repo_id}:{file_path}:{fn.qualname}"
            
            for call in fn.calls:
                edge = self._resolve_single_call(
                    file_path=file_path,
                    caller_fn=fn,
                    call=call,
                    import_map=import_map,
                    source_id=source_id
                )
                if edge:
                    resolved_edges.append(edge)

        return resolved_edges

    def _resolve_single_call(
        self,
        file_path: str,
        caller_fn,
        call: ExtractedCall,
        import_map: Dict[str, tuple[str, str]],
        source_id: str
    ) -> Optional[ResolvedCallEdge]:
        # Case 1: self.method(...)
        if call.receiver in ("self", "cls") and call.attribute_name and caller_fn.parent_class:
            target_symbol = self.catalog.find_local_symbol(
                file_path=file_path,
                name=call.attribute_name,
                parent_class=caller_fn.parent_class
            )
            if target_symbol:
                target_id = f"func:{self.repo_id}:{target_symbol.file_path}:{target_symbol.qualname}"
                return ResolvedCallEdge(
                    source_id=source_id,
                    target_id=target_id,
                    call_expr=call.call_expr,
                    line_no=call.line_no,
                    confidence="exact",
                    resolution_type="method",
                    target_name=call.attribute_name,
                    details=f"Statically resolved class method '{caller_fn.parent_class}.{call.attribute_name}'"
                )

        # Case 2: Direct call: func_name(...)
        if call.receiver is None and call.func_identifier:
            func_name = call.func_identifier
            
            # Check if defined locally in the same file
            local_symbol = self.catalog.find_local_symbol(file_path=file_path, name=func_name)
            if local_symbol and local_symbol.qualname != caller_fn.qualname:
                prefix = "class" if local_symbol.kind == "Class" else "func"
                target_id = f"{prefix}:{self.repo_id}:{local_symbol.file_path}:{local_symbol.qualname}"
                return ResolvedCallEdge(
                    source_id=source_id,
                    target_id=target_id,
                    call_expr=call.call_expr,
                    line_no=call.line_no,
                    confidence="exact",
                    resolution_type="local",
                    target_name=func_name,
                    details=f"Statically resolved local symbol '{func_name}' in {file_path}"
                )

            # Check if imported from another module: from module import func_name
            if func_name in import_map:
                mod_path, orig_name = import_map[func_name]
                symbol_name = orig_name if orig_name else func_name
                
                # Check if internal project module
                full_qualname = f"{mod_path}.{symbol_name}"
                if full_qualname in self.catalog.qualname_to_symbol:
                    target_symbol = self.catalog.qualname_to_symbol[full_qualname]
                    prefix = "class" if target_symbol.kind == "Class" else "func"
                    target_id = f"{prefix}:{self.repo_id}:{target_symbol.file_path}:{target_symbol.qualname}"
                    return ResolvedCallEdge(
                        source_id=source_id,
                        target_id=target_id,
                        call_expr=call.call_expr,
                        line_no=call.line_no,
                        confidence="exact",
                        resolution_type="imported",
                        target_name=symbol_name,
                        details=f"Statically resolved cross-module import from '{mod_path}'"
                    )

        # Case 3: Attribute call on imported module: module.func(...)
        if call.receiver and call.attribute_name:
            if call.receiver in import_map:
                mod_path, _ = import_map[call.receiver]
                target_name = call.attribute_name
                full_qualname = f"{mod_path}.{target_name}"

                # Internal module symbol
                if full_qualname in self.catalog.qualname_to_symbol:
                    target_symbol = self.catalog.qualname_to_symbol[full_qualname]
                    prefix = "class" if target_symbol.kind == "Class" else "func"
                    target_id = f"{prefix}:{self.repo_id}:{target_symbol.file_path}:{target_symbol.qualname}"
                    return ResolvedCallEdge(
                        source_id=source_id,
                        target_id=target_id,
                        call_expr=call.call_expr,
                        line_no=call.line_no,
                        confidence="exact",
                        resolution_type="imported",
                        target_name=target_name,
                        details=f"Statically resolved module attribute call '{full_qualname}'"
                    )

                # External or stdlib package call (e.g. json.dumps or requests.get)
                root_pkg = mod_path.split(".")[0]
                target_id = f"pkg:{root_pkg}"
                return ResolvedCallEdge(
                    source_id=source_id,
                    target_id=target_id,
                    call_expr=call.call_expr,
                    line_no=call.line_no,
                    confidence="approximate",
                    resolution_type="external",
                    target_name=f"{root_pkg}.{target_name}",
                    details=f"External package invocation '{root_pkg}.{target_name}'"
                )

        return None
