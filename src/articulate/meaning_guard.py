"""Conservative lexical preservation checks, not a proof of semantic equivalence.

Paragraph boundaries and ordered protected spans must survive. If alignment is
ambiguous the whole document is retained; otherwise only affected paragraphs
are retained. No model or network is used here.
"""
import hashlib
import re


_MATH = re.compile(
    r'\\begin\{(equation|align|gather|multline|eqnarray|split|theorem|lemma|proof|definition|proposition|corollary|claim)\*?\}.*?\\end\{\1\*?\}'
    r'|\$\$.*?\$\$|\\\[.*?\\\]|\\\(.*?\\\)|(?<!\\)\$(?:\\.|[^$\\])*\$', re.S)
_TAG_BODY = r'''(?:[^>"']|"[^"]*"|'[^']*')*'''
_HTML = re.compile(r'<!--.*?-->|<(?P<opaque>script|style|pre|code)\b' + _TAG_BODY +
                   r'>.*?</(?P=opaque)\s*>|<![^>]*>|</?[A-Za-z]' + _TAG_BODY + r'>', re.S | re.I)
_PATTERNS = [
    ('code', re.compile(r'```.*?```|~~~.*?~~~|(`+)([^`]|(?!\1)`)*?\1', re.S)),
    ('code', re.compile(r'(?m)^(?: {4}|\t)[^\n]+')),
    ('math', _MATH),
    ('url', re.compile(r'(?:https?://|ftp://|mailto:|www\.)[^\s<>\]"\u201d]+', re.I)),
    # Greedy through the last close parenthesis: conservatively includes nested
    # targets and any intervening same-line prose rather than truncating a URL.
    ('link', re.compile(r'\]\([^\n]*\)|\[[^\]\n]*\]\[[^\]\n]*\]|(?m:^\s*\[[^\]\n]+\]:[^\n]+)')),
    # Bracket text may be a shortcut reference; keep it even when no definition
    # occurs in this paragraph (definitions may appear elsewhere in a document).
    ('link', re.compile(r'\[[^\]\n]+\]')),
    ('citation', re.compile(r'\[(?:\d[^\]\n]*|\^[^\]\n]+|@[^\]\n]+)\]|\\(?:cite\w*|ref|eqref)\*?(?:\[[^\]]*\])?\{[^}]*\}|\([^()\n]*[A-Z][^()\n]*\b(?:19|20)\d{2}[a-z]?[^()\n]*\)')),
    ('quote', re.compile(r'"(?:\\.|[^"\\])*"|\u201c[^\u201d]*\u201d|\u2018[^\u2019]*\u2019|(?<!\w)\x27[^\x27\n]+\x27(?!\w)', re.S)),
    # CommonMark permits lazy continuation without a leading >. Protect the
    # entire quote paragraph, conservatively including such following lines.
    ('quote', re.compile(r'(?m)^[ \t]*>[^\n]*(?:\n(?![ \t]*\r?$)[^\n]+)*')),
    ('number', re.compile(r'[+-]?\d+(?:[.,:/\-]\d+)*(?:\s?%|[eE][+-]?\d+)?')),
    ('number-range', re.compile(r'\d+(?:[.,]\d+)*(?:[A-Za-z%]+)?[ \t]*[\u2013\u2014-][ \t]*\d+(?:[.,]\d+)*(?:[A-Za-z%]+)?')),
    ('quantity', re.compile(r'\d+(?:[.,]\d+)*(?:[A-Za-z\u00b5\u03bc\u00b0%]+|[ \t]+(?:kg|mg|g|km|cm|mm|m|ml|mL|L|Hz|kHz|MHz|GHz|ms|s|W|kW|V|A|K|\u00b0C|\u00b0F)\b)')),
]
_PARAGRAPH = re.compile(r'(\r?\n[ \t]*\r?\n(?:[ \t]*\r?\n)*)')
_TOKEN = re.compile(r'\u2983ARTICULATE_[^\u2984]*\u2984')


def protected_spans(text, is_html=False, is_tex=False):
    """Return exact spans; overlaps are intentional (a citation can contain numbers)."""
    patterns = _PATTERNS + ([('html', _HTML)] if is_html else [])
    spans = [{'kind': kind, 'start': m.start(), 'end': m.end(), 'text': m.group()}
             for kind, pattern in patterns for m in pattern.finditer(text)]
    return sorted(spans, key=lambda s: (s['start'], s['end'], s['kind']))


def _signature(text, is_html=False, is_tex=False):
    out = {}
    for span in protected_spans(text, is_html, is_tex):
        out.setdefault(span['kind'], []).append(span['text'])
    return out


def _refusal(index, reasons):
    return {'paragraph': index, 'reasons': reasons}


def guard_rewrite(original, rewrite, is_html=False, is_tex=False):
    """Accept safe paragraphs, retaining originals wherever protected spans differ."""
    if original == rewrite:
        return {'text': original, 'refused': []}
    if original.strip() and not rewrite.strip():
        return {'text': original, 'refused': [_refusal(None, ['empty rewrite'])]}
    old, new = _PARAGRAPH.split(original), _PARAGRAPH.split(rewrite)
    if len(old) != len(new):
        return {'text': original, 'refused': [_refusal(None, ['paragraph alignment changed'])]}
    refused = []
    for i in range(0, len(old), 2):
        before = _signature(old[i], is_html, is_tex)
        after = _signature(new[i], is_html, is_tex)
        reasons = [kind + ' protected spans changed' for kind in sorted(set(before) | set(after))
                   if before.get(kind, []) != after.get(kind, [])]
        if reasons:
            new[i] = old[i]
            refused.append(_refusal(i // 2, reasons))
    # A multiline span might cross a paragraph boundary. Recheck the full result.
    candidate = ''.join(new)
    if _signature(original, is_html, is_tex) != _signature(candidate, is_html, is_tex):
        return {'text': original, 'refused': refused + [_refusal(None, ['cross-paragraph protected spans changed'])]}
    return {'text': candidate, 'refused': refused}


def mask_text(text, is_html=False, is_tex=False):
    """Mask HTML and math using input-specific tokens that cannot collide with input."""
    spans = [s for s in protected_spans(text, is_html, is_tex)
             if (s['kind'] == 'math' and is_tex) or (s['kind'] == 'html' and is_html)]
    # Long outer spans win over overlapping inner spans.
    spans.sort(key=lambda s: (s['start'], -s['end']))
    selected, end = [], -1
    for s in spans:
        if s['start'] >= end:
            selected.append(dict(s))
            end = s['end']
    prefix = hashlib.sha256(text.encode('utf-8')).hexdigest()[:16]
    while 'ARTICULATE_' + prefix in text:
        prefix += '_'
    chunks, end = [], 0
    for i, s in enumerate(selected):
        s['token'] = '\u2983ARTICULATE_' + prefix + '_' + str(i) + '\u2984'
        chunks.extend((text[end:s['start']], s['token']))
        end = s['end']
    chunks.append(text[end:])
    return ''.join(chunks), selected


def restore_masks(original, rewrite, is_html=False, is_tex=False):
    """Require each mask once, in its original paragraph and order, before restoring."""
    if 'ARTICULATE_' not in rewrite:
        return guard_rewrite(original, rewrite, is_html, is_tex)
    masked, masks = mask_text(original, is_html, is_tex)
    if not masks:
        return guard_rewrite(original, rewrite, is_html, is_tex)
    old, new = _PARAGRAPH.split(masked), _PARAGRAPH.split(rewrite)
    if len(old) != len(new):
        return {'text': original, 'refused': [_refusal(None, ['mask paragraph alignment changed'])]}
    refused = []
    for i in range(0, len(old), 2):
        if _TOKEN.findall(old[i]) != _TOKEN.findall(new[i]):
            new[i] = old[i]
            refused.append(_refusal(i // 2, ['mask missing, duplicated, changed or reordered']))
    restored = ''.join(new)
    for s in masks:
        restored = restored.replace(s['token'], s['text'])
    checked = guard_rewrite(original, restored, is_html, is_tex)
    checked['refused'] = refused + checked['refused']
    return checked
