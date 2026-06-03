from pathlib import Path


def test_ci_local_script_matches_github_tests_workflow() -> None:
    root = Path(__file__).resolve().parents[1]
    script = root / "scripts" / "ci_local.sh"
    workflow = (root / ".github" / "workflows" / "tests.yml").read_text(encoding="utf-8")
    text = script.read_text(encoding="utf-8")
    assert script.is_file()
    assert "requirements-dev.txt" in text
    assert "pytest_asyncio" in text
    assert "pytest tests/" in text
    assert "npm run lint" in text
    assert "npm run build" in text
    assert "requirements-dev.txt" in workflow
    assert "pytest-asyncio" in workflow or "pytest_asyncio" in workflow
