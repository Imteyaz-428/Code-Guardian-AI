from pathlib import Path
from unittest.mock import Mock

import pytest

from backend.analysis.graph_dataset import GraphDataset
from backend.ml.dataset_collector import DatasetCollector


class FakeGraph:
    pass


def create_dataset() -> GraphDataset:
    return GraphDataset(
        node_ids=[
            "node_1",
            "node_2",
        ],
        node_features=[
            [1.0, 0.0],
            [0.0, 1.0],
        ],
        edge_index=[
            [0],
            [1],
        ],
        edge_types=[
            "CONTROL_FLOW",
        ],
        node_types=[
            "function",
            "function",
        ],
        node_metadata=[
            {},
            {},
        ],
        labels=[
            0.0,
            1.0,
        ],
    )


def test_collect_repository_requires_existing_path(tmp_path):
    analyzer_factory = Mock()

    collector = DatasetCollector(
        analyzer_factory=analyzer_factory,
    )

    missing_path = tmp_path / "does_not_exist"

    with pytest.raises(FileNotFoundError):
        collector.collect_repository(missing_path)

    analyzer_factory.assert_not_called()


def test_collect_repository_requires_directory(tmp_path):
    analyzer_factory = Mock()

    collector = DatasetCollector(
        analyzer_factory=analyzer_factory,
    )

    file_path = tmp_path / "repository.py"
    file_path.write_text("print('hello')")

    with pytest.raises(ValueError):
        collector.collect_repository(file_path)

    analyzer_factory.assert_not_called()


def test_collect_repository(tmp_path, monkeypatch):
    repository = tmp_path / "repo_1"
    repository.mkdir()

    fake_graph = FakeGraph()

    analyzer = Mock()
    analyzer.unified_code_graph = fake_graph

    analyzer_factory = Mock(
        return_value=analyzer
    )

    expected_dataset = create_dataset()

    from backend.ml import dataset_collector

    monkeypatch.setattr(
        dataset_collector.GraphDatasetBuilder,
        "from_graph",
        Mock(return_value=expected_dataset),
    )

    collector = DatasetCollector(
        analyzer_factory=analyzer_factory,
    )

    record = collector.collect_repository(
        repository_path=repository,
        sample_id="repo_1",
    )

    analyzer_factory.assert_called_once_with(
        Path(repository)
    )

    analyzer.analyze.assert_called_once()

    assert record.sample_id == "repo_1"
    assert record.dataset is expected_dataset
    assert record.label_source == "static_rule"
    assert record.metadata["repository_name"] == "repo_1"
    assert record.metadata["num_nodes"] == 2
    assert record.metadata["num_edges"] == 1
    assert record.metadata["num_features"] == 2


def test_collect_multiple_repositories(tmp_path, monkeypatch):
    repo_1 = tmp_path / "repo_1"
    repo_2 = tmp_path / "repo_2"
    repo_3 = tmp_path / "repo_3"

    repo_1.mkdir()
    repo_2.mkdir()
    repo_3.mkdir()

    analyzer = Mock()

    analyzer_factory = Mock(
        return_value=analyzer
    )

    expected_dataset = create_dataset()

    from backend.ml import dataset_collector

    monkeypatch.setattr(
        dataset_collector.GraphDatasetBuilder,
        "from_graph",
        Mock(return_value=expected_dataset),
    )

    collector = DatasetCollector(
        analyzer_factory=analyzer_factory,
    )

    collection = collector.collect(
        [
            repo_1,
            repo_2,
            repo_3,
        ]
    )

    assert collection.num_samples == 3

    assert set(collection.sample_ids) == {
        "repo_1",
        "repo_2",
        "repo_3",
    }

    assert analyzer.analyze.call_count == 3