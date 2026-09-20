#!/usr/bin/env python3
"""Conservatively extract VBA from an Access SaveAsText mixed dump."""

import argparse
from collections import namedtuple
from pathlib import Path
import re


NATIVE_VBA_EXTENSIONS = frozenset({".bas", ".cls", ".frm", ".dcm"})
ExtractionResult = namedtuple("ExtractionResult", "status kind source reason")
DispatchResult = namedtuple("DispatchResult", "extraction analysis")


_VB_NAME = re.compile(r'^\s*Attribute\s+VB_Name\s*=\s*"[^"]+"\s*$', re.IGNORECASE)
_VBA_OPENING = re.compile(
    r"^\s*(?:Attribute\s+VB_|Option\s+"
    r"(?:Compare|Explicit|Base|Private\s+Module)\b|"
    r"(?:(?:Public|Private|Friend|Static)\s+)?"
    r"(?:Sub|Function|Property\s+(?:Get|Let|Set)|Dim|Const|Type|Enum|Declare|Event)\b)",
    re.IGNORECASE,
)


def _read_source(path):
    raw = path.read_bytes()
    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        return raw.decode("cp932")


def _unresolved(reason, kind="access_saveastext_mixed_dump"):
    return ExtractionResult(status="unresolved", kind=kind, source=None, reason=reason)


def extract_access_saveastext(text):
    """Extract a uniquely located VBA tail from a SaveAsText mixed dump.

    The supported boundaries are an exact ``CodeBehindForm`` line or a unique
    ``Attribute VB_Name = "..."`` module attribute. Anything that resembles a
    boundary without satisfying those rules remains unresolved.
    """

    text = text[1:] if text.startswith("\ufeff") else text
    lines = text.splitlines(keepends=True)
    code_markers = [index for index, line in enumerate(lines) if line.strip().casefold() == "codebehindform"]
    name_attributes = [index for index, line in enumerate(lines) if _VB_NAME.fullmatch(line.rstrip("\r\n"))]

    first_code_marker = code_markers[0] if code_markers else None
    if len(name_attributes) > 1 and (
        first_code_marker is None or min(name_attributes) < first_code_marker
    ):
        return _unresolved("source extraction unresolved: multiple VB_Name boundaries")

    first_name_attribute = name_attributes[0] if len(name_attributes) == 1 else None
    if first_code_marker is not None and (
        first_name_attribute is None or first_code_marker < first_name_attribute
    ):
        boundary = first_code_marker
        start = boundary + 1
    elif first_name_attribute is not None:
        boundary = first_name_attribute
        start = boundary
    else:
        boundary = None

    header_limit = boundary if boundary is not None else len(lines)
    malformed_code_markers = [
        line for line in lines[:header_limit]
        if line.strip().casefold().startswith("codebehindform")
        and line.strip().casefold() != "codebehindform"
    ]
    if malformed_code_markers:
        return _unresolved("source extraction unresolved: malformed CodeBehindForm boundary")

    if boundary is None:
        vba_like_lines = [
            line for line in lines
            if _VBA_OPENING.match(line) and not line.lstrip().casefold().startswith("attribute vb_")
        ]
        if vba_like_lines:
            return _unresolved("source extraction unresolved: VBA-like text has no supported boundary")
        return ExtractionResult(
            status="no_vba",
            kind="access_saveastext_mixed_dump",
            source=None,
            reason="mixed dump contains no VBA code section",
        )

    section_lines = lines[start:]
    meaningful = [
        line for line in section_lines
        if line.strip() and not line.lstrip().startswith("'") and not line.lstrip().casefold().startswith("rem ")
    ]
    if not meaningful or not _VBA_OPENING.match(meaningful[0]):
        return _unresolved("source extraction unresolved: boundary does not start with recognizable VBA")

    return ExtractionResult(
        status="ready",
        kind="access_saveastext_mixed_dump",
        source="".join(section_lines),
        reason="VBA code section extracted from mixed dump",
    )


def extract_source_file(path):
    source_path = Path(path)
    suffix = source_path.suffix.casefold()
    if suffix in NATIVE_VBA_EXTENSIONS:
        return ExtractionResult(
            status="ready",
            kind="native_vba_export",
            source=_read_source(source_path),
            reason="native VBA export",
        )
    if suffix == ".txt":
        return extract_access_saveastext(_read_source(source_path))
    return _unresolved(
        f"source extraction unresolved: unsupported source extension {source_path.suffix or '<none>'}",
        kind="unsupported",
    )


def dispatch_lintable_source(path, analyzer):
    """Call an analyzer only when extraction produced pure, lintable VBA."""

    extraction = extract_source_file(path)
    if extraction.status != "ready" or extraction.source is None:
        return DispatchResult(extraction=extraction, analysis=None)
    return DispatchResult(extraction=extraction, analysis=analyzer(extraction.source))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", type=Path, help="write extracted VBA to a controlled source file")
    args = parser.parse_args()

    result = extract_source_file(args.source)
    if result.status != "ready" or result.source is None:
        print(result.reason)
        return 2 if result.status == "no_vba" else 3

    if args.output:
        with args.output.open("w", encoding="utf-8", newline="") as output:
            output.write(result.source)
    else:
        print(result.source, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
