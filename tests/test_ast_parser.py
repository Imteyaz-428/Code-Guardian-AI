from pathlib import Path
import pytest
from backend.parsing.ast_parser import ASTParser, CodeExtractor


SAMPLE_FILE = Path("tests/sample_project/auth.py")


def test_ast_parser_parses_valid_python():
    parser = ASTParser(SAMPLE_FILE)

    tree = parser.parse()

    assert tree is not None
    
    
def test_code_extractor_extracts_functions_and_structure(tmp_path):
    source_file = tmp_path / "sample.py"

    source_file.write_text(
        """
import os

def login(username):
    if username:
        print(username)
        return True
    return False
""",
        encoding="utf-8",
    )

    tree = ASTParser(source_file).parse()

    extractor = CodeExtractor()
    extractor.visit(tree)

    result = extractor.get_result(source_file)

    assert len(result.functions) == 1
    assert result.functions[0].name == "login"
    assert result.functions[0].parameters == ["username"]

    assert result.imports == ["os"]
    assert result.function_calls == ["print"]
    assert result.conditions == 1
    assert result.loops == 0
    assert result.returns == 2
    
    
    
def test_ast_parser_rejects_invalid_python(tmp_path):
    source_file = tmp_path / "invalid.py"

    source_file.write_text(
        "def broken(:\n    pass\n",
        encoding="utf-8",
    )

    parser = ASTParser(source_file)

    with pytest.raises(ValueError, match="Syntax error"):
        parser.parse()