"""A4: `unsupported-authority` reads every citation style and the writer's own data.

The rule's reason is that an appeal to unnamed studies gives the reader no
source to check. A marker in AMA, Vancouver, ICMJE, MLA, Chicago notes, the
Bluebook, Pandoc, LaTeX or a CS alpha key gives the reader a source, and a
figure reference points at the paper's own evidence. A four-digit count such as
"in 1200 patients" is not a year in citation position, so it no longer silences
the rule. The rule stays MEDIUM where no marker is present.

The lines are the proposals file's control lines (A4-c1 to A4-f3). They measure
nothing about fairness.
"""
import pytest

from articulate import rule_reasons
from controls import assert_passes, cats, run

A4_PASS = [
    ("c1", "Studies have shown that statins lower LDL cholesterol.12", "a.md",
     ("flavored", "research", "essay", "academic/argue")),
    ("c2", "Studies have shown that statins lower LDL cholesterol\u00b9\u00b2.", "a.md",
     ("research", "essay", "academic/argue")),
    ("c3", "Studies have shown that sepsis mortality remains high (12).", "a.md",
     ("research", "essay", "academic/argue")),
    ("c4", "Research suggests the trope recurs across the period (Jones 118).", "a.md",
     ("flavored", "essay")),
    ("c5", "Research shows that the archive was rebuilt twice.[^5]\n\n"
           "[^5]: J. Smith, Archives (London, 1998), 12.\n", "a.md", ("flavored", "essay")),
    ("c6", "Research shows that circuits split on this question, see Smith v. Jones, "
           "998 F.3d 101 (7th Cir. 2021).", "a.md", ("legal", "legal/argue", "essay")),
    ("c7", "Studies have shown that the bound is tight [@smith].", "a.md",
     ("research", "essay")),
    ("c8", "The proof is short.\n\nStudies have shown that the bound is tight "
           "\\cite{smithA}.\n", "a.tex", ("research", "essay")),
    ("c9", "As Smith and Jones (2019) report, research shows that attendance fell.",
     "a.md", ("flavored", "essay")),
    ("c10", "Our data show that knockdown reduced growth (Fig. 2B).", "a.md",
     ("research", "essay", "academic/argue")),
    ("c11", "Data shows a rise in cases, according to the county health department.",
     "a.md", ("journalism", "journalism/explain")),
    ("c12", "Studies have shown that the bound is tight [Smi20].", "a.md",
     ("research", "essay")),
]


@pytest.mark.parametrize("cid,text,name,runs", A4_PASS, ids=[c[0] for c in A4_PASS])
def test_a4_a_cited_claim_does_not_block(cid, text, name, runs):
    assert_passes(text, runs, name)


@pytest.mark.parametrize("marker", [
    "<sup>12</sup>", "^12^", "(12, 13)", "(12-15)", "(ref. 7)", "[12]", "[1, 3]",
    "\\citep{smith}", "\\citet{smith}", "\\footnote{Smith 2019.}", "[@smith2019]",
    "(Smith, 2019)", "[2021] UKSC 5", "410 U.S. 113", "(Smith et al. 2019)",
])
def test_a4_each_marker_form_anchors_the_claim(marker):
    r = run(f"Studies have shown that the effect is small {marker}.", "essay")
    assert "unsupported-authority" not in cats(r, "MEDIUM"), marker


@pytest.mark.parametrize("anchor", ["(Table 2)", "(Figure 3)", "(Supplementary Table S1)",
                                    "(P = .001)", "(95% CI, 0.4 to 0.9)"])
def test_a4_own_data_with_a_figure_or_statistic_is_the_writers_evidence(anchor):
    r = run(f"These data show that the effect is small {anchor}.", "essay")
    assert "unsupported-authority" not in cats(r, "MEDIUM"), anchor


def test_a4_a_figure_reference_does_not_anchor_an_appeal_to_other_studies():
    r = run("Studies have shown that the effect is small (Figure 3).", "essay")
    assert "unsupported-authority" in cats(r, "MEDIUM")


@pytest.mark.parametrize("text", [
    "Studies have shown that screen time harms sleep.",
    "Studies have shown that the drug works in 1200 patients.",
    "Firstly, studies have shown that students learn better at home.",
    "Experts agree that the plan will fail, according to experts.",
])
def test_a4_an_appeal_with_no_marker_still_flags_medium(text):
    assert "unsupported-authority" in cats(run(text, "flavored"), "MEDIUM")
    assert run(text, "essay")["gate"] == "blocked"


def test_a4_a_marker_in_the_next_sentence_does_not_anchor_this_one():
    r = run("Studies have shown that screen time harms sleep. Smith (2019) disagrees.",
            "essay")
    assert "unsupported-authority" in cats(r, "MEDIUM")


def test_a4_the_note_names_both_repairs():
    reason, _source = rule_reasons.reason_for("unsupported-authority")
    assert "cite the source" in reason and "your own view" in reason
