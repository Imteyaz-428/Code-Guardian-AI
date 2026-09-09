class GraphAnalyzer:

    def __init__(self, graph):
        self.nodes, self.edges = self._extract_nodes_and_edges(graph)

    def _extract_nodes_and_edges(self, graph):
        """
        Normalize any supported graph representation into (nodes, edges).

        Supported formats:
            1. A DependencyGraph object (has .nodes / .edges attributes)
            2. A dict: {"nodes": [...], "edges": [...]}
            3. A (nodes, edges) tuple or list

        Unrecognized input safely falls back to two empty lists rather
        than raising, since risk scoring should still work for a file
        with no known dependency graph.
        """

        if hasattr(graph, "nodes") and hasattr(graph, "edges"):
            return graph.nodes, graph.edges

        if isinstance(graph, dict):
            return graph.get("nodes", []), graph.get("edges", [])

        if isinstance(graph, (tuple, list)) and len(graph) == 2:
            first, second = graph

            if self._looks_like_nodes(first) and self._looks_like_edges(second):
                return first, second

        return [], []

    
    # GRAPH FORMAT HELPERS
    

    def _looks_like_nodes(self, value):
        """
        Check whether value looks like a collection of nodes.
        """

        if isinstance(value, dict):
            return True

        if isinstance(value, list):

            if len(value) == 0:
                return True

            return all(
                isinstance(item, dict)
                for item in value
            )

        return False

    def _looks_like_edges(self, value):
        """
        Check whether value looks like a collection of edges.
        """

        if isinstance(value, dict):
            return True

        if isinstance(value, list):

            if len(value) == 0:
                return True

            return all(
                isinstance(item, dict)
                for item in value
            )

        return False

    
    # NODE HANDLING
    

    def get_file_nodes(self):
        """
        Return only file nodes.

        Supported format:

        [
            {
                "id": "main.py",
                "type": "file",
                "path": "main.py"
            }
        ]

        Also supports older formats.
        """

        file_nodes = []

       
        # Dictionary nodes
       

        if isinstance(self.nodes, dict):

            for node_id, node_data in self.nodes.items():

                if isinstance(node_data, dict):

                    node_type = node_data.get("type")

                    if node_type == "file":

                        node = {
                            "id": node_id,
                            **node_data
                        }

                        file_nodes.append(node)

                elif node_data == "file":

                    file_nodes.append({
                        "id": node_id,
                        "type": "file"
                    })

       
        # List nodes
       

        elif isinstance(self.nodes, list):

            for node in self.nodes:

                if not isinstance(node, dict):
                    continue

                if node.get("type") == "file":

                    file_nodes.append(node)

        return file_nodes

    
    # EDGE HANDLING
    

    def get_import_edges(self):
        """
        Return only import edges.
        """

        import_edges = []

        if not isinstance(self.edges, list):
            return import_edges

        for edge in self.edges:

            if not isinstance(edge, dict):
                continue

            source = edge.get("source")
            target = edge.get("target")

            if not source or not target:
                continue

            edge_type = edge.get("type", "import")

            if edge_type == "import":

                import_edges.append(edge)

        return import_edges

    
    # ADJACENCY LIST
    

    def build_adjacency_list(self):
        """
        Build dependency adjacency list.

        Example:

        {
            "main.py": [
                "utils.py",
                "services/user.py"
            ],

            "utils.py": [],

            "services/user.py": []
        }
        """

        adjacency = {}

       
        # Add all file nodes first
       

        file_nodes = self.get_file_nodes()

        for node in file_nodes:

            file_id = node.get("id")

            if file_id:

                adjacency[file_id] = []

       
        # Add import edges
       

        for edge in self.get_import_edges():

            source = edge.get("source")
            target = edge.get("target")

            if not source or not target:
                continue

            if source not in adjacency:

                adjacency[source] = []

            if target not in adjacency[source]:

                adjacency[source].append(target)

        return adjacency

    
    # DEPENDENCIES
    

    def get_dependencies(self, file_path):
        """
        Get files directly imported by file_path.
        """

        adjacency = self.build_adjacency_list()

        return adjacency.get(file_path, [])

    
    # DEPENDENTS
    def get_dependents(self, file_path):
        """
        Get files that directly depend on file_path.
        """

        adjacency = self.build_adjacency_list()

        dependents = []

        for source, targets in adjacency.items():

            if file_path in targets:

                dependents.append(source)

        return dependents

    
    # COUNTS
    

    def get_dependency_count(self, file_path):
        """
        Number of files directly imported by file_path.
        """

        return len(
            self.get_dependencies(file_path)
        )

    def get_dependent_count(self, file_path):
        """
        Number of files directly depending on file_path.
        """

        return len(
            self.get_dependents(file_path)
        )

    
    # CIRCULAR DEPENDENCIES
    

    def find_circular_dependencies(self):
        """
        Detect circular dependencies.

        Example:

            A -> B
            B -> C
            C -> A

        Result:

            A -> B -> C -> A
        """

        graph = self.build_adjacency_list()

        visited = set()
        current_path = []
        cycles = []

        def dfs(node):

            # Node already exists in current DFS path

            if node in current_path:

                cycle_start = current_path.index(node)

                cycle = (
                    current_path[cycle_start:]
                    + [node]
                )

                if cycle not in cycles:

                    cycles.append(cycle)

                return

            # Already completely explored

            if node in visited:

                return

            current_path.append(node)

            # Explore neighbors

            for neighbor in graph.get(node, []):

                dfs(neighbor)

            current_path.pop()

            visited.add(node)

       
        # Start DFS from every node
       

        for node in graph:

            if node not in visited:

                dfs(node)

        return cycles

    
    # STATISTICS
    

    def get_statistics(self):
        """
        Return graph statistics.
        """

        files = self.get_file_nodes()

        imports = self.get_import_edges()

        cycles = self.find_circular_dependencies()

        return {
            "total_files": len(files),
            "total_dependencies": len(imports),
            "circular_dependencies": len(cycles)
        }