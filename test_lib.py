from stencil import BlockNode


class TestTag(BlockNode):
    name = 'test'

    def render(self, context):
        return u'test'
