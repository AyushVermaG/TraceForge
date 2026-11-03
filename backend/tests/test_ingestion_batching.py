"""Regression tests for batched repository persistence to prevent ingestion hangs."""
from unittest.mock import MagicMock, patch
from app.services.ingestion_service import IngestionService
from app.parser.ast_extractor import ParsedFileResult, ExtractedClass, ExtractedFunction, ExtractedImport
from app.parser.symbol_table import SymbolCatalog
from app.parser.call_resolver import ResolvedCallEdge

def test_persist_to_neo4j_uses_batched_unwind():
    """Verify that _persist_to_neo4j executes O(1) batched UNWIND queries rather than O(N) sequential queries."""
    service = IngestionService()

    # Generate synthetic repository data with 20 files, 40 classes, 80 methods, 100 calls
    catalog = SymbolCatalog(repo_id="repo_regression_test")
    catalog.external_packages.update(["os", "sys", "json", "requests", "urllib3"])

    parsed_results = []
    resolved_calls = []

    for i in range(20):
        cls = ExtractedClass(
            name=f"Service{i}",
            qualname=f"Service{i}",
            start_line=1,
            end_line=50,
            docstring="Doc",
            bases=["object"],
            methods=[
                ExtractedFunction(
                    name=f"method_{j}",
                    qualname=f"Service{i}.method_{j}",
                    start_line=10 + j * 5,
                    end_line=14 + j * 5,
                    signature="()",
                    docstring="Method",
                    is_method=True
                )
                for j in range(4)
            ]
        )
        fns = [
            ExtractedFunction(
                name=f"standalone_{k}",
                qualname=f"standalone_{k}",
                start_line=30 + k * 5,
                end_line=34 + k * 5,
                signature="()",
                is_method=False
            )
            for k in range(2)
        ]
        imports = [
            ExtractedImport(module="requests", name="get", line_no=1, is_from=True),
            ExtractedImport(module="json", line_no=2, is_from=False),
        ]
        parsed_results.append(ParsedFileResult(
            relative_path=f"pkg/mod_{i}.py",
            module_dot_path=f"pkg.mod_{i}",
            line_count=60,
            classes=[cls],
            functions=fns,
            imports=imports
        ))

        # Add calls
        for j in range(4):
            resolved_calls.append(ResolvedCallEdge(
                source_id=f"func:repo_regression_test:pkg/mod_{i}.py:Service{i}.method_{j}",
                target_id="pkg:requests",
                call_expr="requests.get()",
                line_no=12 + j * 5,
                confidence="approximate",
                resolution_type="external",
                target_name="requests.get",
                details="External call"
            ))
            resolved_calls.append(ResolvedCallEdge(
                source_id=f"func:repo_regression_test:pkg/mod_{i}.py:Service{i}.method_{j}",
                target_id=f"func:repo_regression_test:pkg/mod_{i}.py:standalone_0",
                call_expr="standalone_0()",
                line_no=13 + j * 5,
                confidence="exact",
                resolution_type="local",
                target_name="standalone_0",
                details="Local call"
            ))

    mock_session = MagicMock()
    mock_driver = MagicMock()
    mock_driver.session.return_value.__enter__.return_value = mock_session

    with patch("app.services.ingestion_service.neo4j_client.get_driver", return_value=mock_driver):
        service._persist_to_neo4j(
            repo_id="repo_regression_test",
            repo_name="regression_test",
            parsed_results=parsed_results,
            catalog=catalog,
            resolved_calls=resolved_calls
        )

    # Total queries executed must be bounded (less than 15) rather than O(N) (~300 queries)
    executed_queries = mock_session.run.call_args_list
    assert len(executed_queries) < 15, f"Expected < 15 batched queries, got {len(executed_queries)}"

    # Confirm UNWIND parameter was used in the batch queries
    cypher_statements = [call[0][0] for call in executed_queries]
    unwind_queries = [stmt for stmt in cypher_statements if "UNWIND $batch AS item" in stmt]
    assert len(unwind_queries) >= 6, f"Expected at least 6 UNWIND queries, got {len(unwind_queries)}"
