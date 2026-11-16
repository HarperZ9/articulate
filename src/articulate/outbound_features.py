"""Measures of a short message for the outbound check: the nine measured tells
of model-written prose, plus the email and post shapes the author named.

The nine tells come from a paired method: human pieces rewritten by a model
from a description, at the same length, then compared pair by pair. Model
rewrites carry fewer nouns from one sentence to the next, more varied words,
fewer words per clause, shorter sentences, fewer proper names, fewer repeated
three-word runs, a narrower band of word frequencies, fewer numbers, and a
new abstract noun in each sentence where the human gave a checkable fact.
None counts alone. The baseline behind them is English news and web prose,
which is why the check compares against references and not against a norm.

measure(text) returns one value per feature, or None where the text is too
short for that feature to mean anything. locate(text, feature, direction)
returns the line that pushes the value furthest in that direction.
Standard library only.
"""
import re
from statistics import mean, pstdev

from . import corpus_features as cf
from .wordlists import FUNCTION_WORDS

GREETING = re.compile(r"^\s*(?:hi|hey|hello|dear|morning|evening|yo|hiya)\b[^,\n.!]{0,40}[,!.]?\s*",
                      re.I)
SIGNOFF_WORDS = ("cheers", "best", "best regards", "regards", "kind regards", "thanks",
                 "thank you", "many thanks", "sincerely", "warmly", "warm regards", "all the best",
                 "talk soon", "take care", "thanks again", "with thanks")
_SO = "|".join(re.escape(w) for w in sorted(SIGNOFF_WORDS, key=len, reverse=True))
_NAME = r"[A-Z][\w'-]*(?:\s+[A-Z][\w'-]*)?"
_NAME_LINE = re.compile(r"^" + _NAME + r"\s*$")
_SIGNOFF_LINE = re.compile(r"^((?i:" + _SO + r"))\s*[,.!]?(?:\s+" + _NAME + r")?\s*$")
_INLINE_TAIL = re.compile(r"(?<=[.!?])\s+(?:((?i:" + _SO + r"))\s*[,.!]?\s+)?(" + _NAME + r")\s*$")
VAGUE = re.compile(r"(?i)\b(?:many|several|various|numerous|countless|multiple|a number of|"
                   r"a range of|a variety of|a handful of|a few|some of)\b")
ABSTRACT = re.compile(r"(?i)\b[a-z]{3,}(?:tion|sion|ment|ness|ity|ance|ence|ism|ship|ure|ency|"
                      r"ancy|ology)s?\b")
SOFTENERS = re.compile(r"(?i)\b(?:one small thing|small thing|quick note|quick question|"
                       r"just wanted to|just a heads up|heads up|i noticed|worth noting|"
                       r"minor point|small note|no worries|hope this helps|if helpful|"
                       r"happy to|feel free|for what it'?s worth|just to flag|to be clear)\b")
ASKS = re.compile(r"(?i)\b(?:would you|could you|can you|let me know|i'?d like to|i'?d love|"
                  r"i'?d be glad|i'?d be happy|would it be|are you open|if you'?re open|"
                  r"with credit|would you be|do you have time|any chance)\b")
STANCE = re.compile(r"(?i)\b(?:wrong|ethics|ethical|evil|enemy|delusion\w*|propaganda|fallacy|"
                    r"disingenu\w*|grifter|shill|despicable|psychopath|bullshit|shit\w*|fuck\w*|"
                    r"damn|hell|crap\w*|ass|insane|garbage|nonsense|ridiculous|absurd|"
                    r"agreed?|disagree|straight up|honestly|bro|dude|man|nah|ain'?t|"
                    r"spot on|next level|best|worst)\b")
ABBREV = re.compile(r"(?i)\b(?:fyi|btw|tbh|imo|imho|idk|ngl|lol|lmao|gvmt|govt|bro|w/|b/c|"
                    r"thx|pls|plz|ya|yea|gonna|wanna|kinda|sorta|cuz)\b")
SURFACE = re.compile(r"\.\.+|(?<=\w)/(?=\w)|~|\*|&|\s>\s|\?\?|!!")
NUMBER = re.compile(r"\b\d[\d,.]*\b|(?i:\b(?:two|three|four|five|six|seven|eight|nine|ten|"
                    r"eleven|twelve|twenty|thirty|forty|fifty|hundred|thousand|million|"
                    r"dozen|half)\b)")
_ID = re.compile(r"\b(?:[A-Za-z]+-?\d+[A-Za-z\d]*|[A-Z]{2,}[a-z]?)\b")
_CLAUSE = re.compile(r"[,;:()–—]|\s-\s|\b(?:and|but|or|so|because|which|who|"
                     r"when|while|if|although|though|since|unless|whereas)\b", re.I)
OPENERS = ("thanks", "praise", "softener", "question", "agreement", "other")
_THANKS = re.compile(r"(?i)^\W*(?:thanks|thank you|many thanks|cheers for|appreciate)")
_PRAISE = re.compile(r"(?i)^\W*(?:great|love|lovely|beautiful|nice|wonderful|fantastic|amazing|"
                     r"really enjoyed|what a)\b")
_AGREE = re.compile(r"(?i)^\W*(?:got it|agreed|yes|yeah|yep|right|fair|true|exactly|ok|okay|"
                    r"sure|makes sense|straight up)\b")

# Minimum size of a text for each family of feature, so that one slash in a
# three-word post does not read as twenty per hundred words.
NL = "\n"
MIN_WORDS_RATE = 12
MIN_SENTENCES_PAIR = 2


def _tail(text):
    """(text without its closing lines, the sign-off word or None)."""
    lines = text.split(NL)
    if len(lines) > 1:
        if _NAME_LINE.match(lines[-1].strip()) and not _SIGNOFF_LINE.match(lines[-1].strip()):
            lines.pop()
        m = _SIGNOFF_LINE.match(lines[-1].strip()) if len(lines) > 1 else None
        if m:
            lines.pop()
            return NL.join(lines), m.group(1)
        return NL.join(lines), None
    m = _INLINE_TAIL.search(text)
    if m and len(m.group(2).split()) <= 2:
        return text[:m.start()], m.group(1)
    return text, None


def body(text):
    """(body text, line offset, greeting, signoff) with the salutation and the
    closing lines removed, whether the message is on one line or several."""
    text = text.replace("’", "'").replace("‘", "'").replace("\r\n", NL).strip(NL)
    joined, signoff = _tail(text.rstrip())
    greeting, offset = None, 0
    g = GREETING.match(joined)
    if g and (joined[:g.end()].rstrip()[-1:] in ",!" or NL in joined[:g.end()]
              or g.end() >= len(joined)):
        greeting = joined[:g.end()].strip()
        offset = joined[:g.end()].count(NL)
        joined = joined[g.end():]
    return joined.strip(), offset, greeting, signoff


def sentence_rows(text):
    """[(line, sentence)] for the message body, lines 1-based in the original text."""
    core, offset, _, _ = body(text)
    rows = []
    for b in cf.prose_blocks(core) or [{"text": core, "line_start": 1}]:
        for a, end in cf.sentence_bounds(b["text"]):
            s = b["text"][a:end]
            if cf.words(s):
                rows.append((b["line_start"] + offset + b["text"][:a].count("\n"), s))
    return rows


def _content(sentence):
    out = set()
    for w in cf.words(sentence):
        low = w.lower()
        if len(low) >= 3 and low not in FUNCTION_WORDS and not low.isdigit():
            out.add(low[:-1] if low.endswith("s") and len(low) > 4 else low)
    return out


def _names(sentence):
    toks = cf.words(sentence)
    named = [w for i, w in enumerate(toks) if i and w[:1].isupper() and w != "I"]
    return len(named) + len([w for w in _ID.findall(sentence) if not w[:1].isupper()])


def _clauses(sentence):
    parts = [p for p in _CLAUSE.split(sentence) if p and cf.words(p)]
    return [len(cf.words(p)) for p in parts] or [len(cf.words(sentence))]


def _mattr(tokens, window=20):
    if len(tokens) < 2:
        return None
    if len(tokens) <= window:
        return round(len(set(tokens)) / len(tokens), 3)
    ratios = [len(set(tokens[i:i + window])) / window for i in range(len(tokens) - window + 1)]
    return round(mean(ratios), 3)


def _cv(values):
    values = [v for v in values if v]
    if len(values) < 2:
        return None
    return round(pstdev(values) / mean(values), 3)


def _per_100(count, total, floor=MIN_WORDS_RATE):
    return round(count * 100 / total, 2) if total >= max(floor, 1) else None


def _opener(first):
    if first is None:
        return None
    for name, rx in (("thanks", _THANKS), ("praise", _PRAISE), ("softener", SOFTENERS),
                     ("agreement", _AGREE)):
        if rx.match(first) or (name == "softener" and SOFTENERS.match(first.strip())):
            return name
    return "question" if first.rstrip().endswith("?") else "other"


def _carry(sents):
    if len(sents) < MIN_SENTENCES_PAIR:
        return None
    pairs = list(zip(sents, sents[1:]))
    return round(sum(1 for a, b in pairs if _content(a) & _content(b)) / len(pairs), 3)


def _new_abstract(sents):
    seen, gained = set(), 0
    for s in sents:
        found = {w.lower() for w in ABSTRACT.findall(s)} - seen
        gained += bool(found)
        seen |= found
    return round(gained / len(sents), 3) if sents else None


def _trigram_repeat(tokens, floor=MIN_WORDS_RATE):
    grams = list(zip(tokens, tokens[1:], tokens[2:]))
    if len(grams) < max(floor, 1):
        return None
    counts = {}
    for g in grams:
        counts[g] = counts.get(g, 0) + 1
    return round(sum(n for n in counts.values() if n > 1) / len(grams), 3)


def measure(text, floor=MIN_WORDS_RATE):
    """Every feature of one message, as a number, a class name, or None. floor is
    the fewest words a rate is computed on; the line finder lowers it."""
    _, _, greeting, signoff = body(text)
    sents = [s for _, s in sentence_rows(text)]
    prose = " ".join(sents)
    tokens = [w.lower() for w in cf.words(prose)]
    n, k = len(tokens), len(sents)
    clauses = [c for s in sents for c in _clauses(s)]
    lengths = [len(w) for w in tokens if w.isalpha()]
    facts = len(NUMBER.findall(prose)) + sum(_names(s) for s in sents)
    lower_starts = sum(1 for s in sents if s.lstrip("\"'(*")[:1].islower())
    marks = len(SURFACE.findall(prose)) + len(ABBREV.findall(prose)) + lower_starts
    return {
        "noun_carry": _carry(sents),
        "vocab_variety": _mattr(tokens) if n >= floor else None,
        "words_per_clause": round(mean(clauses), 2) if clauses else None,
        "sentence_words": round(n / k, 2) if k else None,
        "proper_names_per_100": _per_100(sum(_names(s) for s in sents), n, floor),
        "repeated_trigram_share": _trigram_repeat(tokens, floor),
        "common_word_share": round(sum(t in FUNCTION_WORDS for t in tokens) / n, 3)
        if n >= floor else None,
        "word_length_spread": _cv(lengths) if n >= floor else None,
        "numbers_per_100": _per_100(len(NUMBER.findall(prose)), n, floor),
        "vague_quantity_per_100": _per_100(len(VAGUE.findall(prose)), n, floor),
        "new_abstract_share": _new_abstract(sents) if k >= MIN_SENTENCES_PAIR else None,
        "facts_per_sentence": round(facts / k, 2) if k else None,
        "clause_spread": _cv(clauses),
        "stance_per_100": _per_100(len(STANCE.findall(prose)), n, floor),
        "softener_per_100": _per_100(len(SOFTENERS.findall(prose)), n, floor),
        "ask_per_100": _per_100(len(ASKS.findall(prose)), n, floor),
        "surface_marks_per_100": _per_100(marks, n, floor),
        "semicolon_colon_per_100": _per_100(prose.count(";") + prose.count(":"), n, floor),
        "opener": _opener(sents[0] if sents else None),
        "signoff": "word" if signoff else "none",
        "greeting": "yes" if greeting else "no",
    }


CATEGORICAL = ("opener", "signoff", "greeting")
FEATURES = tuple(measure("One two three. Four five six."))
NUMERIC = tuple(f for f in FEATURES if f not in CATEGORICAL)
