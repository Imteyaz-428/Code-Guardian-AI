"""
Unified Code Graph
==================

Combines the structural relationships discovered by Code Guardian AI
into one graph representation.

Current sources:

    AST / project structure
    CFG
    Call Graph
    Dependency Graph
    Data Flow
    Def-Use
    Reaching Definitions
    Taint Analysis

The graph is intentionally framework-independent.

It does NOT depend on:
    - PyTorch
    - PyTorch Geometric
    - NetworkX

This keeps the analysis layer independent from the future ML layer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# ============================================================
# Edge Types
# ============================================================


class CodeGraphEdgeType(str, Enum):
    """
    Relationship types supported by the unified code graph.
    """

    CONTAINS = "contains"
    NESTS = "nests"

    HAS_CFG_NODE = "has_cfg_node"
    CONTROL_FLOW = "control_flow"

    CALLS = "calls"

    DEPENDS_ON = "depends_on"

    DEFINES = "defines"
    USES = "uses"
    DEF_USE = "def_use"

    REACHING_DEFINITION = "reaching_definition"

    USE_BEFORE_DEFINITION = "use_before_definition"

    DEAD_DEFINITION = "dead_definition"

    TAINT_FLOW = "taint_flow"

    DATA_DEPENDENCY = "data_dependency"

    INHERITS = "inherits"
    OVERRIDES = "overrides"

# ============================================================
# Node
# ============================================================


@dataclass
class CodeGraphNode:
    """
    Represents one node in the unified code graph.

    Examples:

        file
        class
        function
        method
        cfg_node
        definition
        use
        variable
    """

    id: str
    node_type: str

    name: str | None = None

    file: str | None = None

    line: int | None = None

    function_id: str | None = None

    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """
        Convert node to a JSON-compatible dictionary.
        """

        result = {
            "id": self.id,
            "type": self.node_type,
        }

        if self.name is not None:
            result["name"] = self.name

        if self.file is not None:
            result["file"] = self.file

        if self.line is not None:
            result["line"] = self.line

        if self.function_id is not None:
            result["function_id"] = self.function_id

        if self.metadata:
            result["metadata"] = self.metadata

        return result


# ============================================================
# Edge
# ============================================================


@dataclass(frozen=True)
class CodeGraphEdge:
    """
    Represents a relationship between two graph nodes.
    """

    source: str

    target: str

    edge_type: CodeGraphEdgeType

    metadata: tuple[tuple[str, Any], ...] = ()

    def to_dict(self) -> dict[str, Any]:
        """
        Convert edge to a JSON-compatible dictionary.
        """

        return {
            "source": self.source,
            "target": self.target,
            "type": self.edge_type.value,
            "metadata": dict(self.metadata),
        }


# ============================================================
# Unified Graph
# ============================================================


class UnifiedCodeGraph:
    """
    Main graph structure.

    The graph maintains:

        nodes
        edges

    and provides helper methods for adding and querying them.
    """

    def __init__(self) -> None:
        self.nodes: dict[str, CodeGraphNode] = {}
        self.edges: list[CodeGraphEdge] = []

        self._edge_keys: set[
            tuple[
                str,
                str,
                CodeGraphEdgeType,
                tuple[tuple[str, Any], ...],
            ]
        ] = set()

        # Fast adjacency indexes.
        self._outgoing_edges: dict[
            str, list[CodeGraphEdge]
        ] = {}

        self._incoming_edges: dict[
            str, list[CodeGraphEdge]
        ] = {}

    # --------------------------------------------------------
    # Nodes
    # --------------------------------------------------------

    def add_node(
        self,
        
        node_id: str,
        node_type: str,
        name: str | None = None,
        file: str | None = None,
        line: int | None = None,
        function_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> CodeGraphNode:
        """
        Add a node.

        If the node already exists, its metadata is updated.
        """

        if node_id in self.nodes:

            node = self.nodes[node_id]

            if name is not None:
                node.name = name

            if file is not None:
                node.file = file

            if line is not None:
                node.line = line

            if function_id is not None:
                node.function_id = function_id

            if metadata:
                node.metadata.update(metadata)

            return node

        node = CodeGraphNode(
            id=node_id,
            node_type=node_type,
            name=name,
            file=file,
            line=line,
            function_id=function_id,
            metadata=metadata or {},
        )

        self.nodes[node_id] = node
        self._outgoing_edges.setdefault(node_id, [])
        self._incoming_edges.setdefault(node_id, [])

        return node

    # --------------------------------------------------------
    # Edges
    # --------------------------------------------------------

    def add_edge(
        self,
        source: str,
        target: str,
        edge_type: CodeGraphEdgeType | str,
        metadata: dict[str, Any] | None = None,
    ) -> CodeGraphEdge:
        """Add an edge and update adjacency indexes efficiently."""

        if source not in self.nodes:
            raise ValueError(f"Source node does not exist: {source}")

        if target not in self.nodes:
            raise ValueError(f"Target node does not exist: {target}")

        if isinstance(edge_type, str):
            edge_type = CodeGraphEdgeType(edge_type)

        metadata_tuple = tuple(
            sorted(
                (metadata or {}).items(),
                key=lambda item: item[0],
            )
        )

        key = (
            source,
            target,
            edge_type,
            metadata_tuple,
        )

        # Return an existing edge without scanning the complete graph.
        if key in self._edge_keys:
            for edge in self._outgoing_edges.get(source, []):
                if (
                    edge.target == target
                    and edge.edge_type == edge_type
                    and edge.metadata == metadata_tuple
                ):
                    return edge

        edge = CodeGraphEdge(
            source=source,
            target=target,
            edge_type=edge_type,
            metadata=metadata_tuple,
        )

        self.edges.append(edge)
        self._edge_keys.add(key)

        self._outgoing_edges.setdefault(source, []).append(edge)
        self._incoming_edges.setdefault(target, []).append(edge)

        return edge
    # --------------------------------------------------------
    # Queries
    # --------------------------------------------------------

    def get_node(
        self,
        node_id: str,
    ) -> CodeGraphNode | None:
        """
        Return a node by ID.
        """

        return self.nodes.get(node_id)

    def get_edges_from(
        self,
        node_id: str,
    ) -> list[CodeGraphEdge]:
        """Return outgoing edges using the adjacency index."""

        return self._outgoing_edges.get(node_id, [])

    def get_edges_to(
        self,
        node_id: str,
    ) -> list[CodeGraphEdge]:
        """Return incoming edges using the adjacency index."""

        return self._incoming_edges.get(node_id, [])

    def get_edges_by_type(
        self,
        edge_type: CodeGraphEdgeType | str,
    ) -> list[CodeGraphEdge]:
        """
        Return all edges of a particular type.
        """

        if isinstance(edge_type, str):
            edge_type = CodeGraphEdgeType(edge_type)

        return [
            edge
            for edge in self.edges
            if edge.edge_type == edge_type
        ]

    # --------------------------------------------------------
    # Statistics
    # --------------------------------------------------------

    def get_statistics(self) -> dict[str, Any]:
        """
        Return graph statistics.
        """

        node_types: dict[str, int] = {}

        for node in self.nodes.values():

            node_types[node.node_type] = (
                node_types.get(node.node_type, 0) + 1
            )

        edge_types: dict[str, int] = {}

        for edge in self.edges:

            edge_type = edge.edge_type.value

            edge_types[edge_type] = (
                edge_types.get(edge_type, 0) + 1
            )

        return {
            "nodes": len(self.nodes),
            "edges": len(self.edges),
            "node_types": node_types,
            "edge_types": edge_types,
        }

    # --------------------------------------------------------
    # Serialization
    # --------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """
        Convert the complete graph to a dictionary.
        """

        return {
            "nodes": [
                node.to_dict()
                for node in self.nodes.values()
            ],
            "edges": [
                edge.to_dict()
                for edge in self.edges
            ],
            "statistics": self.get_statistics(),
        }


# ============================================================
# Builder
# ============================================================


class UnifiedCodeGraphBuilder:
    """
    Builds a UnifiedCodeGraph from the existing Code Guardian
    analysis results.

    The builder is deliberately tolerant of different analyzer
    return formats so that existing analyzers do not need to be
    rewritten.
    """

    def __init__(self) -> None:

        self.graph = UnifiedCodeGraph()

    # --------------------------------------------------------
    # Generic helpers
    # --------------------------------------------------------

    @staticmethod
    def _safe_get(
        obj: Any,
        attribute: str,
        default: Any = None,
    ) -> Any:
        """
        Safely retrieve an attribute from an object.
        """

        if obj is None:
            return default

        if isinstance(obj, dict):
            return obj.get(attribute, default)

        return getattr(
            obj,
            attribute,
            default,
        )

    @staticmethod
    def _iter_items(
        value: Any,
    ):
        """
        Iterate over dictionary-like or iterable objects.
        """

        if value is None:
            return []

        if isinstance(value, dict):
            return value.items()

        try:
            return enumerate(value)
        except TypeError:
            return []

    # --------------------------------------------------------
    # File / function structure
    # --------------------------------------------------------

    def add_file(
        self,
        file_path: str,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """
        Add a repository file node.
        """

        self.graph.add_node(
            node_id=file_path,
            node_type="file",
            name=file_path,
            file=file_path,
            metadata=metadata,
        )

        return file_path

    def add_function(
        self,
        function_id: str,
        file_path: str | None = None,
        function_name: str | None = None,
        line: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """
        Add a function node.
        """

        self.graph.add_node(
            node_id=function_id,
            node_type="function",
            name=function_name or function_id,
            file=file_path,
            line=line,
            function_id=function_id,
            metadata=metadata,
        )

        if file_path:

            self.add_file(file_path)

            self.graph.add_edge(
                file_path,
                function_id,
                CodeGraphEdgeType.CONTAINS,
            )

        return function_id

    # --------------------------------------------------------
    # CFG
    # --------------------------------------------------------

    def add_cfg(
        self,
        function_id: str,
        cfg: Any,
    ) -> None:
        """
        Add CFG nodes and CONTROL_FLOW edges.
        """

        if cfg is None:
            return

        nodes = []

        get_nodes = getattr(
            cfg,
            "get_nodes",
            None,
        )

        if callable(get_nodes):

            nodes = get_nodes()

        elif hasattr(cfg, "nodes"):

            nodes = cfg.nodes

            if isinstance(nodes, dict):
                nodes = nodes.values()

        for cfg_node in nodes:

            node_id = self._safe_get(
                cfg_node,
                "id",
            )

            if node_id is None:
                continue

            graph_node_id = (
                f"{function_id}::cfg::{node_id}"
            )

            line = self._safe_get(
                cfg_node,
                "line",
            )

            node_type = self._safe_get(
                cfg_node,
                "node_type",
                "cfg_node",
            )

            self.graph.add_node(
                node_id=graph_node_id,
                node_type="cfg_node",
                name=str(node_type),
                line=line,
                function_id=function_id,
                metadata={
                    "cfg_node_id": node_id,
                    "cfg_type": node_type,
                },
            )

            self.graph.add_edge(
                function_id,
                graph_node_id,
                CodeGraphEdgeType.HAS_CFG_NODE,
            )

        # CFG edges
        for cfg_node in nodes:

            source_id = self._safe_get(
                cfg_node,
                "id",
            )

            if source_id is None:
                continue

            graph_source = (
                f"{function_id}::cfg::{source_id}"
            )

            successors = []

            get_successors = getattr(
                cfg,
                "get_successors",
                None,
            )

            if callable(get_successors):

                successors = get_successors(
                    source_id
                )

            elif hasattr(cfg_node, "successors"):

                successors = (
                    getattr(
                        cfg_node,
                        "successors",
                        [],
                    )
                    or []
                )

            for target_id in successors:

                graph_target = (
                    f"{function_id}::cfg::{target_id}"
                )

                if graph_target not in self.graph.nodes:
                    continue

                self.graph.add_edge(
                    graph_source,
                    graph_target,
                    CodeGraphEdgeType.CONTROL_FLOW,
                )

    # --------------------------------------------------------
    # Call Graph
    # --------------------------------------------------------

    def add_call_graph(
        self,
        call_graph: Any,
    ) -> None:
        """
        Add CALLS edges.
        """

        if call_graph is None:
            return

        get_edges = getattr(
            call_graph,
            "get_edges",
            None,
        )

        if callable(get_edges):

            for caller, callee in get_edges():

                self._ensure_function_node(caller)
                self._ensure_function_node(callee)

                self.graph.add_edge(
                    caller,
                    callee,
                    CodeGraphEdgeType.CALLS,
                )

            return

        calls = self._safe_get(
            call_graph,
            "calls",
            {},
        )

        if isinstance(calls, dict):

            for caller, callees in calls.items():

                self._ensure_function_node(caller)

                for callee in callees:

                    self._ensure_function_node(callee)

                    self.graph.add_edge(
                        caller,
                        callee,
                        CodeGraphEdgeType.CALLS,
                    )

    # --------------------------------------------------------
    # Dependency Graph
    # --------------------------------------------------------

    def add_dependency_graph(
        self,
        dependency_graph: Any,
    ) -> None:
        """
        Add dependency nodes and DEPENDS_ON edges.

        Supports the existing DependencyGraph implementation.
        """

        if dependency_graph is None:
            return

        nodes = self._safe_get(
            dependency_graph,
            "nodes",
            [],
        )

        for node in nodes:

            if isinstance(node, dict):

                node_id = node.get("id")

                if node_id is None:
                    continue

                node_type = node.get(
                    "type",
                    "file",
                )

                metadata = dict(node)

                metadata.pop("id", None)
                metadata.pop("type", None)

                self.graph.add_node(
                    node_id=node_id,
                    node_type=node_type,
                    name=node.get(
                        "name",
                        node_id,
                    ),
                    file=node.get(
                        "file",
                    ),
                    line=node.get(
                        "line",
                    ),
                    metadata=metadata,
                )

        edges = self._safe_get(
            dependency_graph,
            "edges",
            [],
        )

        for edge in edges:

            if isinstance(edge, dict):

                source = edge.get("source")
                target = edge.get("target")
                edge_type = edge.get(
                    "type",
                    "import",
                )

            else:

                continue

            if source is None or target is None:
                continue

            self._ensure_generic_node(source)
            self._ensure_generic_node(target)

            self.graph.add_edge(
                source,
                target,
                CodeGraphEdgeType.DEPENDS_ON,
                metadata={
                    "original_type": edge_type,
                },
            )

    # --------------------------------------------------------
    # Data Flow
    # --------------------------------------------------------

    def add_data_flow(
        self,
        function_id: str,
        data_flow: Any,
    ) -> None:
        """
        Add definitions and uses discovered by DataFlowAnalyzer.
        """

        if data_flow is None:
            return

        self._ensure_function_node(function_id)

        definitions = self._safe_get(
            data_flow,
            "definitions",
            [],
        )

        for index, definition in enumerate(
            definitions
        ):

            name = self._safe_get(
                definition,
                "name",
                f"variable_{index}",
            )

            line = self._safe_get(
                definition,
                "line",
            )

            definition_id = self._safe_get(
                definition,
                "id",
            )

            if definition_id is None:

                definition_id = (
                    f"D{index}"
                )

            node_id = (
                f"{function_id}::definition::{definition_id}"
            )

            self.graph.add_node(
                node_id=node_id,
                node_type="definition",
                name=name,
                line=line,
                function_id=function_id,
                metadata={
                    "definition_id": definition_id,
                    "kind": self._safe_get(
                        definition,
                        "kind",
                    ),
                },
            )

            self.graph.add_edge(
                function_id,
                node_id,
                CodeGraphEdgeType.DEFINES,
            )

        uses = self._safe_get(
            data_flow,
            "uses",
            [],
        )

        for index, use in enumerate(uses):

            name = self._safe_get(
                use,
                "name",
                f"variable_{index}",
            )

            line = self._safe_get(
                use,
                "line",
            )

            use_id = self._safe_get(
                use,
                "id",
            )

            if use_id is None:

                use_id = (
                    f"U{index}"
                )

            node_id = (
                f"{function_id}::use::{use_id}"
            )

            self.graph.add_node(
                node_id=node_id,
                node_type="use",
                name=name,
                line=line,
                function_id=function_id,
                metadata={
                    "use_id": use_id,
                    "context": self._safe_get(
                        use,
                        "context",
                    ),
                },
            )

            self.graph.add_edge(
                function_id,
                node_id,
                CodeGraphEdgeType.USES,
            )

    # --------------------------------------------------------
    # Def-Use
    # --------------------------------------------------------

    def add_def_use(
        self,
        function_id: str,
        def_use_result: Any,
    ) -> None:
        """
        Add DEF_USE relationships.
        """

        if def_use_result is None:
            return

        chains = self._safe_get(
            def_use_result,
            "chains",
            [],
        )

        for chain in chains:

            definition_id = self._safe_get(
                chain,
                "definition_id",
            )

            use_id = self._safe_get(
                chain,
                "use_id",
            )

            if (
                definition_id is None
                or use_id is None
            ):
                continue

            definition_node = (
                f"{function_id}::definition::{definition_id}"
            )

            use_node = (
                f"{function_id}::use::{use_id}"
            )

            if (
                definition_node not in
                self.graph.nodes
            ):
                self.graph.add_node(
                    definition_node,
                    "definition",
                    name=self._safe_get(
                        chain,
                        "variable",
                    ),
                    line=self._safe_get(
                        chain,
                        "definition_line",
                    ),
                    function_id=function_id,
                )

            if (
                use_node not in
                self.graph.nodes
            ):
                self.graph.add_node(
                    use_node,
                    "use",
                    name=self._safe_get(
                        chain,
                        "variable",
                    ),
                    line=self._safe_get(
                        chain,
                        "use_line",
                    ),
                    function_id=function_id,
                )

            self.graph.add_edge(
                definition_node,
                use_node,
                CodeGraphEdgeType.DEF_USE,
                metadata={
                    "variable": self._safe_get(
                        chain,
                        "variable",
                    ),
                    "definition_kind": self._safe_get(
                        chain,
                        "definition_kind",
                    ),
                    "use_context": self._safe_get(
                        chain,
                        "use_context",
                    ),
                },
            )

    
    
    # --------------------------------------------------------
    # Reaching Definitions
    # --------------------------------------------------------
     

    def add_reaching_definitions(
        self,
        function_id: str,
        reaching_definitions: Any,
    ) -> None:
        """
        Add Reaching Definition relationships to the unified graph.

        ReachingDefinitionsResult contains:

            definitions
            gen
            kill
            in_sets
            out_sets

        For the unified graph, the important relationship is:

            Definition
                |
                | REACHING_DEFINITION
                v
            CFG Node

        using the IN set of each CFG node.

        Example:

            x = 10
            print(x)

        becomes:

            D0(x)
              |
              | reaching_definition
              v
            CFG(print(x))
        """

        if reaching_definitions is None:
            return

        self._ensure_function_node(function_id)

        # ----------------------------------------------------
        # Definition references
        #
        # Example:
        #
        # [
        #     DefinitionRef(id="D0", definition=...)
        # ]
        # ----------------------------------------------------

        definitions = self._safe_get(
            reaching_definitions,
            "definitions",
            [],
        )

        definitions_by_id: dict[str, Any] = {}

        for definition_ref in definitions or []:

            definition_id = self._safe_get(
                definition_ref,
                "id",
                None,
            )

            if definition_id is None:
                continue

            definitions_by_id[
                str(definition_id)
            ] = definition_ref

        # ----------------------------------------------------
        # Reaching definitions are represented by IN sets.
        #
        # Example:
        #
        # in_sets = {
        #     0: set(),
        #     1: {"D0"},
        #     2: {"D0"},
        # }
        #
        # This means D0 reaches the beginning of CFG node 1
        # and CFG node 2.
        # ----------------------------------------------------

        in_sets = self._safe_get(
            reaching_definitions,
            "in_sets",
            {},
        )

        if not isinstance(in_sets, dict):
            return

        for cfg_node_id, reaching_ids in in_sets.items():

            if not reaching_ids:
                continue

            graph_cfg_node_id = (
                f"{function_id}::cfg::{cfg_node_id}"
            )

            # The CFG node should normally already exist because
            # add_cfg() runs before this method.
            #
            # If it doesn't exist, skip it instead of creating
            # an incomplete CFG node.

            if graph_cfg_node_id not in self.graph.nodes:
                continue

            for definition_id in reaching_ids:

                definition_id = str(
                    definition_id
                )

                definition_ref = (
                    definitions_by_id.get(
                        definition_id
                    )
                )

                # Ignore stale/invalid definition IDs.
                if definition_ref is None:
                    continue

                definition = self._safe_get(
                    definition_ref,
                    "definition",
                    None,
                )

                definition_name = self._safe_get(
                    definition,
                    "name",
                    definition_id,
                )

                definition_line = self._safe_get(
                    definition,
                    "line",
                    None,
                )

                definition_kind = self._safe_get(
                    definition,
                    "kind",
                    None,
                )

                definition_node_id = (
                    f"{function_id}"
                    f"::definition::{definition_id}"
                )

                # ------------------------------------------------
                # The definition node should already have been
                # created by add_data_flow().
                #
                # But create it safely if it doesn't exist.
                # ------------------------------------------------

                if (
                    definition_node_id
                    not in self.graph.nodes
                ):

                    self.graph.add_node(
                        node_id=definition_node_id,
                        node_type="definition",
                        name=definition_name,
                        line=definition_line,
                        function_id=function_id,
                        metadata={
                            "definition_id": definition_id,
                            "kind": definition_kind,
                        },
                    )

                    self.graph.add_edge(
                        function_id,
                        definition_node_id,
                        CodeGraphEdgeType.DEFINES,
                    )

                # ------------------------------------------------
                # Definition -> CFG node
                #
                # This is the actual reaching-definition
                # relationship.
                # ------------------------------------------------

                self.graph.add_edge(
                    definition_node_id,
                    graph_cfg_node_id,
                    CodeGraphEdgeType.REACHING_DEFINITION,
                    metadata={
                        "definition_id": definition_id,
                        "variable": definition_name,
                        "definition_line": definition_line,
                        "cfg_node_id": cfg_node_id,
                        "position": "in",
                    },
                )
                    
                    
                    
    # --------------------------------------------------------
    # Use-Before-Definition
    # --------------------------------------------------------
            # --------------------------------------------------------
    # Use-Before-Definition
    # --------------------------------------------------------

    def add_use_before_definition(
        self,
        function_id: str,
        result: Any,
    ) -> None:
        """
        Add USE_BEFORE_DEFINITION relationships.

        A UBD finding corresponds to an actual variable use.

        The graph therefore reuses the existing use node whenever
        possible instead of creating an unrelated duplicate node.

        Example:

            print(x)

        when x has not been defined:

            Function
                |
                +---- uses ----> U0(x)
                                |
                                |
                       use_before_definition
                                |
                                v
                         UBD finding

        The existing U0 node remains the canonical representation
        of the source-level use.
        """

        if result is None:
            return

        self._ensure_function_node(function_id)

        findings = self._safe_get(
            result,
            "findings",
            [],
        )

        if isinstance(findings, dict):
            findings = findings.values()

        try:
            findings = list(
                findings or []
            )
        except TypeError:
            findings = []

        for index, finding in enumerate(findings):

            # ------------------------------------------------
            # Extract finding information
            # ------------------------------------------------

            variable = self._safe_get(
                finding,
                "variable",
                None,
            )

            if variable is None:
                variable = self._safe_get(
                    finding,
                    "name",
                    f"unknown_{index}",
                )

            line = self._safe_get(
                finding,
                "line",
                None,
            )

            use_id = self._safe_get(
                finding,
                "use_id",
                None,
            )

            reason = self._safe_get(
                finding,
                "reason",
                "Variable is used before a definition reaches this point.",
            )

            cfg_node_ids = self._safe_get(
                finding,
                "cfg_node_ids",
                (),
            )

            # ------------------------------------------------
            # Prefer the actual existing use node.
            #
            # Example:
            #
            #     U0
            #
            # becomes:
            #
            #     U0 --USE_BEFORE_DEFINITION--> UBD finding
            # ------------------------------------------------

            use_node_id = None

            if use_id is not None:

                candidate_use_node = (
                    f"{function_id}::use::{use_id}"
                )

                if candidate_use_node in self.graph.nodes:

                    use_node_id = candidate_use_node

            # ------------------------------------------------
            # If the use node does not already exist, create
            # it safely.
            #
            # This makes the graph builder tolerant when UBD
            # is used independently of add_data_flow().
            # ------------------------------------------------

            if use_node_id is None:

                if use_id is not None:

                    use_node_id = (
                        f"{function_id}"
                        f"::use::{use_id}"
                    )

                else:

                    use_node_id = (
                        f"{function_id}"
                        f"::use::UBD{index}"
                    )

                if use_node_id not in self.graph.nodes:

                    self.graph.add_node(
                        node_id=use_node_id,
                        node_type="use",
                        name=variable,
                        line=line,
                        function_id=function_id,
                        metadata={
                            "use_id": use_id,
                            "ubd_related": True,
                        },
                    )

                    self.graph.add_edge(
                        function_id,
                        use_node_id,
                        CodeGraphEdgeType.USES,
                    )

            # ------------------------------------------------
            # Create a dedicated UBD finding node.
            #
            # This node represents the analysis finding,
            # while the `use` node represents the source-level
            # variable use.
            # ------------------------------------------------

            finding_node_id = (
                f"{function_id}"
                f"::use_before_definition::{use_id or index}"
            )

            self.graph.add_node(
                node_id=finding_node_id,
                node_type="use_before_definition",
                name=variable,
                line=line,
                function_id=function_id,
                metadata={
                    "use_id": use_id,
                    "variable": variable,
                    "reason": reason,
                    "cfg_node_ids": list(
                        cfg_node_ids or []
                    ),
                },
            )

            # ------------------------------------------------
            # Connect the actual use to the UBD finding.
            # ------------------------------------------------

            self.graph.add_edge(
                use_node_id,
                finding_node_id,
                CodeGraphEdgeType.USE_BEFORE_DEFINITION,
                metadata={
                    "use_id": use_id,
                    "variable": variable,
                    "line": line,
                    "reason": reason,
                },
            )
            
    # --------------------------------------------------------
    # Dead Definitions
    # --------------------------------------------------------
            # --------------------------------------------------------
    # Dead Definitions
    # --------------------------------------------------------

    def add_dead_definitions(
        self,
        function_id: str,
        result: Any,
    ) -> None:
        """
        Add DEAD_DEFINITION relationships.

        A dead-definition finding refers to a definition that
        does not reach any valid use.

        The existing definition node is reused whenever possible.

        Example:

            x = 10
            y = 20
            print(x)

        Graph:

            D0(x) ── DEF_USE ──► U0(x)

            D1(y)
              │
              │ DEAD_DEFINITION
              ▼
            DeadFinding(y)

        This keeps the definition node as the canonical
        representation of the source-level definition.
        """

        if result is None:
            return

        self._ensure_function_node(function_id)

        # ----------------------------------------------------
        # DeadDefinitionResult normally exposes:
        #
        #     findings
        #
        # Be tolerant of older representations.
        # ----------------------------------------------------

        findings = self._safe_get(
            result,
            "findings",
            None,
        )

        if findings is None:

            findings = self._safe_get(
                result,
                "dead_definitions",
                None,
            )

        if findings is None:

            findings = self._safe_get(
                result,
                "definitions",
                [],
            )

        if isinstance(findings, dict):
            findings = findings.values()

        try:
            findings = list(
                findings or []
            )
        except TypeError:
            findings = []

        # ----------------------------------------------------
        # Process every dead definition.
        # ----------------------------------------------------

        for index, finding in enumerate(findings):

            definition_id = self._safe_get(
                finding,
                "definition_id",
                None,
            )

            if definition_id is None:

                definition_id = self._safe_get(
                    finding,
                    "id",
                    None,
                )

            if definition_id is None:

                definition_id = f"dead_{index}"

            variable = self._safe_get(
                finding,
                "variable",
                None,
            )

            if variable is None:

                variable = self._safe_get(
                    finding,
                    "name",
                    definition_id,
                )

            line = self._safe_get(
                finding,
                "line",
                None,
            )

            definition_kind = self._safe_get(
                finding,
                "definition_kind",
                None,
            )

            reason = self._safe_get(
                finding,
                "reason",
                "Definition is never used by any valid data-flow use.",
            )

            cfg_node_ids = self._safe_get(
                finding,
                "cfg_node_ids",
                (),
            )

            # ------------------------------------------------
            # Existing canonical definition node.
            # ------------------------------------------------

            definition_node_id = (
                f"{function_id}"
                f"::definition::{definition_id}"
            )

            # ------------------------------------------------
            # If the Data Flow stage did not create the
            # definition node, create it here.
            # ------------------------------------------------

            if definition_node_id not in self.graph.nodes:

                self.graph.add_node(
                    node_id=definition_node_id,
                    node_type="definition",
                    name=variable,
                    line=line,
                    function_id=function_id,
                    metadata={
                        "definition_id": definition_id,
                        "kind": definition_kind,
                    },
                )

                self.graph.add_edge(
                    function_id,
                    definition_node_id,
                    CodeGraphEdgeType.DEFINES,
                )

            # ------------------------------------------------
            # Create analysis finding node.
            #
            # The definition node represents the source code.
            # This node represents the static-analysis finding.
            # ------------------------------------------------

            finding_node_id = (
                f"{function_id}"
                f"::dead_definition::{definition_id}"
            )

            self.graph.add_node(
                node_id=finding_node_id,
                node_type="dead_definition",
                name=variable,
                line=line,
                function_id=function_id,
                metadata={
                    "definition_id": definition_id,
                    "variable": variable,
                    "definition_kind": definition_kind,
                    "reason": reason,
                    "cfg_node_ids": list(
                        cfg_node_ids or []
                    ),
                },
            )

            # ------------------------------------------------
            # Definition → Dead Definition finding
            # ------------------------------------------------

            self.graph.add_edge(
                definition_node_id,
                finding_node_id,
                CodeGraphEdgeType.DEAD_DEFINITION,
                metadata={
                    "definition_id": definition_id,
                    "variable": variable,
                    "line": line,
                    "reason": reason,
                },
            )
            
            
    # --------------------------------------------------------
    # Taint
    # --------------------------------------------------------
    def add_taint_edges(
        self,
        taint_results: Any,
    ) -> None:
        """
        Add TAINT_FLOW relationships from taint-analysis findings.

        TaintAnalysisResult exposes findings containing:

            source_name
            source_line
            sink_name
            sink_line
            variable
            definition_id
            use_id
            path
            reason

        The graph represents the detected flow as:

            taint_source -> taint_sink

        with the security context stored in edge metadata.
        """

        if taint_results is None:
            return

        # --------------------------------------------------------
        # Normalize result collection
        # --------------------------------------------------------

        if isinstance(taint_results, dict):

            iterable = taint_results.values()

        elif isinstance(
            taint_results,
            (list, tuple),
        ):

            iterable = taint_results

        else:

            iterable = [taint_results]

        # --------------------------------------------------------
        # Process each taint result
        # --------------------------------------------------------

        for result in iterable:

            if result is None:
                continue

            findings = self._safe_get(
                result,
                "findings",
                [],
            )

            if isinstance(
                findings,
                dict,
            ):

                findings = findings.values()

            try:

                findings = list(
                    findings or []
                )

            except TypeError:

                findings = []

            # ----------------------------------------------------
            # Convert each taint finding into graph relationships
            # ----------------------------------------------------

            for index, finding in enumerate(
                findings
            ):

                source_name = self._safe_get(
                    finding,
                    "source_name",
                    "unknown_source",
                )

                source_line = self._safe_get(
                    finding,
                    "source_line",
                    None,
                )

                sink_name = self._safe_get(
                    finding,
                    "sink_name",
                    "unknown_sink",
                )

                sink_line = self._safe_get(
                    finding,
                    "sink_line",
                    None,
                )

                variable = self._safe_get(
                    finding,
                    "variable",
                    "",
                )

                definition_id = self._safe_get(
                    finding,
                    "definition_id",
                    "",
                )

                use_id = self._safe_get(
                    finding,
                    "use_id",
                    "",
                )

                path = self._safe_get(
                    finding,
                    "path",
                    (),
                )

                reason = self._safe_get(
                    finding,
                    "reason",
                    None,
                )

                # ------------------------------------------------
                # Stable source node ID
                # ------------------------------------------------

                source_node_id = (
                    "taint::source::"
                    f"{source_name}::"
                    f"{source_line}"
                )

                # ------------------------------------------------
                # Stable sink node ID
                # ------------------------------------------------

                sink_node_id = (
                    "taint::sink::"
                    f"{sink_name}::"
                    f"{sink_line}"
                )

                # ------------------------------------------------
                # Source node
                # ------------------------------------------------

                self.graph.add_node(
                    node_id=source_node_id,
                    node_type="taint_source",
                    name=source_name,
                    line=source_line,
                    metadata={
                        "taint": True,
                        "kind": "source",
                    },
                )

                # ------------------------------------------------
                # Sink node
                # ------------------------------------------------

                self.graph.add_node(
                    node_id=sink_node_id,
                    node_type="taint_sink",
                    name=sink_name,
                    line=sink_line,
                    metadata={
                        "taint": True,
                        "kind": "sink",
                    },
                )

                # ------------------------------------------------
                # Taint flow edge
                # ------------------------------------------------

                metadata = {
                    "variable": variable,
                    "definition_id": definition_id,
                    "use_id": use_id,
                    # tuple (not list): metadata becomes part of a set key
                    "path": tuple(path)
                    if path
                    else (),
                }

                if reason:
                    metadata["reason"] = reason

                self.graph.add_edge(
                    source_node_id,
                    sink_node_id,
                    CodeGraphEdgeType.TAINT_FLOW,
                    metadata=metadata,
                )

    # --------------------------------------------------------
    # Full Build
    # --------------------------------------------------------

    def build(
        self,
        *,
        control_flow_graphs: dict[str, Any] | None = None,
        call_graph: Any = None,
        dependency_graph: Any = None,
        data_flow_results: dict[str, Any] | None = None,
        reaching_definition_results: dict[str, Any] | None = None,
        def_use_results: dict[str, Any] | None = None,
        taint_results: Any = None,
    ) -> UnifiedCodeGraph:
        """
        Build the unified graph.

        Parameters are intentionally optional so individual
        analysis stages can be introduced incrementally.
        """

        self.graph = UnifiedCodeGraph()

        control_flow_graphs = (
            control_flow_graphs or {}
        )

        data_flow_results = (
            data_flow_results or {}
        )
        reaching_definition_results = (
            reaching_definition_results or {}
        )

        def_use_results = (
            def_use_results or {}
        )

        # ----------------------------------------------------
        # Functions + CFG + data flow
        # ----------------------------------------------------

        for function_id, cfg in (
            control_flow_graphs.items()
        ):

            function_name = (
                self._safe_get(
                    cfg,
                    "function_name",
                    function_id,
                )
            )

            self.add_function(
                function_id=function_id,
                function_name=function_name,
            )

            self.add_cfg(
                function_id,
                cfg,
            )
            if function_id in data_flow_results:

                self.add_data_flow(
                    function_id,
                    data_flow_results[
                        function_id
                    ],
                )

            if function_id in reaching_definition_results:

                self.add_reaching_definitions(
                    function_id,
                    reaching_definition_results[
                        function_id
                    ],
                )

            if function_id in def_use_results:

                self.add_def_use(
                    function_id,
                    def_use_results[
                        function_id
                    ],
                )
        # ----------------------------------------------------
        # Call graph
        # ----------------------------------------------------

        self.add_call_graph(
            call_graph
        )

        # ----------------------------------------------------
        # Dependency graph
        # ----------------------------------------------------

        self.add_dependency_graph(
            dependency_graph
        )

        # ----------------------------------------------------
        # Taint
        # ----------------------------------------------------

        self.add_taint_edges(
            taint_results
        )

        return self.graph

    # --------------------------------------------------------
    # Internal helpers
    # --------------------------------------------------------

    def _ensure_function_node(
        self,
        function_id: str,
    ) -> None:
        """
        Create a function node if it doesn't exist.
        """

        if function_id not in self.graph.nodes:

            self.graph.add_node(
                node_id=function_id,
                node_type="function",
                name=function_id,
                function_id=function_id,
            )

    def _ensure_generic_node(
        self,
        node_id: str,
    ) -> None:
        """
        Create a generic node if it doesn't exist.
        """

        if node_id not in self.graph.nodes:

            self.graph.add_node(
                node_id=node_id,
                node_type="unknown",
                name=node_id,
            )