"""E2E: CliRunner brandos run, daily, signals, agents."""
from click.testing import CliRunner

from brand_os_cli.main import brandos

runner = CliRunner()


def test_brandos_agents():
    result = runner.invoke(brandos, ["agents"])
    assert result.exit_code == 0
    assert "CONTEXT_SCANNER" in result.output or "STRATEGIC_PLANNER" in result.output


def test_brandos_run_requires_topic():
    result = runner.invoke(brandos, ["run"])
    assert result.exit_code != 0


def test_brandos_run_with_topic():
    result = runner.invoke(brandos, ["run", "API release", "--api"])
    if result.exit_code != 0 and "Connection" in str(result.exception or result.output):
        return
    assert result.exit_code == 0 or "API error" in result.output


def test_brandos_signals():
    result = runner.invoke(brandos, ["signals"])
    assert result.exit_code == 0


def test_brandos_daily():
    result = runner.invoke(brandos, ["daily"])
    assert result.exit_code == 0
