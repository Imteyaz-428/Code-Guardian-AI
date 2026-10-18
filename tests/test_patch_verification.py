from backend.services.patch_verification import PatchVerificationService


def create_repository(root, *, test_source=None):
    """Create a minimal temporary Python repository."""
    (root / "app.py").write_text(
        "def calculate(a, b):\n"
        "    return a + b\n",
        encoding="utf-8",
    )

    if test_source is not None:
        test_dir = root / "nested" / "tests"
        test_dir.mkdir(parents=True)
        (test_dir / "test_app.py").write_text(
            test_source,
            encoding="utf-8",
        )

    return root


def test_invalid_python_syntax_is_rejected(tmp_path):
    repo = create_repository(tmp_path)

    result = PatchVerificationService().verify(
        repo, "app.py", "def broken(:\n"
    )

    assert result["status"] == "rejected"
    assert result["syntax_passed"] is False


def test_disabled_tests_return_syntax_passed(tmp_path):
    repo = create_repository(tmp_path)

    result = PatchVerificationService().verify(
        repo,
        "app.py",
        "def calculate(a, b):\n    return a + b\n",
        run_tests=False,
    )

    assert result["status"] == "syntax_passed"
    assert result["tests_run"] is False


def test_no_test_files_returns_syntax_passed(tmp_path):
    repo = create_repository(tmp_path)

    result = PatchVerificationService().verify(
        repo,
        "app.py",
        "def calculate(a, b):\n    return a + b\n",
    )

    assert result["status"] == "syntax_passed"
    assert result["tests_passed"] is None


def test_nested_tests_that_pass_are_verified(tmp_path):
    repo = create_repository(
        tmp_path,
        test_source=(
            "from app import calculate\n\n"
            "def test_calculate():\n"
            "    assert calculate(2, 3) == 5\n"
        ),
    )

    result = PatchVerificationService().verify(
        repo,
        "app.py",
        "def calculate(a, b):\n    return a + b\n",
    )

    assert result["status"] == "verified"
    assert result["tests_run"] is True
    assert result["tests_passed"] is True


def test_failing_tests_are_rejected(tmp_path):
    repo = create_repository(
        tmp_path,
        test_source=(
            "from app import calculate\n\n"
            "def test_calculate():\n"
            "    assert calculate(2, 3) == 99\n"
        ),
    )

    result = PatchVerificationService().verify(
        repo,
        "app.py",
        "def calculate(a, b):\n    return a + b\n",
    )

    assert result["status"] == "rejected"
    assert result["tests_passed"] is False


def test_zero_collected_tests_are_not_verified(tmp_path):
    repo = create_repository(
        tmp_path,
        test_source="value = 42\n",
    )

    result = PatchVerificationService().verify(
        repo,
        "app.py",
        "def calculate(a, b):\n    return a + b\n",
    )

    assert result["status"] != "verified"
