# -*- coding: utf-8 -*-

import os
import glob
import json

import stencil


def test_output():

    stencil.FILTERS.update({
        'title': unicode.title,
    })

    loader = stencil.TemplateLoader(['tmpl/'])

    for fn in sorted(glob.glob('tests/integration/tmpl/*.tpl')):
        print fn,
        base, ext = os.path.splitext(fn)

        try:
            t = loader.load(os.path.basename(fn))
        except StandardError:
            import traceback
            traceback.print_exc()
            print "FAIL"
            continue

        with open(base + '.out', 'r') as fin:
            out = fin.read()

        with open(base + '.json', 'r') as fin:
            data = json.load(fin)

        c = stencil.Context(data)
        result = t.render(c)

        assert result == out, 'Mismatched output for %r\n%r\n%r' % (fn, out, result)
        print "OK"
