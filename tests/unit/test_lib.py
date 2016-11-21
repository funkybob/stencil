# -*- coding: utf-8 -*-


import stencil

from stencil import BlockNode, Token


class TestTag(BlockNode):
    name = 'test'

    def render(self, context, output):
        output.write(u'test')


def test_tokenise():
    """Test :py:func:`stencil.tokenise` function."""

    it_token = stencil.tokenise('abc {{ x }} xyz')

    token = it_token.next()
    assert token is not None
    assert isinstance(token, Token)
    assert token.type == 'text'
    assert token.content == 'abc '

    token = it_token.next()
    assert token is not None
    assert isinstance(token, Token)
    assert token.type == 'var'
    assert token.content == 'x'

    token = it_token.next()
    assert token is not None
    assert isinstance(token, Token)
    assert token.type == 'text'
    assert token.content == ' xyz'
