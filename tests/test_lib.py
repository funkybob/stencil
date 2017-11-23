# -*- coding: utf-8 -*-
"""Module used in test_output module."""

from stencil import BlockNode


class TestTag(BlockNode, name='test'):

    def render(self, context, output):
        output.write(u'test')
