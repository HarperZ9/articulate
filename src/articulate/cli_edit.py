"""Options the editing commands share: plan, submit, judge, fix and polish.

articulate.cli registers the commands and calls these helpers, so the option
code lives in one place and the core command line stays small.

  --allow-change KINDS  protected change kinds the edit may make (plan, fix,
                        polish). Each accepted change is reported.
"""
from . import edit_options


def add_arguments(parser, cmd):
    """Register the shared editing options for one subcommand."""
    if cmd in ("plan", "fix", "polish"):
        parser.add_argument(
            "--allow-change", default=None, metavar="KINDS",
            help="comma-separated protected change kinds the edit may make, reported in "
                 "allowed_changes: " + ", ".join(edit_options.ALLOWABLE))


def edit_kwargs(args):
    """Keyword options for host_edit.edit_plan or editing.run_edit. Empty when
    no option is set, so the call is the same as before these options existed."""
    allow = edit_options.parse_allow(getattr(args, "allow_change", None))
    return {"allow_change": allow} if allow else {}
