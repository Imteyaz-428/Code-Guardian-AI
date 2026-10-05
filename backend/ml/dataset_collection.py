from __future__ import annotations

from dataclasses import dataclass, field
import random
from typing import Any

from backend.analysis.graph_dataset import GraphDataset


@dataclass
class GraphDatasetRecord:
    """
    One repository/codebase represented as a single GraphDataset.

    A record is the unit used for dataset splitting.
    This prevents node-level leakage between train/validation/test sets.
    """

    sample_id: str
    dataset: GraphDataset

    label_source: str = "static_rule"

    source: str | None = None

    metadata: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        """Validate this dataset record."""

        if not self.sample_id:
            raise ValueError("sample_id cannot be empty")

        self.dataset.validate()

        if not self.label_source:
            raise ValueError("label_source cannot be empty")


@dataclass
class GraphDatasetCollection:
    """
    Collection of graph datasets.

    Each GraphDataset represents one repository/codebase.

    Example:

        Repository A -> GraphDataset
        Repository B -> GraphDataset
        Repository C -> GraphDataset
        ...

    Dataset splitting happens at repository/sample level,
    not at individual node level.
    """

    records: list[GraphDatasetRecord] = field(default_factory=list)

    def add(self, record: GraphDatasetRecord) -> None:
        """Add a dataset record to the collection."""

        record.validate()

        if any(existing.sample_id == record.sample_id for existing in self.records):
            raise ValueError(
                f"Duplicate sample_id: {record.sample_id}"
            )

        self.records.append(record)

    @property
    def num_samples(self) -> int:
        """Return number of graph samples."""

        return len(self.records)

    @property
    def sample_ids(self) -> list[str]:
        """Return all sample IDs."""

        return [record.sample_id for record in self.records]

    def validate(self) -> None:
        """Validate the entire collection."""

        seen_ids: set[str] = set()

        for record in self.records:
            record.validate()

            if record.sample_id in seen_ids:
                raise ValueError(
                    f"Duplicate sample_id: {record.sample_id}"
                )

            seen_ids.add(record.sample_id)

    def split(
        self,
        train_ratio: float = 0.70,
        validation_ratio: float = 0.15,
        test_ratio: float = 0.15,
        seed: int = 42,
    ) -> tuple[
        "GraphDatasetCollection",
        "GraphDatasetCollection",
        "GraphDatasetCollection",
    ]:
        """
        Split collection into train, validation and test sets.

        Splitting happens at graph/repository level.

        This is important because splitting individual nodes from
        the same repository can cause data leakage.
        """

        ratios = (
            train_ratio,
            validation_ratio,
            test_ratio,
        )

        if any(ratio < 0 for ratio in ratios):
            raise ValueError("Split ratios cannot be negative")

        if abs(sum(ratios) - 1.0) > 1e-6:
            raise ValueError(
                "train_ratio + validation_ratio + test_ratio must equal 1.0"
            )

        shuffled_records = list(self.records)

        rng = random.Random(seed)
        rng.shuffle(shuffled_records)

        total = len(shuffled_records)

        train_count = int(total * train_ratio)
        validation_count = int(total * validation_ratio)

        train_records = shuffled_records[:train_count]

        validation_records = shuffled_records[
            train_count:train_count + validation_count
        ]

        test_records = shuffled_records[
            train_count + validation_count:
        ]

        return (
            GraphDatasetCollection(train_records),
            GraphDatasetCollection(validation_records),
            GraphDatasetCollection(test_records),
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize the collection."""

        return {
            "num_samples": self.num_samples,
            "records": [
                {
                    "sample_id": record.sample_id,
                    "label_source": record.label_source,
                    "source": record.source,
                    "metadata": record.metadata,
                    "dataset": record.dataset.to_dict(),
                }
                for record in self.records
            ],
        }