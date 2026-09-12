"""
Data Flow Analysis - Milestone 1

This module identifies:
- Variable definitions
- Variable uses

It is intentionally independent of ProjectAnalyzer/API integration.
The existing AST and CFG implementations are reused rather than modified.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set


@dataclass
class Definition:
    """Represents a variable definition."""

    name: str
    line: int
    kind: str
    cfg_node_ids: List[str] = field(default_factory=list)


@dataclass
class VariableUse:
    """Represents a variable use."""

    name: str
    line: int
    context: str
    cfg_node_ids: List[str] = field(default_factory=list)


@dataclass
class DataFlowResult:
    """Result of first-level data-flow analysis."""

    function_id: str
    definitions: List[Definition] = field(default_factory=list)
    uses: List[VariableUse] = field(default_factory=list)

    @property
    def defined_variables(self) -> Set[str]:
        """Return all variables defined in the function."""
        return {definition.name for definition in self.definitions}

    @property
    def used_variables(self) -> Set[str]:
        """Return all variables used in the function."""
        return {use.name for use in self.uses}


class DataFlowAnalyzer:
    """
    Performs first-level data-flow analysis for a single function.

    Current responsibility:
        AST
         ↓
        Definitions + Uses

    This class does NOT yet perform:
        - Reaching definitions
        - Def-use chains
        - Use-before-definition detection
        - Interprocedural analysis
    """

    def analyze(
        self,
        function_node: ast.FunctionDef | ast.AsyncFunctionDef,
        function_id: str,
        cfg_node_map: Optional[Dict[int, List[str]]] = None,
    ) -> DataFlowResult:
        """
        Analyze definitions and variable uses inside one function.

        Args:
            function_node:
                AST node representing the function.

            function_id:
                Stable Code Guardian function ID.

            cfg_node_map:
                Optional mapping:

                    source_line -> CFG node IDs

                This allows data-flow facts to be associated with
                the existing CFG without modifying the CFG implementation.

        Returns:
            DataFlowResult
        """

        result = DataFlowResult(function_id=function_id)

        cfg_node_map = cfg_node_map or {}

        # Function parameters are definitions.
        self._collect_parameters(
            function_node,
            result,
            cfg_node_map,
        )

        # Analyze the function body.
        for statement in function_node.body:
            self._visit_statement(
                statement,
                result,
                cfg_node_map,
            )

        return result

   
    # Parameters
   

    def _collect_parameters(
        self,
        function_node: ast.FunctionDef | ast.AsyncFunctionDef,
        result: DataFlowResult,
        cfg_node_map: Dict[int, List[str]],
    ) -> None:
        """Collect function parameters as definitions."""

        arguments = function_node.args

        all_args = (
            list(arguments.posonlyargs)
            + list(arguments.args)
            + list(arguments.kwonlyargs)
        )

        if arguments.vararg:
            all_args.append(arguments.vararg)

        if arguments.kwarg:
            all_args.append(arguments.kwarg)

        for argument in all_args:
            result.definitions.append(
                Definition(
                    name=argument.arg,
                    line=getattr(argument, "lineno", function_node.lineno),
                    kind="parameter",
                    cfg_node_ids=self._cfg_nodes_for_line(
                        getattr(argument, "lineno", function_node.lineno),
                        cfg_node_map,
                    ),
                )
            )

   
    # Statement handling
   

    def _visit_statement(
        self,
        node: ast.stmt,
        result: DataFlowResult,
        cfg_node_map: Dict[int, List[str]],
    ) -> None:
        """Visit one statement."""

        if isinstance(node, ast.Assign):
            self._visit_expression(
                node.value,
                result,
                cfg_node_map,
            )

            for target in node.targets:
                self._collect_target_definitions(
                    target,
                    result,
                    cfg_node_map,
                    kind="assignment",
                )

            return

        if isinstance(node, ast.AnnAssign):
            if node.value:
                self._visit_expression(
                    node.value,
                    result,
                    cfg_node_map,
                )

            self._collect_target_definitions(
                node.target,
                result,
                cfg_node_map,
                kind="assignment",
            )

            return

        if isinstance(node, ast.AugAssign):
            # x += 1 means:
            #
            # x → use
            # x → definition
            self._visit_expression(
                node.target,
                result,
                cfg_node_map,
                target_as_use=True,
            )

            self._visit_expression(
                node.value,
                result,
                cfg_node_map,
            )

            self._collect_target_definitions(
                node.target,
                result,
                cfg_node_map,
                kind="augmented_assignment",
            )

            return

        if isinstance(node, ast.For):
            # The iterable is read before the loop target is defined.
            self._visit_expression(
                node.iter,
                result,
                cfg_node_map,
            )

            self._collect_target_definitions(
                node.target,
                result,
                cfg_node_map,
                kind="loop_target",
            )

            for statement in node.body:
                self._visit_statement(
                    statement,
                    result,
                    cfg_node_map,
                )

            for statement in node.orelse:
                self._visit_statement(
                    statement,
                    result,
                    cfg_node_map,
                )

            return

        if isinstance(node, ast.AsyncFor):
            self._visit_expression(
                node.iter,
                result,
                cfg_node_map,
            )

            self._collect_target_definitions(
                node.target,
                result,
                cfg_node_map,
                kind="loop_target",
            )

            for statement in node.body:
                self._visit_statement(
                    statement,
                    result,
                    cfg_node_map,
                )

            for statement in node.orelse:
                self._visit_statement(
                    statement,
                    result,
                    cfg_node_map,
                )

            return

        if isinstance(node, ast.While):
            self._visit_expression(
                node.test,
                result,
                cfg_node_map,
            )

            for statement in node.body:
                self._visit_statement(
                    statement,
                    result,
                    cfg_node_map,
                )

            for statement in node.orelse:
                self._visit_statement(
                    statement,
                    result,
                    cfg_node_map,
                )

            return

        if isinstance(node, ast.If):
            self._visit_expression(
                node.test,
                result,
                cfg_node_map,
            )

            for statement in node.body:
                self._visit_statement(
                    statement,
                    result,
                    cfg_node_map,
                )

            for statement in node.orelse:
                self._visit_statement(
                    statement,
                    result,
                    cfg_node_map,
                )

            return

        if isinstance(node, (ast.With, ast.AsyncWith)):
            for item in node.items:
                self._visit_expression(
                    item.context_expr,
                    result,
                    cfg_node_map,
                )

                if item.optional_vars:
                    self._collect_target_definitions(
                        item.optional_vars,
                        result,
                        cfg_node_map,
                        kind="with_target",
                    )

            for statement in node.body:
                self._visit_statement(
                    statement,
                    result,
                    cfg_node_map,
                )

            return

        if isinstance(node, ast.Try):
            for statement in node.body:
                self._visit_statement(
                    statement,
                    result,
                    cfg_node_map,
                )

            for handler in node.handlers:
                if handler.type:
                    self._visit_expression(
                        handler.type,
                        result,
                        cfg_node_map,
                    )

                if handler.name:
                    result.definitions.append(
                        Definition(
                            name=handler.name,
                            line=getattr(handler, "lineno", node.lineno),
                            kind="exception_target",
                            cfg_node_ids=self._cfg_nodes_for_line(
                                getattr(handler, "lineno", node.lineno),
                                cfg_node_map,
                            ),
                        )
                    )

                for statement in handler.body:
                    self._visit_statement(
                        statement,
                        result,
                        cfg_node_map,
                    )

            for statement in node.orelse:
                self._visit_statement(
                    statement,
                    result,
                    cfg_node_map,
                )

            for statement in node.finalbody:
                self._visit_statement(
                    statement,
                    result,
                    cfg_node_map,
                )

            return

        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            # Do not include nested function internals in the
            # enclosing function's data-flow analysis.
            return

        if isinstance(node, ast.ClassDef):
            # Do not include class internals in the enclosing
            # function's data-flow analysis.
            return

        # Generic handling for statements not requiring special
        # definition semantics.
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.expr):
                self._visit_expression(
                    child,
                    result,
                    cfg_node_map,
                )
            elif isinstance(child, ast.stmt):
                self._visit_statement(
                    child,
                    result,
                    cfg_node_map,
                )

   
    # Expression handling
   

    def _visit_expression(
        self,
        node: ast.AST,
        result: DataFlowResult,
        cfg_node_map: Dict[int, List[str]],
        target_as_use: bool = False,
    ) -> None:
        """Collect variable uses from an expression."""

        # Function calls need special handling.
        #
        # Example:
        #
        #     print(x)
        #
        # Data Flow should still record BOTH:
        #
        #     print -> call
        #     x     -> load
        #
        # This allows later analyses such as
        # Use-Before-Definition to distinguish a function name
        # from an actual variable use.

        if isinstance(node, ast.Call):

            # Direct function call:
            #
            #     print(x)
            #     calculate(x)
            #     get_values()
            #
            # Record the function name as a use, but mark it
            # as a call target.
            if isinstance(node.func, ast.Name):
                result.uses.append(
                    VariableUse(
                        name=node.func.id,
                        line=getattr(node, "lineno", 0),
                        context="call",
                        cfg_node_ids=self._cfg_nodes_for_line(
                            getattr(node, "lineno", 0),
                            cfg_node_map,
                        ),
                    )
                )

            else:
                # For calls such as:
                #
                #     obj.method(x)
                #
                # obj is a real variable use.
                self._visit_expression(
                    node.func,
                    result,
                    cfg_node_map,
                )

            # Analyze positional arguments.
            for arg in node.args:
                self._visit_expression(
                    arg,
                    result,
                    cfg_node_map,
                )

            # Analyze keyword argument values.
            for keyword in node.keywords:
                self._visit_expression(
                    keyword.value,
                    result,
                    cfg_node_map,
                )

            return

        # Normal variable use.
        if isinstance(node, ast.Name):
            if isinstance(node.ctx, ast.Load) or target_as_use:
                result.uses.append(
                    VariableUse(
                        name=node.id,
                        line=getattr(node, "lineno", 0),
                        context="load",
                        cfg_node_ids=self._cfg_nodes_for_line(
                            getattr(node, "lineno", 0),
                            cfg_node_map,
                        ),
                    )
                )

            return

        # Do not descend into nested lambda scope.
        if isinstance(node, ast.Lambda):
            return

        # Do not analyze nested function internals.
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return

        # Do not analyze nested class internals.
        if isinstance(node, ast.ClassDef):
            return

        # Generic expression handling.
        for child in ast.iter_child_nodes(node):
            self._visit_expression(
                child,
                result,
                cfg_node_map,
                target_as_use=False,
            )
   
    # Target definitions
   

    def _collect_target_definitions(
        self,
        target: ast.AST,
        result: DataFlowResult,
        cfg_node_map: Dict[int, List[str]],
        kind: str,
    ) -> None:
        """Collect definitions from assignment targets."""

        if isinstance(target, ast.Name):
            result.definitions.append(
                Definition(
                    name=target.id,
                    line=getattr(target, "lineno", 0),
                    kind=kind,
                    cfg_node_ids=self._cfg_nodes_for_line(
                        getattr(target, "lineno", 0),
                        cfg_node_map,
                    ),
                )
            )

            return

        if isinstance(target, (ast.Tuple, ast.List)):
            for element in target.elts:
                self._collect_target_definitions(
                    element,
                    result,
                    cfg_node_map,
                    kind,
                )

            return

        if isinstance(target, ast.Starred):
            self._collect_target_definitions(
                target.value,
                result,
                cfg_node_map,
                kind,
            )

            return

        # Attribute and subscript targets do not define a new local
        # variable, but their contained expressions may use variables.
        if isinstance(target, (ast.Attribute, ast.Subscript)):
            self._visit_expression(
                target,
                result,
                cfg_node_map,
            )

   
    # CFG association
   

    @staticmethod
    def _cfg_nodes_for_line(
        line: int,
        cfg_node_map: Dict[int, List[str]],
    ) -> List[str]:
        """Return CFG node IDs associated with a source line."""

        return list(cfg_node_map.get(line, []))