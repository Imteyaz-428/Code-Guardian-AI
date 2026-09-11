from __future__ import annotations

import ast


class CFGNode:
    """
    Represents a single node in a control flow graph.
    """

    def __init__(
        self,
        node_id: int,
        node_type: str,
        label: str,
        line: int | None = None,
    ):
        self.id = node_id
        self.type = node_type
        self.label = label
        self.line = line

    def to_dict(self):
        return {
            "id": self.id,
            "type": self.type,
            "label": self.label,
            "line": self.line,
        }


class ControlFlowGraph:
    """
    Represents the control flow graph of a function.
    """

    def __init__(self, function_name: str):
        self.function_name = function_name

        self.nodes: dict[int, CFGNode] = {}

        # source node -> destination nodes
        self.edges: dict[int, set[int]] = {}

        self._next_node_id = 0

    def add_node(
        self,
        node_type: str,
        label: str,
        line: int | None = None,
    ) -> int:
        """
        Add a node and return its ID.
        """

        node_id = self._next_node_id
        self._next_node_id += 1

        self.nodes[node_id] = CFGNode(
            node_id=node_id,
            node_type=node_type,
            label=label,
            line=line,
        )

        self.edges[node_id] = set()

        return node_id

    def add_edge(self, source: int, destination: int):
        """
        Add a directed control-flow edge.
        """

        if source not in self.nodes:
            raise ValueError(f"Unknown source node: {source}")

        if destination not in self.nodes:
            raise ValueError(f"Unknown destination node: {destination}")

        self.edges[source].add(destination)

    def get_successors(self, node_id: int) -> list[int]:
        """
        Return nodes that can execute after this node.
        """

        return sorted(self.edges.get(node_id, set()))

    def get_predecessors(self, node_id: int) -> list[int]:
        """
        Return nodes that can execute before this node.
        """

        predecessors = []

        for source, destinations in self.edges.items():
            if node_id in destinations:
                predecessors.append(source)

        return sorted(predecessors)

    def get_nodes(self) -> list[CFGNode]:
        """
        Return all CFG nodes.
        """

        return [
            self.nodes[node_id]
            for node_id in sorted(self.nodes)
        ]

    def get_edges(self) -> list[tuple[int, int]]:
        """
        Return all CFG edges.
        """

        edges = []

        for source, destinations in self.edges.items():
            for destination in destinations:
                edges.append((source, destination))

        return sorted(edges)

    def get_statistics(self):
        """
        Return basic CFG statistics.
        """

        return {
            "function": self.function_name,
            "nodes": len(self.nodes),
            "edges": sum(len(destinations) for destinations in self.edges.values()),
        }
        
        
class CFGAnalyzer:
    """
    Builds a control flow graph from a Python function AST.

    Supports:
    - sequential statements
    - if / elif / else
    - for loops
    - while loops
    - break
    - continue
    - nested loops
    - return
    - try / except / else / finally
    """

    def __init__(self):
        self.graph = None

        # Stack of active loops.
        #
        # Each entry contains:
        #   continue_target -> loop condition node
        #   break_nodes     -> break statements belonging to this loop
        self.loop_stack = []

    def analyze(
        self,
        function_node: ast.FunctionDef | ast.AsyncFunctionDef,
    ) -> ControlFlowGraph:
        """
        Build a CFG for a single function.
        """

        self.graph = ControlFlowGraph(function_node.name)
        self.loop_stack = []

        start = self.graph.add_node(
            node_type="entry",
            label="ENTRY",
            line=function_node.lineno,
        )

        end = self.graph.add_node(
            node_type="exit",
            label="EXIT",
            line=None,
        )

        previous_nodes = {start}

        previous_nodes = self._build_statements(
            function_node.body,
            previous_nodes,
            end,
        )

        # Connect any remaining executable paths to EXIT.
        for node_id in previous_nodes:
            self.graph.add_edge(node_id, end)

        return self.graph

    def _build_statements(
        self,
        statements,
        previous_nodes,
        exit_node,
    ):
        """
        Build CFG nodes for a sequence of statements.
        """

        current_nodes = set(previous_nodes)

        for statement in statements:
            current_nodes = self._build_statement(
                statement,
                current_nodes,
                exit_node,
            )

        return current_nodes

    def _build_statement(
        self,
        statement,
        previous_nodes,
        exit_node,
    ):
        """
        Build CFG structure for one statement.
        """

        # ---------------------------------------------------------
        # IF / ELIF / ELSE
        # ---------------------------------------------------------

        if isinstance(statement, ast.If):
            return self._build_if(
                statement,
                previous_nodes,
                exit_node,
            )

        # ---------------------------------------------------------
        # LOOPS
        # ---------------------------------------------------------

        if isinstance(statement, (ast.For, ast.While)):
            return self._build_loop(
                statement,
                previous_nodes,
                exit_node,
            )

        # ---------------------------------------------------------
        # TRY / EXCEPT
        # ---------------------------------------------------------

        if isinstance(statement, ast.Try):
            return self._build_try(
                statement,
                previous_nodes,
                exit_node,
            )

        # ---------------------------------------------------------
        # RETURN
        # ---------------------------------------------------------

        if isinstance(statement, ast.Return):
            node_id = self._add_statement_node(statement)

            self._connect(
                previous_nodes,
                node_id,
            )

            self.graph.add_edge(
                node_id,
                exit_node,
            )

            # Return terminates this control-flow path.
            return set()

        # ---------------------------------------------------------
        # BREAK
        # ---------------------------------------------------------

        if isinstance(statement, ast.Break):
            node_id = self._add_statement_node(statement)

            self._connect(
                previous_nodes,
                node_id,
            )

            # A break outside a loop is invalid Python syntax,
            # but guard against it anyway.
            if self.loop_stack:
                self.loop_stack[-1]["break_nodes"].add(node_id)

            # Break terminates the current path.
            return set()

        # ---------------------------------------------------------
        # CONTINUE
        # ---------------------------------------------------------

        if isinstance(statement, ast.Continue):
            node_id = self._add_statement_node(statement)

            self._connect(
                previous_nodes,
                node_id,
            )

            # Continue must go to the CURRENT loop.
            if self.loop_stack:
                continue_target = self.loop_stack[-1]["continue_target"]

                self.graph.add_edge(
                    node_id,
                    continue_target,
                )

            # Continue terminates the current path.
            return set()

        # ---------------------------------------------------------
        # NORMAL STATEMENT
        # ---------------------------------------------------------

        node_id = self._add_statement_node(statement)

        self._connect(
            previous_nodes,
            node_id,
        )

        return {node_id}

    def _build_if(
        self,
        statement: ast.If,
        previous_nodes,
        exit_node,
    ):
        """
        Build CFG for an if / elif / else structure.
        """

        condition_node = self.graph.add_node(
            node_type="condition",
            label="if",
            line=statement.lineno,
        )

        self._connect(
            previous_nodes,
            condition_node,
        )

        true_end = self._build_statements(
            statement.body,
            {condition_node},
            exit_node,
        )

        false_end = set()

        if statement.orelse:
            false_end = self._build_statements(
                statement.orelse,
                {condition_node},
                exit_node,
            )
        else:
            # No else branch means the condition itself
            # represents the false path.
            false_end.add(condition_node)

        return true_end | false_end

    def _build_loop(
        self,
        statement,
        previous_nodes,
        exit_node,
    ):
        """
        Build CFG for for / while loops.

        Loop structure:

                    ┌──────────────┐
                    │              │
                    ↓              │
                  LOOP ─────→ BODY │
                    │              │
                    │              │
                    └──────────────┘
                    │
                    ↓
                 LOOP EXIT
        """

        loop_node = self.graph.add_node(
            node_type="loop",
            label=(
                "for"
                if isinstance(statement, ast.For)
                else "while"
            ),
            line=statement.lineno,
        )

        self._connect(
            previous_nodes,
            loop_node,
        )

        # Explicit node representing the path after the loop.
        loop_exit = self.graph.add_node(
            node_type="loop_exit",
            label="LOOP_EXIT",
            line=statement.lineno,
        )

        # The false condition exits the loop.
        self.graph.add_edge(
            loop_node,
            loop_exit,
        )

        # Push the current loop context.
        loop_context = {
            "continue_target": loop_node,
            "break_nodes": set(),
        }

        self.loop_stack.append(loop_context)

        body_end = self._build_statements(
            statement.body,
            {loop_node},
            exit_node,
        )

        # Pop this loop before handling its following statements.
        self.loop_stack.pop()

        # Normal body completion goes back to the loop condition.
        for node_id in body_end:
            self.graph.add_edge(
                node_id,
                loop_node,
            )

        # break -> loop exit
        for break_node in loop_context["break_nodes"]:
            self.graph.add_edge(
                break_node,
                loop_exit,
            )

        # Handle loop else.
        #
        # Python loop else executes when the loop finishes
        # normally, but NOT when break is used.
        if statement.orelse:
            return self._build_statements(
                statement.orelse,
                {loop_exit},
                exit_node,
            )

        return {loop_exit}

    def _build_try(
        self,
        statement: ast.Try,
        previous_nodes,
        exit_node,
    ):
        """
        Build CFG for try / except / else / finally.

        Simplified structure:

                    ┌── except ──┐
                    │            │
        previous → TRY → normal → ELSE
                    │
                    └──────────────→ FINALLY
        """

        try_node = self.graph.add_node(
            node_type="try",
            label="try",
            line=statement.lineno,
        )

        self._connect(
            previous_nodes,
            try_node,
        )

        # ---------------------------------------------------------
        # TRY BODY
        # ---------------------------------------------------------

        try_end = self._build_statements(
            statement.body,
            {try_node},
            exit_node,
        )

        # ---------------------------------------------------------
        # EXCEPT HANDLERS
        # ---------------------------------------------------------

        handler_ends = set()

        for handler in statement.handlers:
            handler_node = self.graph.add_node(
                node_type="except",
                label="except",
                line=getattr(handler, "lineno", None),
            )

            # An exception from the try block can enter
            # any matching handler.
            self.graph.add_edge(
                try_node,
                handler_node,
            )

            handler_end = self._build_statements(
                handler.body,
                {handler_node},
                exit_node,
            )

            handler_ends |= handler_end

        # ---------------------------------------------------------
        # TRY ELSE
        # ---------------------------------------------------------

        normal_end = try_end

        if statement.orelse:
            normal_end = self._build_statements(
                statement.orelse,
                try_end,
                exit_node,
            )

        # ---------------------------------------------------------
        # FINALLY
        # ---------------------------------------------------------

        if statement.finalbody:
            finally_node = self.graph.add_node(
                node_type="finally",
                label="finally",
                line=getattr(
                    statement.finalbody[0],
                    "lineno",
                    statement.lineno,
                ),
            )

            for node_id in normal_end | handler_ends:
                self.graph.add_edge(
                    node_id,
                    finally_node,
                )

            finally_end = self._build_statements(
                statement.finalbody,
                {finally_node},
                exit_node,
            )

            return finally_end

        return normal_end | handler_ends

    def _add_statement_node(self, statement):
        """
        Create a CFG node for a normal statement.
        """

        label = type(statement).__name__

        return self.graph.add_node(
            node_type="statement",
            label=label,
            line=getattr(statement, "lineno", None),
        )

    def _connect(self, sources, destination):
        """
        Connect multiple source nodes to one destination.
        """

        for source in sources:
            self.graph.add_edge(
                source,
                destination,
            )