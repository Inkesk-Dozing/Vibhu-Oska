"""
Vibhu-Oska AI-OS — CodeAnalyzer Plugin
AST-based static analysis, complexity metrics, and quality scoring.
Works with TestingFramework to form the self-correction loop.
"""

from __future__ import annotations

import ast
import re
import subprocess
import sys
import textwrap
import asyncio
from pathlib import Path
from typing import Any

from Backend.Plugins.ToolRegistry.BaseService import BaseService
from Backend.Plugins.Logger.Logger import Logger
from Shared.Models import PluginInfo, CoreStatus, ExecutionTarget


class CodeAnalyzer(BaseService):
    """
    Static code analysis plugin for Python (+ stub for other languages).

    Provides:
      - Cyclomatic complexity (McCabe)
      - AST structure analysis (classes, functions, imports)
      - Duplicate detection
      - Quality score (0-100)
      - Ruff linting integration
      - Code documentation ratio

    Actions:
      - analyze(code, language): Full analysis → quality_score dict
      - lint(code): Ruff lint → list of issues
      - complexity(code): Cyclomatic complexity per function
    """

    def __init__(self) -> None:
        self._initialized = False
        self._python = sys.executable
        self._log = Logger.get("CodeAnalyzer")

    # ══════════════════════════════════════════════════════════════
    # BaseService Interface
    # ══════════════════════════════════════════════════════════════

    def info(self) -> PluginInfo:
        return PluginInfo(
            name="code_analyzer",
            version="0.1.0",
            description="AST-based static analysis, complexity metrics, and quality scoring",
            capabilities=["analyze", "lint", "complexity"],
            status=CoreStatus.HEALTHY if self._initialized else CoreStatus.UNKNOWN,
            preferred_target=ExecutionTarget.CPU,
        )

    def health_check(self) -> bool:
        return self._initialized

    async def initialize(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        self._log.info("CodeAnalyzer ready")

    async def shutdown(self) -> None:
        self._initialized = False

    async def execute(self, action: str, **kwargs: Any) -> Any:
        if action == "analyze":
            return await self.analyze(kwargs["code"], kwargs.get("language", "python"))
        elif action == "lint":
            return await self.lint(kwargs["code"])
        elif action == "complexity":
            return self.compute_complexity(kwargs["code"])
        else:
            raise ValueError(f"Unknown CodeAnalyzer action: {action}")

    # ══════════════════════════════════════════════════════════════
    # Full Analysis
    # ══════════════════════════════════════════════════════════════

    async def analyze(self, code: str, language: str = "python") -> dict[str, Any]:
        """Run complete analysis and return quality score + breakdown."""
        if language != "python":
            return {"quality_score": 50, "note": f"Analysis for '{language}' not implemented", "language": language}

        # Parse AST
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return {
                "quality_score": 0,
                "syntax_valid":  False,
                "syntax_error":  f"Line {e.lineno}: {e.msg}",
                "language":      language,
            }

        # Gather metrics
        structure     = self._analyze_structure(tree, code)
        complexity    = self.compute_complexity(code)
        lint_issues   = await self.lint(code)
        doc_ratio     = self._doc_ratio(tree, code)

        # Compute quality score (0-100)
        score = 100

        # Penalty: lint issues
        score -= min(30, len(lint_issues.get("issues", [])) * 3)

        # Penalty: high complexity
        max_complexity = max((f["complexity"] for f in complexity.get("functions", [])), default=1)
        if max_complexity > 10: score -= 20
        elif max_complexity > 7: score -= 10
        elif max_complexity > 4: score -= 5

        # Penalty: no docstrings
        if doc_ratio < 0.3: score -= 10
        elif doc_ratio < 0.5: score -= 5

        # Penalty: very short (< 10 lines) — probably incomplete
        lines = code.strip().splitlines()
        if len(lines) < 10: score -= 15

        score = max(0, min(100, score))

        self._log.debug("Code analysis complete", score=score, functions=len(structure.get("functions", [])))

        return {
            "quality_score": score,
            "syntax_valid":  True,
            "language":      language,
            "structure":     structure,
            "complexity":    complexity,
            "lint":          lint_issues,
            "doc_ratio":     round(doc_ratio, 2),
            "line_count":    len(lines),
            "recommendation": self._recommend(score, lint_issues, max_complexity),
        }

    # ══════════════════════════════════════════════════════════════
    # AST Structure
    # ══════════════════════════════════════════════════════════════

    def _analyze_structure(self, tree: ast.AST, code: str) -> dict[str, Any]:
        classes   = [n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
        functions = [n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef)]
        imports   = [ast.unparse(n) for n in ast.walk(tree) if isinstance(n, ast.Import | ast.ImportFrom)]
        return {"classes": classes, "functions": functions, "imports": imports[:20]}

    # ══════════════════════════════════════════════════════════════
    # Cyclomatic Complexity (McCabe)
    # ══════════════════════════════════════════════════════════════

    def compute_complexity(self, code: str) -> dict[str, Any]:
        """Compute cyclomatic complexity per function."""
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return {"functions": [], "avg_complexity": 0}

        results = []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                cc = 1  # Base
                for child in ast.walk(node):
                    if isinstance(child, ast.If | ast.While | ast.For | ast.ExceptHandler |
                                       ast.With | ast.Assert | ast.comprehension):
                        cc += 1
                    elif isinstance(child, ast.BoolOp):
                        cc += len(child.values) - 1
                results.append({"name": node.name, "complexity": cc, "line": node.lineno})

        avg = round(sum(r["complexity"] for r in results) / len(results), 1) if results else 0
        return {"functions": results, "avg_complexity": avg}

    # ══════════════════════════════════════════════════════════════
    # Ruff Linting
    # ══════════════════════════════════════════════════════════════

    async def lint(self, code: str) -> dict[str, Any]:
        """Run Ruff linter on code string via subprocess."""
        try:
            import tempfile
            with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as f:
                f.write(code)
                tmppath = f.name

            result = await asyncio.to_thread(
                subprocess.run,
                [self._python, "-m", "ruff", "check", "--output-format=json", tmppath],
                capture_output=True, text=True, timeout=10
            )
            Path(tmppath).unlink(missing_ok=True)

            issues = []
            if result.stdout:
                import json
                try:
                    raw = json.loads(result.stdout)
                    issues = [{"code": i.get("code"), "message": i.get("message"), "line": i.get("location", {}).get("row")} for i in raw]
                except json.JSONDecodeError:
                    pass

            return {"issues": issues, "count": len(issues)}
        except FileNotFoundError:
            return {"issues": [], "count": 0, "note": "ruff not installed"}
        except Exception as e:
            return {"issues": [], "count": 0, "error": str(e)}

    # ══════════════════════════════════════════════════════════════
    # Documentation Ratio
    # ══════════════════════════════════════════════════════════════

    def _doc_ratio(self, tree: ast.AST, code: str) -> float:
        """Ratio of functions/classes that have docstrings."""
        total = 0
        documented = 0
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
                total += 1
                if ast.get_docstring(node):
                    documented += 1
        return documented / total if total else 0.5

    # ══════════════════════════════════════════════════════════════
    # Recommendation
    # ══════════════════════════════════════════════════════════════

    def _recommend(self, score: int, lint: dict, max_cc: int) -> str:
        if score >= 85:
            return "Code quality is high — ready for deployment"
        issues = lint.get("issues", [])
        parts = []
        if issues: parts.append(f"Fix {len(issues)} lint issue(s)")
        if max_cc > 7: parts.append("Reduce function complexity (consider splitting functions > 7)")
        if not parts: parts.append("Add docstrings and increase test coverage")
        return "; ".join(parts)
