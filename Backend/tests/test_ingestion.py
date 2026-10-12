from pathlib import Path

import pytest
from core.ingestion import (
    IngestionError,
    from_local_path,
    from_pasted_markdown,
    is_candidate,
    parse_github_url,
)


FIXTURE_PROJECT = Path(__file__).parent / "fixtures" / "tiny_counter"


def test_parse_valid():
    assert parse_github_url("https://github.com/foo/bar") == ("foo", "bar")
    assert parse_github_url("https://github.com/foo/bar.git/") == ("foo", "bar")


@pytest.mark.parametrize("u", ["https://evil.com/foo/bar", "ftp://github.com/a/b", "https://github.com/onlyowner", "nonsense"])
def test_parse_invalid(u):
    with pytest.raises(IngestionError):
        parse_github_url(u)


def test_secret_and_build_files_excluded():
    assert not is_candidate(".env", 10)
    assert not is_candidate("config/id_rsa", 10)
    assert not is_candidate("node_modules/x/index.js", 10)
    assert not is_candidate("big.py", 10**9)
    assert is_candidate("README.md", 100)
    assert is_candidate("index.html", 100)
    assert is_candidate("styles/main.css", 100)


def test_paste_fallback():
    docs = from_pasted_markdown("# Hi")
    assert docs[0].path == "pasted/README.md"
    with pytest.raises(IngestionError):
        from_pasted_markdown("  ")


def test_ingest_local_project_fixture():
    docs = from_local_path(FIXTURE_PROJECT)
    paths = {doc.path for doc in docs}

    assert "README.md" in paths
    assert "src/counter.py" in paths
    assert all(doc.source_id and doc.content for doc in docs)


def test_local_path_must_be_a_directory(tmp_path):
    file_path = tmp_path / "README.md"
    file_path.write_text("# Not a directory", encoding="utf-8")

    with pytest.raises(IngestionError, match="must be a directory"):
        from_local_path(file_path)


def test_local_import_excludes_secrets_and_virtualenv(tmp_path):
    (tmp_path / "README.md").write_text("# Example", encoding="utf-8")
    (tmp_path / ".env").write_text("TOKEN=not-a-real-secret", encoding="utf-8")
    venv_file = tmp_path / "venv" / "site-packages" / "module.py"
    venv_file.parent.mkdir(parents=True)
    venv_file.write_text("ignored", encoding="utf-8")

    docs = from_local_path(tmp_path)

    assert {doc.path for doc in docs} == {"README.md"}
