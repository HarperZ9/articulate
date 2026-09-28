import importlib

import pytest


def guard():
    # Missing implementation is a visible assertion failure in the first red run.
    assert importlib.util.find_spec('articulate.meaning_guard'), 'meaning guard missing'
    return importlib.import_module('articulate.meaning_guard')


@pytest.mark.parametrize('old,new,kind', [
    ('We measured 14 samples.', 'We measured 15 samples.', 'number'),
    ('See https://example.org/a.', 'See https://example.org/b.', 'url'),
    ('The result [12] holds.', 'The result holds.', 'citation'),
    ('The result (Smith, 2025) holds.', 'The result (Jones, 2025) holds.', 'citation'),
    ('Use `run --fast` here.', 'Use `run --slow` here.', 'code'),
    ('She said "keep the data".', 'She said "drop the data".', 'quote'),
    ('She said ‘keep the data’.', 'She said ‘drop the data’.', 'quote'),
    ('We use $x < y$.', 'We use $x > y$.', 'math'),
    ('[Read](./a.md)', '[Read](./b.md)', 'link'),
])
def test_protected_content_refuses_changed_paragraph(old, new, kind):
    result = guard().guard_rewrite(old, new)
    assert result['text'] == old
    assert any(kind in reason for item in result['refused'] for reason in item['reasons'])


def test_guard_accepts_safe_paragraph_and_retains_unsafe_one():
    result = guard().guard_rewrite('We really measured 14 samples.\n\nWe really wait.',
                                   'We measured 15 samples.\n\nWe wait.')
    assert result['text'] == 'We really measured 14 samples.\n\nWe wait.'
    assert len(result['refused']) == 1


def test_resegmentation_cannot_bypass_guard():
    old = 'We measured 14 samples.\n\nThe count matters.'
    result = guard().guard_rewrite(old, 'We measured 15 samples. The count matters.')
    assert result['text'] == old
    assert result['refused']


def test_protected_order_cannot_change():
    old = 'We measured 14 successes and 3 failures.'
    assert guard().guard_rewrite(old, 'We measured 3 successes and 14 failures.')['text'] == old


def test_math_and_html_mask_restoration_and_corruption():
    g = guard()
    original = '<p>We really use $x < y$.</p>'
    masked, masks = g.mask_text(original, is_html=True, is_tex=True)
    assert '$x < y$' not in masked
    assert '<p>' not in masked
    assert masks
    good = g.restore_masks(original, masked.replace('really ', ''), is_html=True, is_tex=True)
    assert good['text'] == '<p>We use $x < y$.</p>'
    bad = g.restore_masks(original, masked.replace(masks[0]['token'], ''), is_html=True, is_tex=True)
    assert bad['text'] == original
    assert bad['refused']


def test_cross_paragraph_masks_cannot_be_moved():
    g = guard()
    old = 'We use $x$.\n\nWe use $y$.'
    masked, masks = g.mask_text(old, is_tex=True)
    candidate = masked.replace(masks[0]['token'], 'TEMP').replace(masks[1]['token'], masks[0]['token']).replace('TEMP', masks[1]['token'])
    assert g.restore_masks(old, candidate, is_tex=True)['text'] == old


@pytest.mark.parametrize('old,new', [
    ('The sample weighed 3kg.', 'The sample weighed 4kg.'),
    ('See https://en.wikipedia.org/wiki/Name_(thing).', 'See https://en.wikipedia.org/wiki/Name_(other).'),
    ('See https://example.org/name(foo)bar.', 'See https://example.org/name(foo)baz.'),
    ('<p title="a > b">Wait.</p>', '<p title="a > c">Wait.</p>'),
    ('<a title="a > b" href=/old>Wait.</a>', '<a title="a > b" href=/new>Wait.</a>'),
])
def test_protected_boundaries_cannot_hide_content_changes(old, new):
    assert guard().guard_rewrite(old, new, is_html=True)['text'] == old


def test_raw_restored_submission_is_accepted():
    old = '<p>We really use $x$.</p>'
    assert guard().restore_masks(old, '<p>We use $x$.</p>', is_html=True, is_tex=True)['text'] == '<p>We use $x$.</p>'


def test_raw_restored_submission_still_rejects_changed_math():
    old = '<p>We use $x$.</p>'
    assert guard().restore_masks(old, '<p>We use $y$.</p>', is_html=True, is_tex=True)['text'] == old


@pytest.mark.parametrize('old,new', [
    ('The sample weighed 3kg.', 'The sample weighed 3mg.'),
    ('The sample weighed 3 kg.', 'The sample weighed 3 mg.'),
    ('See [the guide][safe].\n\n[safe]: /a\n[evil]: /b', 'See [the guide][evil].\n\n[safe]: /a\n[evil]: /b'),
    ('> We never share data.', '> We always share data.'),
])
def test_quantity_reference_and_blockquote_are_protected(old, new):
    assert guard().guard_rewrite(old, new)['text'] == old


@pytest.mark.parametrize('old,new', [
    ('Read [manual](./foo(bar).md).', 'Read [manual](./foo(bar).exe).'),
    ('<script>const s = "</code>"; allowAccess = false;</script>', '<script>const s = "</code>"; allowAccess = true;</script>'),
    ('    run --dry-run\n\nDone.', '    run --execute\n\nDone.'),
])
def test_nested_links_opaque_html_and_indented_code_are_protected(old, new):
    assert guard().guard_rewrite(old, new, is_html=True)['text'] == old


@pytest.mark.parametrize('old,new', [
    ('See [safe].\n\n[safe]: /a\n[evil]: /b', 'See [evil].\n\n[safe]: /a\n[evil]: /b'),
    ('See [safe][].\n\n[safe]: /a\n[evil]: /b', 'See [evil][].\n\n[safe]: /a\n[evil]: /b'),
    ('> We keep data\nand never share it.', '> We keep data\nand always share it.'),
])
def test_shortcut_links_and_lazy_quote_continuations_are_protected(old, new):
    assert guard().guard_rewrite(old, new)['text'] == old
