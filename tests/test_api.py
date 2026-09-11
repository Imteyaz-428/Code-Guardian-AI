from fastapi.testclient import TestClient

from backend.api.main import app
from backend.core.config import settings


client = TestClient(app)


def test_analyze_api_returns_control_flow_graph(tmp_path, monkeypatch):
    """
    Verify that the /analyze API returns CFG data
    for functions found in the repository.
    """

    # ---------------------------------------------------------
    # Create a temporary test repository
    # ---------------------------------------------------------

    repository = tmp_path / "sample_repo"
    repository.mkdir()

    main_file = repository / "main.py"

    main_file.write_text(
        """
def calculate(x):
    if x > 0:
        return x
    return 0
""".strip()
    )

    # ---------------------------------------------------------
    # Allow the temporary repository for this test
    # ---------------------------------------------------------

    monkeypatch.setattr(
        settings,
        "ALLOWED_ANALYSIS_ROOT",
        tmp_path,
    )

    # ---------------------------------------------------------
    # Call API
    # ---------------------------------------------------------

    response = client.post(
        "/analyze",
        json={
            "repository_path": str(repository),
        },
    )

    # ---------------------------------------------------------
    # Basic response validation
    # ---------------------------------------------------------

    assert response.status_code == 200

    data = response.json()

    assert "control_flow_graphs" in data

    # ---------------------------------------------------------
    # CFG validation
    # ---------------------------------------------------------

    cfgs = data["control_flow_graphs"]

    assert len(cfgs) == 1

    cfg = cfgs[0]

    assert cfg["function"] == "main.py::calculate"

    # CFG must contain nodes.
    assert len(cfg["nodes"]) > 0

    # CFG must contain edges.
    assert len(cfg["edges"]) > 0

    # ---------------------------------------------------------
    # Check ENTRY and EXIT nodes
    # ---------------------------------------------------------

    node_types = {
        node["type"]
        for node in cfg["nodes"]
    }

    assert "entry" in node_types
    assert "exit" in node_types

    # ---------------------------------------------------------
    # Check condition node
    # ---------------------------------------------------------

    condition_nodes = [
        node
        for node in cfg["nodes"]
        if node["type"] == "condition"
    ]

    assert len(condition_nodes) == 1

    assert condition_nodes[0]["label"] == "if"