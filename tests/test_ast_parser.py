from backend.parsing.ast_parser import ASTParser, CodeExtractor
from backend.analysis.metrics import MetricsAnalyzer


file_path = "tests/sample_project/auth.py"

# -------------------------
# AST extraction
# -------------------------

parser = ASTParser(file_path)

tree = parser.parse()

extractor = CodeExtractor()
extractor.visit(tree)

result = extractor.get_result(file_path)

print("=== ANALYSIS RESULT ===")

print(result)


# -------------------------
# Metrics
# -------------------------

metrics_analyzer = MetricsAnalyzer()
metrics_analyzer.visit(tree)

print("\n=== FUNCTION METRICS ===")

for metric in metrics_analyzer.metrics:
    print(metric)