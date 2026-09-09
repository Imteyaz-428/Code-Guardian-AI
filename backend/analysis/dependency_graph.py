class DependencyGraph:

    def __init__(self):
        self.nodes = []
        self.edges = []

    def add_node(self, node_id, node_type="file", metadata=None):
        """
        Add a node to the graph.
        """

        # Don't create duplicate nodes
        for node in self.nodes:
            if node["id"] == node_id:
                return

        node = {
            "id": node_id,
            "type": node_type
        }

        if metadata:
            node.update(metadata)

        self.nodes.append(node)

    def add_edge(self, source, target, edge_type="import"):
        """
        Add an edge between two nodes.
        """

        edge = {
            "source": source,
            "target": target,
            "type": edge_type
        }

        if edge not in self.edges:
            self.edges.append(edge)

    def add_file_node(self, file_path, metadata=None):
        """
        Add a file node.
        """

        node_metadata = {
            "file": file_path,
            "path": file_path
        }

        if metadata:
            node_metadata.update(metadata)

        self.add_node(
            file_path,
            "file",
            node_metadata
        )

    def add_function_node(
        self,
        file_path,
        function_name,
        line
    ):
        """
        Add a function node.
        """

        node_id = f"{file_path}::{function_name}"

        self.add_node(
            node_id,
            "function",
            {
                "file": file_path,
                "name": function_name,
                "line": line
            }
        )

    def add_class_node(
        self,
        file_path,
        class_name,
        line
    ):
        """
        Add a class node.
        """

        node_id = f"{file_path}::{class_name}"

        self.add_node(
            node_id,
            "class",
            {
                "file": file_path,
                "name": class_name,
                "line": line
            }
        )

    def add_method_node(
        self,
        file_path,
        class_name,
        method_name,
        line
    ):
        """
        Add a method node.
        """

        node_id = (
            f"{file_path}::"
            f"{class_name}."
            f"{method_name}"
        )

        self.add_node(
            node_id,
            "method",
            {
                "file": file_path,
                "class": class_name,
                "name": method_name,
                "line": line
            }
        )

    def add_node_metadata(
        self,
        file_path,
        metadata
    ):
        """
        Add metadata to an existing node.
        """

        for node in self.nodes:
            if node["id"] == file_path:
                node.update(metadata)
                return

    def to_dict(self):
        """
        Convert graph to dictionary.
        """

        return {
            "nodes": self.nodes,
            "edges": self.edges
        }