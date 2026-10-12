import json
import pytest
from core import export
from core.schemas import CaseStudy

CS = CaseStudy(title='T #*_$ "x"', summary="s", problem="p", architecture="a", implementation="i",
               challenges="c", results="r", limitations="l", future_work="f")


def test_typst_data_is_json_safe():
    data = export.build_typst_data(CS, "https://github.com/a/b")
    assert json.loads(json.dumps(data))["title"] == CS.title  # no Typst escaping needed


def test_markdown_has_sections():
    md = export.case_study_to_markdown(CS)
    assert "## Limitations" in md


def test_pdf_missing_typst(monkeypatch):
    monkeypatch.setattr(export.shutil, "which", lambda _: None)
    with pytest.raises(export.ExportError):
        export.export_pdf(CS)
