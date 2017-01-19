# -*- coding: utf-8 -*-

from __future__ import print_function


import sys

import json
import string
import traceback
import unittest

import stencil


class IntegrationTestCase(unittest.TestCase):

    dir_tpl = 'tests/integration/tmpl/'

    @staticmethod
    def basename(file_name, extension):
        """Return full path."""
        return '%s/%s.%s' % (IntegrationTestCase.dir_tpl, file_name, extension)

    def setUp(self):
        stencil.FILTERS.update({
            'title': string.capwords,
        })

        self.loader = stencil.TemplateLoader([IntegrationTestCase.dir_tpl])

    def assert_output(self, base):
        try:
            t = self.loader.load('%s.tpl' % base)
        except:
            assert False, '[%s]\n%s' % (
                base, ''.join(traceback.format_exc())
            )

        out = self.read_text_data(base)
        data = self.read_json_data(base)

        c = stencil.Context(data)
        result = t.render(c)

        assert result == out, 'Mismatched output for %r\n%r\n%r' % (base, out, result)

    def read_json_data(self, file_name):
        """Return JSON data for the given template test.

        Args:
            file_name (str): the template being tested.

        Returns:
            (str): JSON.
        """
        with open(self.basename(file_name, 'json'), 'r') as fin:
            return json.load(fin)

    def read_text_data(self, file_name):
        """Return expected output for the given template test.

        Args:
            file_name (str): the template being tested.

        Returns:
            (str): output.
        """
        with open(self.basename(file_name, 'out'), 'r') as fin:
            return fin.read()

    def test_simple(self):
        self.assert_output('01_simple')

    def test_for(self):
        self.assert_output('02_for')

    def test_if(self):
        self.assert_output('03_if')

    def test_ifnot(self):
        self.assert_output('04_ifnot')

    def test_filter(self):
        self.assert_output('05_filter')

    def test_filter_args(self):
        stencil.FILTERS['join'] = lambda x, n: n.join(x)
        self.assert_output('05_filter_args')

    def test_include(self):
        self.assert_output('06_include')

    def test_var(self):
        self.assert_output('07_var')

    def test_comment(self):
        self.assert_output('08_comment')

    def test_load(self):
        self.assert_output('09_load')

    def test_extends(self):
        self.assert_output('10_extends')
