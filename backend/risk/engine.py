from backend.models.analysis_result import (
    FunctionMetrics,
    RiskFinding,
)


class RiskEngine:

    def calculate_risk(
        self,
        metrics: FunctionMetrics
    ) -> RiskFinding:

        score = 0
        reasons = []

        # -------------------------
        # Cyclomatic complexity
        # -------------------------

        if metrics.cyclomatic_complexity >= 10:
            score += 30
            reasons.append(
                "Very high cyclomatic complexity"
            )

        elif metrics.cyclomatic_complexity >= 5:
            score += 20
            reasons.append(
                "High cyclomatic complexity"
            )

        elif metrics.cyclomatic_complexity >= 3:
            score += 10
            reasons.append(
                "Moderate cyclomatic complexity"
            )

        # -------------------------
        # Lines of code
        # -------------------------

        if metrics.lines_of_code >= 50:
            score += 25
            reasons.append(
                "Large function"
            )

        elif metrics.lines_of_code >= 25:
            score += 15
            reasons.append(
                "Moderately large function"
            )

        # -------------------------
        # Nesting depth
        # -------------------------

        if metrics.nesting_depth >= 4:
            score += 20
            reasons.append(
                "Deep nesting"
            )

        elif metrics.nesting_depth >= 2:
            score += 10
            reasons.append(
                "Moderate nesting"
            )

        # -------------------------
        # Parameters
        # -------------------------

        if metrics.parameters >= 6:
            score += 10
            reasons.append(
                "Too many parameters"
            )

        elif metrics.parameters >= 4:
            score += 5
            reasons.append(
                "Multiple parameters"
            )

        # -------------------------
        # Function calls
        # -------------------------

        if metrics.function_calls >= 10:
            score += 15
            reasons.append(
                "Many function calls"
            )

        elif metrics.function_calls >= 5:
            score += 8
            reasons.append(
                "Several function calls"
            )

        # -------------------------
        # Limit score
        # -------------------------

        score = min(score, 100)

        # -------------------------
        # Risk level
        # -------------------------

        if score >= 50:
            level = "HIGH"

        elif score >= 30:
            level = "MEDIUM"

        else:
            level = "LOW"

        return RiskFinding(
            function_name=metrics.name,
            line=metrics.line,
            score=score,
            level=level,
            reasons=reasons,
        )