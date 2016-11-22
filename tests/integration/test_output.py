# -*- coding: utf-8 -*-

from __future__ import print_function


import sys
import os

import glob
import json
import string
import traceback
import unittest

import stencil


class IntegrationTestCase(unittest.TestCase):

    @staticmethod
    def test_output():

        stencil.FILTERS.update({
            'title': string.capwords,
        })

        loader = stencil.TemplateLoader(['tmpl/'])

        counter = 0
        for fn in sorted(glob.glob('tests/integration/tmpl/*.tpl')):
            print(fn,)
            base, ext = os.path.splitext(fn)

            try:
                t = loader.load(os.path.basename(fn))
            except:
                eargs = sys.exc_info()
                assert False, '[%s]\n%s' % (fn, traceback.format_exception(*eargs))

            with open(base + '.out', 'r') as fin:
                out = fin.read()

            with open(base + '.json', 'r') as fin:
                data = json.load(fin)

            c = stencil.Context(data)
            result = t.render(c)

            assert result == out, 'Mismatched output for %r\n%r\n%r' % (fn, out, result)
            counter += 1

        assert counter == 31, 'Expected 31 test run as opposed to %d' % counter
