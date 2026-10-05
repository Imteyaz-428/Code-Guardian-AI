import pytest

from backend.analysis.graph_dataset import GraphDataset
from backend.ml.dataset_collection import (
    GraphDatasetCollection,
    GraphDatasetRecord,
)


def create_dataset() -> GraphDataset:
    return GraphDataset(
        node_ids=["node_1", "node_2"],
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


def test_add_record():
    collection = GraphDatasetCollection()

    record = GraphDatasetRecord(
        sample_id="repo_1",
        dataset=create_dataset(),
    )

    collection.add(record)

    assert collection.num_samples == 1
    assert collection.sample_ids == ["repo_1"]


def test_duplicate_sample_id_rejected():
    collection = GraphDatasetCollection()

    collection.add(
        GraphDatasetRecord(
            sample_id="repo_1",
            dataset=create_dataset(),
        )
    )

    with pytest.raises(ValueError):
        collection.add(
            GraphDatasetRecord(
                sample_id="repo_1",
                dataset=create_dataset(),
            )
        )


def test_collection_validation():
    collection = GraphDatasetCollection()

    collection.add(
        GraphDatasetRecord(
            sample_id="repo_1",
            dataset=create_dataset(),
            label_source="static_rule",
        )
    )

    collection.validate()

    assert collection.num_samples == 1


def test_split():
    collection = GraphDatasetCollection()

    for i in range(10):
        collection.add(
            GraphDatasetRecord(
                sample_id=f"repo_{i}",
                dataset=create_dataset(),
            )
        )

    train, validation, test = collection.split(
        train_ratio=0.7,
        validation_ratio=0.2,
        test_ratio=0.1,
        seed=42,
    )

    assert train.num_samples == 7
    assert validation.num_samples == 2
    assert test.num_samples == 1


def test_split_has_no_overlap():
    collection = GraphDatasetCollection()

    for i in range(20):
        collection.add(
            GraphDatasetRecord(
                sample_id=f"repo_{i}",
                dataset=create_dataset(),
            )
        )

    train, validation, test = collection.split(seed=42)

    train_ids = set(train.sample_ids)
    validation_ids = set(validation.sample_ids)
    test_ids = set(test.sample_ids)

    assert train_ids.isdisjoint(validation_ids)
    assert train_ids.isdisjoint(test_ids)
    assert validation_ids.isdisjoint(test_ids)


def test_split_is_deterministic():
    collection = GraphDatasetCollection()

    for i in range(20):
        collection.add(
            GraphDatasetRecord(
                sample_id=f"repo_{i}",
                dataset=create_dataset(),
            )
        )

    train1, validation1, test1 = collection.split(seed=42)
    train2, validation2, test2 = collection.split(seed=42)

    assert train1.sample_ids == train2.sample_ids
    assert validation1.sample_ids == validation2.sample_ids
    assert test1.sample_ids == test2.sample_ids


def test_invalid_split_ratio():
    collection = GraphDatasetCollection()

    with pytest.raises(ValueError):
        collection.split(
            train_ratio=0.5,
            validation_ratio=0.2,
            test_ratio=0.2,
        )


def test_label_source():
    record = GraphDatasetRecord(
        sample_id="repo_1",
        dataset=create_dataset(),
        label_source="real_vulnerability",
    )

    assert record.label_source == "real_vulnerability"


def test_metadata():
    record = GraphDatasetRecord(
        sample_id="repo_1",
        dataset=create_dataset(),
        metadata={
            "language": "python",
            "repository": "example",
        },
    )

    assert record.metadata["language"] == "python"
    assert record.metadata["repository"] == "example"


def test_to_dict():
    collection = GraphDatasetCollection()

    collection.add(
        GraphDatasetRecord(
            sample_id="repo_1",
            dataset=create_dataset(),
            label_source="static_rule",
            source="local_repository",
        )
    )

    data = collection.to_dict()

    assert data["num_samples"] == 1
    assert len(data["records"]) == 1
    assert data["records"][0]["sample_id"] == "repo_1"
    assert data["records"][0]["label_source"] == "static_rule"