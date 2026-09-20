"""Regression tests for the SaveAsText parser/lint input gate."""

import importlib.util
from pathlib import Path

import pytest


SPEC = importlib.util.spec_from_file_location(
    "extract_access_saveastext", Path(__file__).with_name("extract_access_saveastext.py")
)
HELPER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(HELPER)


@pytest.mark.parametrize("boundary", ["CodeBehindForm\n", 'Attribute VB_Name = "Form_Sample"\n'])
def test_ready_extracts_only_the_vba_tail(boundary):
    code = "Option Compare Database\nPublic Function Smoke() As Boolean\n    Smoke = True\nEnd Function\n"
    result = HELPER.extract_access_saveastext("Version = 20\nBegin Form\nEnd\n" + boundary + code)
    assert result.status == "ready"
    assert result.kind == "access_saveastext_mixed_dump"
    assert result.source == (boundary if boundary.startswith("Attribute") else "") + code


def test_code_marker_precedes_attributes_and_preserves_vba_body():
    code = ('Attribute VB_Name = "Form_Sample"\nOption Explicit\n'
            'Public Sub Smoke()\n    CodeBehindForm\nEnd Sub\n')
    result = HELPER.extract_access_saveastext("\ufeffVersion = 20\nCodeBehindForm\n" + code)
    assert result.status == "ready"
    assert result.source == code


def test_comments_and_blank_lines_before_valid_opening_are_preserved():
    code = "\n' comment\nRem comment\nOption Explicit\n"
    result = HELPER.extract_access_saveastext("CodeBehindForm\n" + code)
    assert result.status == "ready"
    assert result.source == code


def test_no_vba_dump_does_not_reach_analyzer(tmp_path):
    path = tmp_path / "form.txt"
    path.write_text("Version = 20\nBegin Form\n    Caption = \"Sample\"\nEnd\n", encoding="utf-8")
    calls = []
    result = HELPER.dispatch_lintable_source(path, calls.append)
    assert result.extraction.status == "no_vba"
    assert result.extraction.source is None
    assert result.analysis is None
    assert calls == []


@pytest.mark.parametrize("dump, reason", [
    ("CodeBehindForm = True\nOption Explicit\n", "malformed CodeBehindForm boundary"),
    ("Version = 20\nOption Explicit\n", "VBA-like text has no supported boundary"),
    ("CodeBehindForm\nBegin Form\nEnd\n", "boundary does not start with recognizable VBA"),
    ("CodeBehindForm\n' empty\n", "boundary does not start with recognizable VBA"),
    ('Attribute VB_Name = "First"\nAttribute VB_Name = "Second"\nOption Explicit\n',
     "multiple VB_Name boundaries"),
])
def test_unresolved_dump_never_reaches_analyzer(tmp_path, dump, reason):
    path = tmp_path / "form.txt"
    path.write_text(dump, encoding="utf-8")
    calls = []
    result = HELPER.dispatch_lintable_source(path, calls.append)
    assert result.extraction.status == "unresolved"
    assert reason in result.extraction.reason
    assert result.extraction.source is None
    assert result.analysis is None
    assert calls == []


@pytest.mark.parametrize("newline", ["\n", "\r\n"])
def test_ready_dispatch_receives_extracted_source(tmp_path, newline):
    path = tmp_path / "form.txt"
    code = "Option Explicit" + newline
    path.write_bytes(("Version = 20" + newline + "CodeBehindForm" + newline + code).encode("utf-8"))
    calls = []

    def analyze(source):
        calls.append(source)
        return {"accepted": True}

    result = HELPER.dispatch_lintable_source(path, analyze)
    assert calls == [code]
    assert result.analysis == {"accepted": True}


@pytest.mark.parametrize("suffix", [".bas", ".cls", ".frm", ".dcm"])
@pytest.mark.parametrize("encoding", ["utf-8-sig", "cp932"])
def test_native_exports_keep_source_and_supported_encodings(tmp_path, suffix, encoding):
    path = tmp_path / ("Module1" + suffix)
    code = "Option Explicit\n' 日本語\n"
    path.write_bytes(code.encode(encoding))
    result = HELPER.extract_source_file(path)
    assert result.status == "ready"
    assert result.kind == "native_vba_export"
    assert result.source == code


def test_unsupported_extension_does_not_read_or_dispatch(tmp_path):
    calls = []
    result = HELPER.dispatch_lintable_source(tmp_path / "database.accdb", calls.append)
    assert result.extraction.status == "unresolved"
    assert result.extraction.kind == "unsupported"
    assert calls == []
