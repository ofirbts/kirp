import zipfile
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_WP = _ROOT / "docs" / "KIRP_INTELLIGENCE_OS_WHITEPAPER.md"
_BRIEF = _ROOT / "docs" / "KIRP_EXECUTIVE_TECHNICAL_BRIEF.md"
_HTML = _ROOT / "docs" / "KIRP_EXECUTIVE_TECHNICAL_BRIEF_PRINT.html"


def test_whitepaper_present_with_core_sections():
    text = _WP.read_text(encoding="utf-8")
    assert _WP.is_file()
    assert "KIRP_EXECUTIVE_TECHNICAL_BRIEF.md" in text
    assert "## Why now" in text
    assert "## Operating theses" in text
    assert "## 5 · Real system characteristics" in text
    assert "## 6 · One real flow" in text
    assert "**Why me / why this:**" in text
    assert "Most AI systems do not fail loudly enough." in text
    assert "A hallucinated success response is operationally worse than a crashed request." in text
    assert "Autonomous without auditability is just unmanaged side effects." in text
    assert "Prompt orchestration is not systems engineering." in text
    assert "```mermaid" in text
    assert "flowchart TB" in text or "flowchart TD" in text or "flowchart LR" in text
    assert "stateDiagram-v2" in text


def test_executive_brief_and_print_html_exist():
    brief = _BRIEF.read_text(encoding="utf-8")
    assert _BRIEF.is_file()
    assert "## Thesis" in brief
    assert "Real infra choices" in brief
    assert _HTML.is_file()
    assert "mermaid" in _HTML.read_text(encoding="utf-8")
    assert "IBM Plex" in _HTML.read_text(encoding="utf-8")


def test_outreach_zip_bundle():
    zpath = _ROOT / "docs" / "KIRP_TECHNICAL_OUTREACH_BUNDLE.zip"
    assert zpath.is_file()
    with zipfile.ZipFile(zpath, "r") as zf:
        names = set(zf.namelist())
    assert "KIRP_EXECUTIVE_TECHNICAL_BRIEF.md" in names
    assert "KIRP_EXECUTIVE_TECHNICAL_BRIEF_PRINT.html" in names
    assert "KIRP_INTELLIGENCE_OS_WHITEPAPER.md" in names
    assert "KIRP_OUTREACH_README_HE.txt" in names
