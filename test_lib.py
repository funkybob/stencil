from stencil import BlockNode


class TestTag(BlockNode):
    name = 'test'

    def render(self, context, output):
        output.write(u'test')
