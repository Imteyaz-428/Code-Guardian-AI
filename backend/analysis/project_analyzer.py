from __future__ import annotations

from pathlib import Path

from backend.analysis.call_graph import CallGraphAnalyzer
from backend.analysis.cfg import CFGAnalyzer
from backend.analysis.data_flow import DataFlowAnalyzer
from backend.analysis.dead_definitions import DeadDefinitionAnalyzer
from backend.analysis.def_use import DefUseAnalyzer
from backend.analysis.function_collector import FunctionCollector
from backend.analysis.metrics import MetricsAnalyzer
from backend.analysis.reaching_definitions import (
    ReachingDefinitionsAnalyzer,
)
from backend.analysis.risk_labels import RiskLabelGenerator
from backend.analysis.taint_analysis import TaintAnalyzer
from backend.analysis.unified_code_graph import (
    UnifiedCodeGraph,
    UnifiedCodeGraphBuilder,
)
from backend.analysis.use_before_definition import (
    UseBeforeDefinitionAnalyzer,
)
from backend.models.analysis_result import AnalysisResult
from backend.parsing.ast_parser import ASTParser, CodeExtractor
from backend.repository.manager import RepositoryManager


class ProjectAnalyzer:
    """
    Complete static analysis orchestrator for Code Guardian AI.

    Pipeline:

        Repository
            ↓
        Python Files
            ↓
        AST
            ↓
        Metrics
            ↓
        Function Collection
            ↓
        CFG
            ↓
        Data Flow
            ↓
        Reaching Definitions
            ↓
        Def-Use
            ↓
        Use-Before-Definition
            ↓
        Dead Definitions
            ↓
        Interprocedural Taint Analysis
            ↓
        Call Graph
            ↓
        Unified Code Graph
            ↓
        Static Risk Labels

    This class performs STATIC analysis only.

    GNN prediction is intentionally kept separate.

    Later pipeline:

        UnifiedCodeGraph
                ↓
        GraphDataset
                ↓
        GNN
                ↓
        ML Risk Prediction

    Then:

        Static Risk
             +
        GNN Risk
             ↓
        Final Risk Assessment
    """

    # =========================================================
    # INITIALIZATION
    # =========================================================

    def __init__(
        self,
        repository_path: str | Path,
    ):
        self.repository_manager = RepositoryManager(
            repository_path
        )

        self.errors: list[str] = []

        # -----------------------------------------------------
        # Repository-level Call Graph
        # -----------------------------------------------------

        self.call_graph = None

        # -----------------------------------------------------
        # Repository-level CFGs
        #
        # function_id -> ControlFlowGraph
        # -----------------------------------------------------

        self.control_flow_graphs = {}

        # -----------------------------------------------------
        # Function AST nodes
        #
        # function_id -> AST FunctionDef / AsyncFunctionDef
        # -----------------------------------------------------

        self.functions = {}

        # -----------------------------------------------------
        # Data Flow
        #
        # function_id -> DataFlowResult
        # -----------------------------------------------------

        self.data_flow_results = {}

        # -----------------------------------------------------
        # Reaching Definitions
        #
        # function_id -> ReachingDefinitionsResult
        # -----------------------------------------------------

        self.reaching_definitions = {}

        # -----------------------------------------------------
        # Def-Use
        #
        # function_id -> DefUseResult
        # -----------------------------------------------------

        self.def_use_results = {}

        # -----------------------------------------------------
        # Use-Before-Definition
        #
        # function_id -> UseBeforeDefinitionResult
        # -----------------------------------------------------

        self.use_before_definition = {}

        # -----------------------------------------------------
        # Dead Definitions
        #
        # function_id -> DeadDefinitionResult
        # -----------------------------------------------------

        self.dead_definitions = {}

        # -----------------------------------------------------
        # Interprocedural Taint Analysis
        #
        # One project-level TaintAnalysisResult.
        #
        # This is intentionally NOT a dictionary because
        # TaintAnalyzer.analyze_project() performs propagation
        # across function boundaries.
        # -----------------------------------------------------

        self.taint_results = None

        # -----------------------------------------------------
        # Unified Code Graph
        # -----------------------------------------------------

        self.unified_code_graph: UnifiedCodeGraph | None = None

        # -----------------------------------------------------
        # Static Risk Labels
        #
        # Generated from UnifiedCodeGraph.
        # -----------------------------------------------------

        self.risk_labels = None

    # =========================================================
    # MAIN ANALYSIS
    # =========================================================

    def analyze(self) -> list[AnalysisResult]:
        """
        Analyze the complete repository.

        This is the main static-analysis entry point.

        Returns
        -------
        list[AnalysisResult]
            File-level static analysis results.

        Side Effects
        ------------
        Populates:

            self.functions
            self.control_flow_graphs
            self.data_flow_results
            self.reaching_definitions
            self.def_use_results
            self.use_before_definition
            self.dead_definitions
            self.taint_results
            self.call_graph
            self.unified_code_graph
            self.risk_labels
        """

        # -----------------------------------------------------
        # Reset previous analysis state
        # -----------------------------------------------------

        self._reset_analysis_state()

        results: list[AnalysisResult] = []

        trees = {}

        root = (
            self.repository_manager
            .repository_path
            .resolve()
        )

        # =====================================================
        # PASS 1
        #
        # AST
        # Metrics
        # Function Collection
        # CFG
        # =====================================================

        for file_path in (
            self.repository_manager.get_python_files()
        ):

            try:

                tree = ASTParser(
                    file_path
                ).parse()

            except ValueError as exc:

                self.errors.append(
                    str(exc)
                )

                continue

            # -------------------------------------------------
            # Repository-relative path
            # -------------------------------------------------

            relative_path = (
                file_path.resolve()
                .relative_to(root)
                .as_posix()
            )

            # Keep AST tree for repository-level analysis.

            trees[
                relative_path
            ] = tree

            # -------------------------------------------------
            # AST Extraction
            # -------------------------------------------------

            extractor = CodeExtractor()

            extractor.visit(tree)

            result = extractor.get_result(
                file_path
            )

            # -------------------------------------------------
            # Metrics
            # -------------------------------------------------

            metrics_analyzer = (
                MetricsAnalyzer()
            )

            metrics_analyzer.visit(tree)

            result.metrics = (
                metrics_analyzer.metrics
            )

            # -------------------------------------------------
            # Function Collection
            # -------------------------------------------------

            function_collector = (
                FunctionCollector(
                    relative_path
                )
            )

            function_collector.visit(tree)

            self.functions.update(
                function_collector.functions
            )

            # -------------------------------------------------
            # CFG
            # -------------------------------------------------

            cfg_analyzer = CFGAnalyzer()

            for (
                function_id,
                function_node,
            ) in function_collector.functions.items():

                try:

                    cfg = cfg_analyzer.analyze(
                        function_node
                    )

                    self.control_flow_graphs[
                        function_id
                    ] = cfg

                except Exception as exc:

                    self.errors.append(
                        (
                            f"CFG analysis failed for "
                            f"{function_id}: {exc}"
                        )
                    )

            results.append(
                result
            )

        # =====================================================
        # PASS 2
        #
        # Intra-procedural Data Flow
        #
        # Data Flow
        # Reaching Definitions
        # Def-Use
        # Use-Before-Definition
        # Dead Definitions
        # =====================================================

        self._run_data_flow_analysis()

        # =====================================================
        # PASS 3
        #
        # Interprocedural Taint Analysis
        # =====================================================

        self._run_taint_analysis()

        # =====================================================
        # PASS 4
        #
        # Repository Call Graph
        # =====================================================

        if trees:

            try:

                call_graph_analyzer = (
                    CallGraphAnalyzer()
                )

                self.call_graph = (
                    call_graph_analyzer.analyze(
                        trees
                    )
                )

            except Exception as exc:

                self.errors.append(
                    (
                        "Call graph analysis failed: "
                        f"{exc}"
                    )
                )

        # =====================================================
        # PASS 5
        #
        # Unified Code Graph
        # =====================================================

        self._build_unified_code_graph()

        # =====================================================
        # PASS 6
        #
        # Static Risk Labels
        # =====================================================

        self.risk_labels = (
            self.generate_risk_labels()
        )

        return results

    # =========================================================
    # RESET
    # =========================================================

    def _reset_analysis_state(self) -> None:
        """
        Reset all analysis state before a new run.
        """

        self.errors = []

        self.call_graph = None

        self.control_flow_graphs = {}

        self.functions = {}

        self.data_flow_results = {}

        self.reaching_definitions = {}

        self.def_use_results = {}

        self.use_before_definition = {}

        self.dead_definitions = {}

        self.taint_results = None

        self.unified_code_graph = None

        self.risk_labels = None

    # =========================================================
    # DATA FLOW PIPELINE
    # =========================================================

    def _run_data_flow_analysis(self) -> None:
        """
        Run all intra-procedural data-flow analyses.

        Pipeline:

            Function
                ↓
            CFG
                ↓
            Data Flow
                ↓
            Reaching Definitions
                ↓
            Def-Use
                ↓
            Use-Before-Definition
                ↓
            Dead Definitions

        Taint analysis is intentionally separate because
        the taint engine supports project-level interprocedural
        propagation.
        """

        data_flow_analyzer = (
            DataFlowAnalyzer()
        )

        reaching_definitions_analyzer = (
            ReachingDefinitionsAnalyzer()
        )

        def_use_analyzer = (
            DefUseAnalyzer()
        )

        use_before_definition_analyzer = (
            UseBeforeDefinitionAnalyzer()
        )

        dead_definition_analyzer = (
            DeadDefinitionAnalyzer()
        )

        # -----------------------------------------------------
        # Function-by-function analysis
        # -----------------------------------------------------

        for (
            function_id,
            function_node,
        ) in self.functions.items():

            cfg = self.control_flow_graphs.get(
                function_id
            )

            if cfg is None:

                continue

            try:

                # -------------------------------------------------
                # CFG Node Mapping
                # -------------------------------------------------

                cfg_node_map = (
                    self._build_cfg_node_map(
                        cfg
                    )
                )

                # -------------------------------------------------
                # Data Flow
                # -------------------------------------------------

                data_flow = (
                    data_flow_analyzer.analyze(
                        function_node=function_node,
                        function_id=function_id,
                        cfg_node_map=cfg_node_map,
                    )
                )

                self.data_flow_results[
                    function_id
                ] = data_flow

                # -------------------------------------------------
                # Reaching Definitions
                # -------------------------------------------------

                reaching = (
                    reaching_definitions_analyzer.analyze(
                        cfg=cfg,
                        data_flow=data_flow,
                    )
                )

                self.reaching_definitions[
                    function_id
                ] = reaching

                # -------------------------------------------------
                # Def-Use
                # -------------------------------------------------

                def_use = (
                    def_use_analyzer.analyze(
                        data_flow=data_flow,
                        reaching_definitions=reaching,
                    )
                )

                self.def_use_results[
                    function_id
                ] = def_use

                # -------------------------------------------------
                # Use-Before-Definition
                # -------------------------------------------------

                use_before = (
                    use_before_definition_analyzer.analyze(
                        data_flow=data_flow,
                        reaching_definitions=reaching,
                    )
                )

                self.use_before_definition[
                    function_id
                ] = use_before

                # -------------------------------------------------
                # Dead Definitions
                # -------------------------------------------------

                dead = (
                    dead_definition_analyzer.analyze(
                        reaching_definitions=reaching,
                        def_use=def_use,
                    )
                )

                self.dead_definitions[
                    function_id
                ] = dead

            except Exception as exc:

                self.errors.append(
                    (
                        f"Data-flow analysis failed for "
                        f"{function_id}: {exc}"
                    )
                )

    # =========================================================
    # TAINT ANALYSIS
    # =========================================================

    def _run_taint_analysis(self) -> None:
        """
        Run project-level interprocedural taint analysis.

        TaintAnalyzer.analyze_project() is used instead of
        running analyze() independently for each function.

        This preserves:

            - source detection
            - sink detection
            - sanitizer detection
            - variable propagation
            - function-call propagation
            - interprocedural source-to-sink flows
            - vulnerability classification
        """

        if not self.functions:
            return

        try:

            taint_analyzer = (
                TaintAnalyzer()
            )

            self.taint_results = (
                taint_analyzer.analyze_project(
                    functions=self.functions,
                )
            )

        except Exception as exc:

            self.errors.append(
                (
                    "Taint analysis failed: "
                    f"{exc}"
                )
            )

            self.taint_results = None

    # =========================================================
    # CFG NODE MAP
    # =========================================================

    @staticmethod
    def _build_cfg_node_map(
        cfg,
    ) -> dict[int, list[int]]:
        """
        Build:

            source line -> CFG node IDs

        Example:

            {
                2: [1],
                3: [2],
                4: [3],
            }

        This allows data-flow analysis to associate
        source-level definitions and uses with CFG nodes.
        """

        mapping: dict[int, list[int]] = {}

        for node in cfg.get_nodes():

            line = node.line

            if line is None:

                continue

            mapping.setdefault(
                line,
                [],
            ).append(
                node.id
            )

        return mapping

    # =========================================================
    # UNIFIED CODE GRAPH
    # =========================================================

    def _build_unified_code_graph(
        self,
    ) -> None:
        """
        Combine all static analysis information into
        one UnifiedCodeGraph.

        The UnifiedCodeGraph becomes the central representation
        used later for:

            - graph feature extraction
            - dataset generation
            - GNN training
            - GNN inference
            - explainability
        """

        builder = (
            UnifiedCodeGraphBuilder()
        )

        # =====================================================
        # FUNCTIONS
        # =====================================================

        for (
            function_id,
            function_node,
        ) in self.functions.items():

            cfg = (
                self.control_flow_graphs.get(
                    function_id
                )
            )

            # -------------------------------------------------
            # Extract file path
            # -------------------------------------------------

            file_path = (
                function_id.split(
                    "::",
                    1,
                )[0]
            )

            # -------------------------------------------------
            # Function name
            # -------------------------------------------------

            function_name = getattr(
                function_node,
                "name",
                function_id,
            )

            # -------------------------------------------------
            # Source line
            # -------------------------------------------------

            line = getattr(
                function_node,
                "lineno",
                None,
            )

            # -------------------------------------------------
            # Function node
            # -------------------------------------------------

            builder.add_function(
                function_id=function_id,
                file_path=file_path,
                function_name=function_name,
                line=line,
            )

            # -------------------------------------------------
            # CFG
            # -------------------------------------------------

            if cfg is not None:

                builder.add_cfg(
                    function_id=function_id,
                    cfg=cfg,
                )

            # -------------------------------------------------
            # Data Flow
            # -------------------------------------------------

            data_flow = (
                self.data_flow_results.get(
                    function_id
                )
            )

            if data_flow is not None:

                builder.add_data_flow(
                    function_id=function_id,
                    data_flow=data_flow,
                )

            # -------------------------------------------------
            # Def-Use
            # -------------------------------------------------

            def_use = (
                self.def_use_results.get(
                    function_id
                )
            )

            if def_use is not None:

                builder.add_def_use(
                    function_id=function_id,
                    def_use_result=def_use,
                )

            # -------------------------------------------------
            # Reaching Definitions
            # -------------------------------------------------

            reaching_definitions = (
                self.reaching_definitions.get(
                    function_id
                )
            )

            if reaching_definitions is not None:

                builder.add_reaching_definitions(
                    function_id=function_id,
                    reaching_definitions=(
                        reaching_definitions
                    ),
                )

            # -------------------------------------------------
            # Use-Before-Definition
            # -------------------------------------------------

            use_before_definition = (
                self.use_before_definition.get(
                    function_id
                )
            )

            if use_before_definition is not None:

                builder.add_use_before_definition(
                    function_id=function_id,
                    result=(
                        use_before_definition
                    ),
                )

            # -------------------------------------------------
            # Dead Definitions
            # -------------------------------------------------

            dead_definitions = (
                self.dead_definitions.get(
                    function_id
                )
            )

            if dead_definitions is not None:

                builder.add_dead_definitions(
                    function_id=function_id,
                    result=dead_definitions,
                )

        # =====================================================
        # CALL GRAPH
        # =====================================================

        if self.call_graph is not None:

            builder.add_call_graph(
                self.call_graph
            )

        # =====================================================
        # TAINT ANALYSIS
        #
        # Project-level result is added once.
        # =====================================================

        if self.taint_results is not None:

            builder.add_taint_edges(
                self.taint_results
            )

        # =====================================================
        # SAVE
        # =====================================================

        self.unified_code_graph = (
            builder.graph
        )

    # =========================================================
    # STATIC RISK LABELS
    # =========================================================

    def generate_risk_labels(self):
        """
        Generate explainable static-risk labels from the
        UnifiedCodeGraph.

        This is NOT the GNN prediction.

        These labels are generated from deterministic/static
        analysis signals and will later become the basis for
        supervised GNN training labels.

        analyze() must be called before this method.
        """

        if self.unified_code_graph is None:

            raise RuntimeError(
                "Unified code graph has not been built. "
                "Call analyze() before generating risk labels."
            )

        generator = RiskLabelGenerator(
            self.unified_code_graph
        )

        return generator.generate()

    # =========================================================
    # ANALYSIS SUMMARY
    # =========================================================

    def get_analysis_summary(self) -> dict:
        """
        Return a compact summary of the completed static
        analysis.

        This will later be consumed by the unified API.
        """

        graph = (
            self.unified_code_graph
        )

        taint_finding_count = 0
        taint_vulnerability_count = 0

        if self.taint_results is not None:

            taint_finding_count = (
                getattr(
                    self.taint_results,
                    "finding_count",
                    len(
                        getattr(
                            self.taint_results,
                            "findings",
                            [],
                        )
                    ),
                )
            )

            taint_vulnerability_count = (
                getattr(
                    self.taint_results,
                    "vulnerability_count",
                    len(
                        getattr(
                            self.taint_results,
                            "vulnerabilities",
                            [],
                        )
                    ),
                )
            )

        summary = {
            "files": len(
                self.repository_manager.get_python_files()
            ),
            "functions": len(
                self.functions
            ),
            "cfgs": len(
                self.control_flow_graphs
            ),
            "data_flow_functions": len(
                self.data_flow_results
            ),
            "reaching_definition_functions": len(
                self.reaching_definitions
            ),
            "def_use_functions": len(
                self.def_use_results
            ),
            "use_before_definition_functions": len(
                self.use_before_definition
            ),
            "dead_definition_functions": len(
                self.dead_definitions
            ),
            "taint_analysis_available": (
                self.taint_results is not None
            ),
            "taint_finding_count": (
                taint_finding_count
            ),
            "taint_vulnerability_count": (
                taint_vulnerability_count
            ),
            "call_graph_available": (
                self.call_graph is not None
            ),
            "unified_graph_available": (
                graph is not None
            ),
            "risk_labels_available": (
                self.risk_labels is not None
            ),
            "errors": self.errors,
        }

        if graph is not None:

            summary.update(
                {
                    "graph_nodes": len(
                        graph.nodes
                    ),
                    "graph_edges": len(
                        graph.edges
                    ),
                }
            )

        return summary