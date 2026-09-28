"""Stateless host editing and deterministic fallback, using only local checks.

The plan token binds content and settings, not caller identity or authority. It
is an integrity checksum, not a signature; callers may generate their own plans.
"""
import base64
from collections import Counter
import hashlib
import hmac
import json
import re

from . import detector, modes, profiles, prompts
from .meaning_guard import guard_rewrite, mask_text, protected_spans, restore_masks


def _canonical(value):
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(',', ':'), allow_nan=False)


def _hash(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def _settings(mode, profile, goal, is_html, is_tex):
    if goal not in ('fix', 'polish', 'judge'):
        raise ValueError('goal must be fix, polish or judge')
    if mode and profile is not None:
        raise ValueError('choose mode or profile, not both')
    prof = modes.load(mode) if mode else (profiles.load(profile) if isinstance(profile, str)
                                         else profile if profile is not None else profiles.load(profiles.DEFAULT))
    if not isinstance(prof, dict):
        raise ValueError('profile must be a name or object')
    # Normalize tuples to JSON lists so the digest is stable across processes.
    return json.loads(_canonical({'schema': 'articulate/edit-plan/v1', 'mode': mode,
                                 'profile': prof, 'goal': goal, 'is_html': bool(is_html),
                                 'is_tex': bool(is_tex), 'ruleset': detector.ruleset_fingerprint()}))


def _token(text, settings):
    raw = _canonical(settings)
    encoded = base64.urlsafe_b64encode(raw.encode('utf-8')).decode('ascii').rstrip('=')
    return encoded + '.' + _hash(_canonical({'original': text, 'settings': settings}))


def _verify(text, plan_id):
    try:
        if not isinstance(plan_id, str) or len(plan_id) > 100000:
            raise ValueError('invalid plan token')
        encoded, digest = plan_id.rsplit('.', 1)
        settings = json.loads(base64.b64decode(encoded + '=' * (-len(encoded) % 4), altchars=b'-_', validate=True))
        if not isinstance(settings, dict) or settings.get('schema') != 'articulate/edit-plan/v1':
            raise ValueError('unknown plan schema')
        if not hmac.compare_digest(_token(text, settings), plan_id):
            raise ValueError('plan does not match original text or settings')
        if settings.get('ruleset') != detector.ruleset_fingerprint():
            raise ValueError('plan ruleset changed; request a new plan')
        required = {'schema', 'mode', 'profile', 'goal', 'is_html', 'is_tex', 'ruleset'}
        if set(settings) != required or settings['goal'] not in ('fix', 'polish', 'judge'):
            raise ValueError('invalid plan settings')
        if not isinstance(settings['profile'], dict) or any(type(settings[k]) is not bool for k in ('is_html', 'is_tex')):
            raise ValueError('invalid plan settings')
        return settings
    except (TypeError, KeyError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError('invalid plan token') from exc


def _findings(result):
    return [dict(f, reason=f['label']) for tier in ('high', 'medium', 'low') for f in result[tier]]


def _summary(findings):
    return '\n'.join('L{line} [{tier} {category}] {reason}: {snippet}'.format(**f) for f in findings) or 'No mechanical findings.'


def edit_plan(text, mode=None, profile=None, goal='fix', is_html=False, is_tex=False):
    settings = _settings(mode, profile, goal, is_html, is_tex)
    before = detector.check_text(text, profile=settings['profile'])
    findings = _findings(before)
    delta = settings['profile'].get('editor', {}).get('standard_delta', '')
    instr = (prompts.judge_instructions(_summary(findings), delta) if goal == 'judge'
             else prompts.rewrite_instructions(_summary(findings), is_html=is_html, standard_delta=delta))
    masked, masks = mask_text(text, is_html, is_tex)
    return {'ok': True, 'status': 'host_edit_required', 'backend': 'host', 'model': None, 'attempts': [],
            'goal': goal, 'profile': settings['profile'], 'mode': mode,
            'is_html': bool(is_html), 'is_tex': bool(is_tex), 'plan_id': _token(text, settings),
            'text': text, 'masked_text': masked, 'masks': masks, 'instructions': instr,
            'protected_spans': protected_spans(text, is_html, is_tex),
            'findings_before': findings, 'gate_before': before['gate'], 'gate': before['gate'],
            'instruction': 'Use these instructions and masked_text to produce a rewrite (or assessment for judge), then call edit_submit with the original text, result and plan_id.',
            'quality_instructions': prompts.quality_instructions() if goal == 'polish' else None,
            'quality_status': 'unassessed',
            'quality_scores_format': {'before': {q: 'integer 1..5' for q in prompts.QUALITIES},
                                      'after': {q: 'integer 1..5' for q in prompts.QUALITIES}} if goal == 'polish' else None,
            'does_not_prove': 'Protected-span preservation is not semantic equivalence or factual correctness.'}


def _quality(scores):
    if scores is None:
        return 'unassessed'
    if not isinstance(scores, dict):
        raise ValueError('scores must contain before and after assessments')
    for when in ('before', 'after'):
        if not isinstance(scores.get(when), dict) or any(type(scores[when].get(k)) is not int or not 1 <= scores[when][k] <= 5 for k in prompts.QUALITIES):
            raise ValueError('scores must supply all five integer qualities from 1 to 5 before and after')
    return 'regressed' if any(scores['after'][k] < scores['before'][k] for k in prompts.QUALITIES) else 'host_assessed_no_regression'


def _result(original, accepted, settings, refused, backend, model, quality_status='unassessed', scores=None):
    before = detector.check_text(original, profile=settings['profile'])
    after = detector.check_text(accepted, profile=settings['profile'])
    bf, af = _findings(before), _findings(after)
    bc, ac = Counter(f['rule_id'] for f in bf), Counter(f['rule_id'] for f in af)
    deltas = [{'rule_id': rule, 'before': bc[rule], 'after': ac[rule], 'delta': ac[rule] - bc[rule]}
              for rule in sorted(set(bc) | set(ac))]
    receipt = {'schema': 'articulate/editor-receipt/v1', 'backend': backend, 'model': model, 'attempts': [],
               'original_sha256': 'sha256:' + _hash(original), 'text_sha256': 'sha256:' + _hash(accepted),
               'ruleset_version': settings['ruleset'], 'settings': settings,
               'gate_before': before['gate'], 'gate_after': after['gate'], 'rule_deltas': deltas,
               'quality_status': quality_status, 'scores': scores,
               'does_not_prove': 'A lexical guard and detector gate do not prove semantic equivalence, quality or factual correctness. Host scores are supplied assessments, not independent measurements.'}
    return {'ok': True, 'text': accepted, 'goal': settings['goal'], 'backend': backend, 'model': model,
            'attempts': [], 'gate_before': before['gate'], 'gate_after': after['gate'], 'gate': after['gate'],
            'findings_before': bf, 'findings_after': af, 'remaining_findings': af,
            'rule_deltas': deltas, 'refused': refused, 'receipt': receipt,
            'quality_status': quality_status, 'scores': scores}


def edit_submit(text, rewrite, plan_id, scores=None, model=None):
    settings = _verify(text, plan_id)
    if not isinstance(rewrite, str):
        raise ValueError('rewrite must be text')
    if settings['goal'] == 'judge':
        out = _result(text, text, settings, [], 'host', model)
        out['assessment'] = rewrite
        return out
    guarded = restore_masks(text, rewrite, settings['is_html'], settings['is_tex'])
    accepted, refused = guarded['text'], guarded['refused']
    quality = _quality(scores)
    if settings['goal'] == 'polish':
        before = detector.check_text(text, profile=settings['profile'])
        after = detector.check_text(accepted, profile=settings['profile'])
        reasons = []
        if quality == 'regressed':
            reasons.append('quality scores regressed')
        if accepted != text and after['gate'] != 'ok':
            reasons.append('polish candidate detector gate is blocked')
        required = set(settings['profile'].get('editor', {}).get('require_fix', []))
        if required & {f['category'] for f in after['low']} - {f['category'] for f in before['low']}:
            reasons.append('required advisory regressed')
        if reasons:
            accepted = text
            refused.append({'paragraph': None, 'reasons': reasons})
    if refused and quality == 'host_assessed_no_regression':
        quality = 'unassessed_after_guard'
    return _result(text, accepted, settings, refused, 'host', model, quality, scores)


def deterministic_edit(text, mode=None, profile=None, goal='fix', is_html=False, is_tex=False):
    settings = _settings(mode, profile, goal, is_html, is_tex)
    candidate = text
    prof = settings['profile']
    if goal != 'judge' and prof.get('slop') != 'off' and prof.get('editor', {}).get('run_fix_by_default', True):
        # Transform only unprotected text. A final common guard also checks the result.
        spans = sorted(protected_spans(text, is_html, is_tex), key=lambda s: (s['start'], -s['end']))
        chunks, end = [], 0
        def transform(prose):
            if prof.get('no_em_dash', True):
                prose = re.sub(r'[ \t]*\u2014[ \t]*|[ \t]+\u2013[ \t]+', ', ', prose)
            # Internal doubled spaces only; indentation and Markdown line breaks stay.
            return re.sub(r'(?<=\S)[ \t]{2,}(?=\S)', ' ', prose)
        for span in spans:
            if span['start'] >= end:
                chunks.extend((transform(text[end:span['start']]), text[span['start']:span['end']]))
                end = span['end']
        chunks.append(transform(text[end:]))
        candidate = ''.join(chunks)
    checked = guard_rewrite(text, candidate, is_html, is_tex)
    if goal == 'polish' and detector.check_text(text, profile=prof)['gate'] == 'ok' and detector.check_text(checked['text'], profile=prof)['gate'] != 'ok':
        checked = {'text': text, 'refused': [{'paragraph': None, 'reasons': ['detector gate regressed']}]}
    out = _result(text, checked['text'], settings, checked['refused'], 'none', None)
    out['instruction'] = 'For a model edit, use edit_plan/edit_submit or configure a reachable model backend.'
    if goal == 'judge':
        out['assessment'] = _summary(out['findings_before'])
    return out
