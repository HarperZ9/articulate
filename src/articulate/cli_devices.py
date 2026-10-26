"""`articulate devices`: rhetorical devices in a text, where they are.

    articulate devices FILE ... [--json] [--speak | --ssml] [--only DEVICE,...]

Reads each file with articulate.devices and lists every device found with its
line and passage: antithesis, tricolon, anaphora, chiasmus, alliteration,
assonance, polysyndeton, asyndeton, anadiplosis, epizeuxis, isocolon, zeugma
and oxymoron. A device is a shape every kind of writer uses; the report names
where it is and never gates, and it says nothing about who wrote the text.
--speak prints a script to read aloud and --ssml the same script as SSML.
Exit code is 0 unless a file cannot be read.
"""
import json
import sys

from . import devices, speech
from .detector import binary_reason


def _read(path):
    with open(path, "rb") as fh:
        data = fh.read()
    reason = binary_reason(data, name=path)
    if reason:
        raise ValueError(f"{path}: {reason}")
    return data.decode("utf-8", errors="replace").replace("\r\n", "\n")


def cmd_devices(args):
    only = set(filter(None, (args.only or "").split(",")))
    unknown = only - set(devices.DEVICES)
    if unknown:
        print(f"[articulate] unknown device: {', '.join(sorted(unknown))}", file=sys.stderr)
        return 2
    payload = []
    for path in args.files:
        try:
            text = _read(path)
        except (OSError, ValueError) as exc:
            print(f"[articulate] {exc}", file=sys.stderr)
            return 2
        found = [f for f in devices.analyze(text)["findings"] if not only or f["device"] in only]
        for f in found:
            f["line"] = speech.line_of(text, f["start"])
        if args.speak:
            print(speech.script(found, text))
        elif args.ssml:
            print(speech.ssml(found, text))
        elif args.json:
            counts = {d: sum(1 for f in found if f["device"] == d) for d in devices.DEVICES}
            payload.append({"file": path, "counts": counts, "findings": found})
        else:
            print(f"{path}: {len(found)} device finding{'s' if len(found) != 1 else ''}")
            for f in found:
                detail = f" ({f['detail']})" if f.get("detail") else ""
                print(f"  {f['line']:>4}  {f['device']:<13}{detail}  {f['snippet'][:80]}")
    if args.json:
        print(json.dumps(payload if len(payload) != 1 else payload[0], ensure_ascii=False, indent=1))
    return 0


def register(sub):
    p = sub.add_parser("devices", help="find rhetorical devices and show where they are")
    p.add_argument("files", nargs="+", help="text files")
    p.add_argument("--only", help="comma-separated devices to report")
    out = p.add_mutually_exclusive_group()
    out.add_argument("--json", action="store_true", help="print findings as JSON")
    out.add_argument("--speak", action="store_true", help="print a script to read aloud")
    out.add_argument("--ssml", action="store_true", help="print the spoken script as SSML")
    p.set_defaults(corpus_handler=cmd_devices)
