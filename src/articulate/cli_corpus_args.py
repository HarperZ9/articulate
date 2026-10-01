"""Argument parsers for the series and voice verbs, kept apart from their
handlers so each file stays short."""


def _corpus(sub, run, handler, genres):
    p = sub.add_parser("corpus", help="review a series of documents together")
    p.add_argument("files", nargs="+")
    p.add_argument("--single", action="store_true", help="structural checks on one file")
    p.add_argument("--keep", help="file of phrases and headings you repeat on purpose")
    p.add_argument("--genre", choices=genres, default="essay")
    p.add_argument("--json", action="store_true")
    p.add_argument("--receipt", help="write a corpus receipt to this file")
    p.set_defaults(corpus_handler=run(handler))


def _voice(sub, run, handler):
    p = sub.add_parser("voice", help="learn, show, compare or delete your voice profile")
    vs = p.add_subparsers(dest="voice_cmd", required=True)
    learn = vs.add_parser("learn", help="build a profile from samples you name")
    learn.add_argument("samples", nargs="+")
    learn.add_argument("--name", required=True)
    learn.add_argument("--no-vocabulary", action="store_true",
                       help="leave the vocabulary field out of the profile")
    show = vs.add_parser("show", help="print every stored field in words")
    show.add_argument("name")
    show.add_argument("--json", action="store_true")
    compare = vs.add_parser("compare", help="place drafts against your measured range")
    compare.add_argument("drafts", nargs="+")
    compare.add_argument("--name", required=True)
    compare.add_argument("--json", action="store_true")
    delete = vs.add_parser("delete", help="remove a stored profile")
    delete.add_argument("name")
    vs.add_parser("list", help="list stored profiles")
    vs.add_parser("path", help="print the store folder")
    for parser in vs.choices.values():
        parser.add_argument("--dir", help="store folder (default: your local data folder)")
    p.set_defaults(corpus_handler=run(handler))


def _interview(sub, run, handler):
    p = sub.add_parser("interview", help="questions only you can answer, at their lines")
    p.add_argument("doc", nargs="?")
    p.add_argument("--voice", help="a stored voice profile name")
    p.add_argument("--dir", help="voice store folder")
    p.add_argument("--out", help="write a marked copy (or, with --collect, the cleaned text)")
    p.add_argument("--collect", help="a marked copy to read answers from")
    p.add_argument("--answers-out", help="with --collect, write the answers here")
    p.add_argument("--json", action="store_true")
    p.set_defaults(corpus_handler=run(handler))


def _restructure(sub, run, handler):
    p = sub.add_parser("restructure", help="propose moving limit and source lines to one section")
    p.add_argument("doc")
    p.add_argument("--out", help="write the proposal here; the input is never changed")
    p.add_argument("--anchors", choices=("footnote", "link"), default="footnote")
    p.add_argument("--json", action="store_true")
    p.set_defaults(corpus_handler=run(handler))


def _titles(sub, run, handler):
    p = sub.add_parser("titles", help="title families and questions for a series")
    p.add_argument("paths", nargs="*")
    p.add_argument("--titles", help="file with one title per line")
    p.add_argument("--answers", help="file with one answer per title, in order")
    p.add_argument("--json", action="store_true")
    p.set_defaults(corpus_handler=run(handler))


def add_parsers(sub, handlers, run, genres):
    _corpus(sub, run, handlers["corpus"], genres)
    _voice(sub, run, handlers["voice"])
    _interview(sub, run, handlers["interview"])
    _restructure(sub, run, handlers["restructure"])
    _titles(sub, run, handlers["titles"])
