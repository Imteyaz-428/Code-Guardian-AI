# Project Progress — Day 11

## Date
10 September 2026

## Focus
Call Graph Implementation, Project-Level Integration, and Import-Aware Resolution

---

## 1. Objective

The objective of Day 11 was to extend Code Guardian AI from file-level structural analysis toward repository-level program understanding by implementing and integrating a Call Graph.

The Call Graph represents relationships between functions and methods in the analyzed repository.

The main relationship is:

    Caller → Callee

For example:

    main.py::main
            ↓
    auth.py::login
            ↓
    database.py::get_user

This provides an important foundation for the future CFG, Data Flow Graph, and Unified Code Graph stages.

---

## 2. Why Call Graph Was Added

Earlier versions of Code Guardian AI could:

- Parse Python source code.
- Extract functions and classes.
- Calculate function-level metrics.
- Detect file dependencies.
- Build dependency graphs.
- Detect circular dependencies.
- Calculate deterministic risk scores.

However, the system did not yet understand direct function-to-function relationships across a repository.

For example, dependency analysis can identify:

    main.py → auth.py

but a Call Graph can provide a more precise relationship:

    main.py::main
            ↓
    auth.py::login

This gives Code Guardian AI deeper structural information about how execution can move between functions.

---

## 3. Call Graph Data Structure

A new CallGraph structure was implemented.

It maintains two directions of relationships:

    caller → callees

and:

    callee → callers

The main structures are:

    calls
    called_by

This allows the system to answer both:

- Which functions does this function call?
- Which functions call this function?

The graph also provides:

- All function nodes.
- All caller-callee edges.
- Number of functions.
- Number of call relationships.

---

## 4. Function Identification

Functions are represented using repository-relative identifiers.

For a top-level function:

    main.py::main

For another file:

    auth.py::login

For a class method:

    services.py::UserService::login

This avoids machine-specific absolute paths and creates stable identifiers for later graph processing and machine-learning datasets.

---

## 5. AST-Based Call Detection

The Call Graph Analyzer uses Python's AST representation to identify function calls.

The analyzer walks through each function and searches for:

    ast.Call

The call expression is then converted into a readable name.

Examples:

    calculate()

becomes:

    calculate

and:

    utils.calculate()

becomes:

    utils.calculate

This allows the analyzer to process both normal function calls and attribute-based method calls.

---

## 6. Function and Method Collection

A FunctionCollector was implemented to collect functions and methods from every parsed AST.

It supports:

- Regular functions.
- Async functions.
- Class methods.
- Nested class structures.

Function identifiers are generated using the source file and, where applicable, the class name.

Examples:

    main.py::process

    services.py::UserService::login

This allows methods with identical names in different classes to remain distinguishable.

---

## 7. ProjectAnalyzer Integration

The Call Graph was integrated into ProjectAnalyzer.

The previous workflow was approximately:

    RepositoryManager
          ↓
    ASTParser
          ↓
    CodeExtractor
          ↓
    MetricsAnalyzer
          ↓
    AnalysisResult

The workflow now additionally retains all successfully parsed AST trees and passes them to CallGraphAnalyzer.

The updated architecture is:

    RepositoryManager
          ↓
    Python files
          ↓
    ASTParser
          ↓
       AST trees
       /      \
      /        \
    Metrics   Call Graph
      ↓          ↓
    Results   Repository Graph

The Call Graph is stored as repository-level analysis data rather than being duplicated inside every AnalysisResult.

---

## 8. Repository-Relative Paths

During integration, an issue was discovered with absolute file paths.

Initially, the Call Graph received paths such as:

    /Users/.../Code-Guadian-AI/main.py

This caused unstable function identifiers.

The implementation was changed to convert paths to repository-relative paths:

    main.py
    auth.py
    services/user.py

Therefore graph identifiers now remain portable:

    main.py::main
    auth.py::login
    services/user.py::get_user

This is important for future graph storage, visualization, datasets, and machine-learning processing.

---

## 9. Import-Aware Call Resolution

The initial Call Graph used simple name-based resolution.

For example:

    calculate()

was resolved by searching for a function named:

    calculate

This worked for simple repositories but could become ambiguous when multiple modules contained functions with the same name.

The resolver was therefore enhanced to understand imports.

---

## 10. Supported Import Patterns

The improved resolver supports:

### Normal function import

    from utils import calculate

    def process():
        calculate()

Resolution:

    process
       ↓
    utils.py::calculate


### Module import

    import utils

    def process():
        utils.calculate()

Resolution:

    process
       ↓
    utils.py::calculate


### Function import alias

    from utils import calculate as calc

    def process():
        calc()

Resolution:

    process
       ↓
    utils.py::calculate


### Relative function import

    from .utils import calculate

    def process():
        calculate()

Resolution:

    package/main.py::process
            ↓
    package/utils.py::calculate


### Relative module import

    from . import utils

    def process():
        utils.calculate()

Resolution:

    package/main.py::process
            ↓
    package/utils.py::calculate


### Parent-package relative import

    from ..utils import calculate

Resolution correctly handles the parent package relationship.

---

## 11. Resolution Strategy

The Call Graph resolver now uses multiple levels of resolution.

The general order is:

    1. Same-class method
           ↓
    2. Import-aware resolution
           ↓
    3. Same-file function
           ↓
    4. Unique repository-wide function
           ↓
    5. Ambiguous/external call → ignored

This prevents the analyzer from creating incorrect edges when a call cannot be reliably resolved.

---

## 12. Handling Ambiguous Calls

Static analysis cannot reliably determine every Python call.

For example:

    obj.calculate()

may depend on the runtime type of `obj`.

Similarly:

    getattr(service, "calculate")()

cannot always be resolved statically.

Therefore the current implementation intentionally avoids guessing when a call is ambiguous or external.

This keeps the Call Graph conservative and reduces false relationships.

---

## 13. Testing

Dedicated Call Graph tests were created and expanded throughout the implementation.

The final Call Graph test suite contains 10 tests covering:

1. Basic call graph.
2. Cross-file call graph.
3. Class method call graph.
4. Same method names in different classes.
5. `from module import function`.
6. `import module`.
7. Import aliases.
8. Relative function imports.
9. Relative module imports.
10. Parent-package relative imports.

Final result:

    10 passed

---

## 14. ProjectAnalyzer Integration Testing

Additional tests were created for ProjectAnalyzer.

The tests verify:

- Call Graph creation during project analysis.
- Repository-level function relationships.
- Cross-file function relationships.
- Caller lookup.
- Callee lookup.
- Graph statistics.

Example repository relationship:

    main.py::main
          ↓
    auth.py::login
          ↓
    database.py::get_user

Both ProjectAnalyzer integration tests passed.

---

## 15. Regression Testing

After implementing and improving Call Graph functionality, the complete project test suite was executed.

Final result:

    34 passed in 0.10s

This confirms that the new Call Graph functionality did not break the existing:

- AST parser.
- Code extraction.
- Configuration.
- Dependency analyzer.
- Dependency graph.
- Metrics analyzer.
- Project analyzer.
- Repository security validation.

---

## 16. Final Architecture After Day 11

The current backend architecture is:

    Repository
        ↓
    RepositoryManager
        ↓
    Python File Discovery
        ↓
    ASTParser
        ↓
    AST
        ├── CodeExtractor
        │       ↓
        │   AnalysisResult
        │
        ├── MetricsAnalyzer
        │       ↓
        │   Function Metrics
        │
        ├── DependencyAnalyzer
        │       ↓
        │   Dependency Graph
        │
        ├── RiskEngine
        │       ↓
        │   Risk Findings
        │
        └── CallGraphAnalyzer
                ↓
            Call Graph
                ↓
          Caller → Callee

---

## 17. Current Project Status

At the end of Day 11, Code Guardian AI has a stable static-analysis foundation.

Implemented capabilities include:

- Repository management.
- Secure repository path validation.
- Python file discovery.
- Python AST parsing.
- Function/class extraction.
- Function-level metrics.
- Cyclomatic complexity.
- Dependency analysis.
- Dependency graph construction.
- Circular dependency detection.
- Function/file/project risk analysis.
- Repository-level Call Graph.
- Cross-file call resolution.
- Import-aware call resolution.
- Relative import resolution.
- ProjectAnalyzer Call Graph integration.
- Automated regression testing.

The complete test suite currently passes:

    34 / 34 tests

---

## 18. What Was Not Done Today

API integration was intentionally not started on Day 11.

The Call Graph was first stabilized and tested independently and through ProjectAnalyzer.

The next stage will be to expose the verified Call Graph through the FastAPI analysis response.

---

## 19. Next Step

Day 12 will focus on:

    FastAPI Call Graph Integration

Planned workflow:

    ProjectAnalyzer
          ↓
    CallGraph
          ↓
    API response schema
          ↓
    POST /analyze
          ↓
    Call Graph JSON
          ↓
    API integration tests

The frontend visualization will be considered only after the API response is stable and verified.

---

## 20. Day 11 Outcome

Day 11 successfully moved Code Guardian AI from basic repository/file analysis toward repository-level program-flow understanding.

The most important achievement was the implementation of a tested Call Graph that can represent function relationships within and across Python files while handling common absolute, aliased, and relative import patterns.

The system is now ready for the next architectural layer: exposing the Call Graph through the backend API.