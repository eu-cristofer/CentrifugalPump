"""The bundled Word report templates are neutral and generated.

They carry only the styles the report code uses, no image, author, notice or
classification label, and they equal the output of
``pump/templates/build_templates.py`` byte for byte.  A site template can be
chosen with ``template_path`` or ``PUMP_TEMPLATE_DIR``.
"""

import importlib.util
import re
import shutil
import zipfile
from pathlib import Path

import pytest
from docx import Document

from pump.utilities.report import ReportGenerator

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_DIR = ROOT / "pump" / "templates"
LANGUAGES = ["en", "pt"]
STYLES = [
    "Normal",
    "Title_1",
    "Title_2",
    "Title_3",
    "Text_body",
    "Intense Quote",
    "Table Grid",
]
FORBIDDEN = re.compile(r"property|confidential|INTERNA", re.IGNORECASE)


@pytest.fixture(scope="module")
def builder():
    spec = importlib.util.spec_from_file_location(
        "build_templates", TEMPLATE_DIR / "build_templates.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _bundled(language):
    return TEMPLATE_DIR / f"template_{language}.docx"


@pytest.mark.parametrize("language", LANGUAGES)
def test_bundled_template_has_required_styles(language):
    names = {style.name for style in Document(str(_bundled(language))).styles}
    for name in STYLES:
        assert name in names


@pytest.mark.parametrize("language", LANGUAGES)
def test_bundled_template_is_empty_and_clean(language):
    path = _bundled(language)
    doc = Document(str(path))
    assert not [p for p in doc.paragraphs if p.text.strip()]
    assert not doc.tables
    for section in doc.sections:
        assert not any(p.text.strip() for p in section.header.paragraphs)
    assert doc.core_properties.author == ""
    assert doc.core_properties.title == "PumpFlow report"
    with zipfile.ZipFile(path) as zf:
        for name in zf.namelist():
            assert not name.startswith("word/media/")
            assert not name.startswith("word/embeddings/")


@pytest.mark.parametrize("language", LANGUAGES)
def test_bundled_template_has_no_forbidden_words(language):
    with zipfile.ZipFile(_bundled(language)) as zf:
        for name in zf.namelist():
            if name.endswith((".xml", ".rels")):
                text = zf.read(name).decode("utf-8", errors="ignore")
                assert not FORBIDDEN.search(text), name


@pytest.mark.parametrize("language", LANGUAGES)
def test_build_is_reproducible_and_matches_committed(builder, tmp_path, language):
    first = builder.build_template(language, tmp_path / "a" / f"{language}.docx")
    second = builder.build_template(language, tmp_path / "b" / f"{language}.docx")
    assert first.read_bytes() == second.read_bytes()
    assert first.read_bytes() == _bundled(language).read_bytes()


def test_template_path_defaults_to_bundled(monkeypatch):
    monkeypatch.delenv("PUMP_TEMPLATE_DIR", raising=False)
    path = ReportGenerator(language="en")._get_template_path()
    assert Path(path).resolve() == _bundled("en").resolve()


def test_template_path_uses_env_dir(monkeypatch, tmp_path):
    shutil.copy(_bundled("en"), tmp_path / "template_en.docx")
    monkeypatch.setenv("PUMP_TEMPLATE_DIR", str(tmp_path))
    path = ReportGenerator(language="en")._get_template_path()
    assert Path(path).resolve() == (tmp_path / "template_en.docx").resolve()


def test_env_dir_without_file_falls_back_to_bundled(monkeypatch, tmp_path):
    monkeypatch.setenv("PUMP_TEMPLATE_DIR", str(tmp_path))
    path = ReportGenerator(language="en")._get_template_path()
    assert Path(path).resolve() == _bundled("en").resolve()


def test_explicit_template_path_wins_over_env(monkeypatch, tmp_path):
    env_dir = tmp_path / "env"
    env_dir.mkdir()
    shutil.copy(_bundled("en"), env_dir / "template_en.docx")
    explicit = tmp_path / "explicit.docx"
    shutil.copy(_bundled("en"), explicit)
    monkeypatch.setenv("PUMP_TEMPLATE_DIR", str(env_dir))
    gen = ReportGenerator(language="en", template_path=explicit)
    assert Path(gen._get_template_path()).resolve() == explicit.resolve()


def test_missing_explicit_template_raises(monkeypatch, tmp_path):
    monkeypatch.delenv("PUMP_TEMPLATE_DIR", raising=False)
    gen = ReportGenerator(language="en", template_path=tmp_path / "missing.docx")
    with pytest.raises(FileNotFoundError):
        gen._get_template_path()
