# -*- coding: utf-8 -*-

import unittest

import stencil

from stencil import BlockNode, Token


class TestTag(BlockNode):
    name = 'test'

    def render(self, context, output):
        output.write(u'test')


class ModuleTestCase(unittest.TestCase):
    """Test cases for the stencil module."""

    @staticmethod
    def test_tokenise():
        """Test stencil.tokenise() function."""

        it_token = stencil.tokenise('abc {{ x }} xyz')

        token = next(it_token)
        assert isinstance(token, Token)
        assert token.type == 'text'
        assert token.content == 'abc '

        token = next(it_token)
        assert isinstance(token, Token)
        assert token.type == 'var'
        assert token.content == 'x'

        token = next(it_token)
        assert isinstance(token, Token)
        assert token.type == 'text'
        assert token.content == ' xyz'
