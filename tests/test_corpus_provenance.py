"""Every text shipped in the corpus has a recorded source and a licence that
allows redistribution (PR 9, decision 9). An unknown licence is a reason to
remove a file, not to keep it."""
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
README = (ROOT / "corpus" / "README.md").read_text(encoding="utf-8")


def _rows():
    rows = {}
    for line in README.splitlines():
        m = re.match(r"\|\s*`control/([^`]+)`\s*\|(.*)\|(.*)\|\s*$", line)
        if m:
            rows[m.group(1)] = (m.group(2).strip(), m.group(3).strip())
    return rows


def test_every_control_text_is_listed_with_a_redistributable_licence():
    rows = _rows()
    files = sorted(p.name for p in (ROOT / "corpus" / "control").iterdir() if p.is_file())
    assert files and sorted(rows) == files
    for name, (_source, licence) in rows.items():
        assert licence.lower().startswith("public domain"), (name, licence)


def test_the_federal_control_records_its_source_url():
    federal = [(n, s) for n, (s, _lic) in _rows().items() if ".gov" in s]
    assert federal, "no United States federal government control text"
    for name, source in federal:
        assert re.search(r"https://www\.[a-z.]+\.gov/\S+", source), name
