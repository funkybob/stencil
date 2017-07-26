# -*- coding: utf-8 -*-

import unittest

import stencil

from stencil import Token


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


class ContextTestCase(unittest.TestCase):

    def test_push(self):
        ctx = stencil.Context({'a': 1})
        self.assertEqual(ctx['a'], 1)
        self.assertIsNone(ctx['None'])
        with ctx:
            ctx.update({'a': 2})
            self.assertEqual(ctx['a'], 2)
        self.assertEqual(ctx['a'], 1)
