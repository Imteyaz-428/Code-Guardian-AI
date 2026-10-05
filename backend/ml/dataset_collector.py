from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from backend.analysis.graph_dataset import GraphDatasetBuilder
from backend.ml.dataset_collection import (
    GraphDatasetCollection,
    GraphDatasetRecord,
)


class DatasetCollector:
    """
    Converts analyzed repositories into GraphDataset records.

    Pipeline:

        Repository
            ↓
        ProjectAnalyzer
            ↓
        UnifiedCodeGraph
            ↓
        GraphDataset
            ↓
        GraphDatasetRecord
            ↓
        GraphDatasetCollection

    One repository produces exactly one GraphDataset.
    """

    def __init__(
        self,
        analyzer_factory: Callable[[Path], Any],
        label_provider: Callable[[Any], Any] | None = None,
    ) -> None:
        """
        Parameters
        ----------
        analyzer_factory:
            Function that receives a repository path and returns
            a configured ProjectAnalyzer.

        label_provider:
            Optional function that receives the analyzer and returns
            labels aligned by graph node ID.
        """

        self.analyzer_factory = analyzer_factory
        self.label_provider = label_provider

    def collect_repository(
        self,
        repository_path: str | Path,
        sample_id: str | None = None,
        label_source: str = "static_rule",
        metadata: dict[str, Any] | None = None,
    ) -> GraphDatasetRecord:
        """
        Analyze one repository and convert it into a GraphDatasetRecord.
        """

        repository_path = Path(repository_path)

        if not repository_path.exists():
            raise FileNotFoundError(
                f"Repository does not exist: {repository_path}"
            )

        if not repository_path.is_dir():
            raise ValueError(
                f"Repository path must be a directory: {repository_path}"
            )

        if sample_id is None:
            sample_id = repository_path.name

        analyzer = self.analyzer_factory(repository_path)

        # Run the complete existing static-analysis pipeline.
        analyzer.analyze()

        # ProjectAnalyzer already builds the unified code graph.
        graph = analyzer.unified_code_graph

        labels = None

        if self.label_provider is not None:
            labels = self.label_provider(analyzer)

        dataset = GraphDatasetBuilder.from_graph(
            graph,
            labels=labels,
        )

        record_metadata = {
            "repository_name": repository_path.name,
            "repository_path": str(repository_path),
            "num_nodes": dataset.num_nodes,
            "num_edges": dataset.num_edges,
            "num_features": dataset.num_features,
        }

        if metadata is not None:
            record_metadata.update(metadata)

        return GraphDatasetRecord(
            sample_id=sample_id,
            dataset=dataset,
            label_source=label_source,
            source=str(repository_path),
            metadata=record_metadata,
        )

    def collect(
        self,
        repositories: list[str | Path],
        label_source: str = "static_rule",
    ) -> GraphDatasetCollection:
        """
        Collect multiple repositories into one dataset collection.
        """

        collection = GraphDatasetCollection()

        for repository_path in repositories:
            record = self.collect_repository(
                repository_path=repository_path,
                label_source=label_source,
            )

            collection.add(record)

        collection.validate()

        return collection