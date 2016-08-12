import re

from collections import namedtuple


TOK_COMMENT = 'comment'
TOK_TEXT = 'text'
TOK_VAR = 'var'
TOK_BLOCK = 'block'

tag_re = re.compile(r'{%\s*(?P<block>.+?)\s*%}|{{\s*(?P<var>.+?)\s*}}|{#\s*(?P<comment>.+?)\s*#}', re.DOTALL)

nodename_re = re.compile(r'\w+')

Token = namedtuple('Token', 'type content')


def digattr(obj, attr, default=None):
    '''Perform template-style dotted lookup'''
    for step in attr.split('.'):
        try:    # dict lookup
            obj = obj[step]
        except (TypeError, AttributeError, KeyError):
            try:    # attribute lookup
                obj = getattr(obj, step)
            except (TypeError, AttributeError):
                try:    # list index lookup
                    obj = obj[int(step)]
                except (IndexError, ValueError, KeyError, TypeError):
                    return default
        if callable(obj):
            obj = obj()
    return obj


def tokenise(template):
    '''A generator which yields Token instances'''
    upto = 0

    for m in tag_re.finditer(template):
        start, end = m.span()
        # If there's a gap between our start and the end of the last match,
        # there's a Text node between.
        if upto < start:
            yield Token(TOK_TEXT, template[upto:start])
        upto = end

        mode = m.lastgroup
        content = m.group(mode)
        yield Token(mode, content.strip())

    # if the last match ended before the end of the source, we have a tail Text
    # node.
    if upto < len(template):
        yield Token(TOK_TEXT, template[upto:])


class ContextManager(object):
    def __init__(self, context):
        self.context = context

    def __enter__(self):
        pass

    def __exit__(self, *args, **kwargs):
        self.context.pop()


class Context(object):
    def __init__(self, **kwargs):
        self._stack = []
        self.push(**kwargs)

    def push(self, **kwargs):
        self._stack.insert(0, kwargs)
        return ContextManager(self)

    def pop(self):
        self._stack.pop(0)

    def __getitem__(self, key):
        for layer in self._stack:
            if key in layer:
                return layer[key]
        raise KeyError(key)


class Template(object):
    def __init__(self, src, loader=None):
        self.src = src
        self.tokens = tokenise(src)
        self.loader = loader

        self.nodes = list(self.parse())

    def parse(self):
        for token in self.tokens:
            if token.type == TOK_TEXT:
                yield TextNode(token.content)
            elif token.type == TOK_VAR:
                yield VarNode(token.content)
            elif token.type == TOK_BLOCK:
                m = nodename_re.match(token.content)
                if not m:
                    raise SyntaxError(token)
                yield BlockNode.__tags__[m.group(0)].parse(token.content[m.end(0):], self)
            else:  # TOK_COMMENT
                pass

    def render(self, context):
        if isinstance(context, dict):
            context = Context(**context)
        return u''.join(
            node.render(context) or ''
            for node in self.nodes
        )


class Node(object):
    name = None

    def __init__(self, content):
        self.content = content

    def render(self, context):
        pass


class TextNode(Node):

    def render(self, context):
        return self.content


class VarNode(Node):

    def render(self, context):
        # Parse expr
        # Resolve in context
        value = digattr(context, self.content)
        return value


class BlockMeta(type):
    def __new__(mcs, name, bases, attrs):
        cls = super(BlockMeta, mcs).__new__(mcs, name, bases, attrs)
        if name != 'BlockNode':
            BlockNode.__tags__[attrs['name']] = cls
        return cls


class BlockNode(Node):
    __metaclass__ = BlockMeta
    __tags__ = {}

    @classmethod
    def parse(cls, content, parser):
        return cls(content)

    def render(self, context):
        return ''


class ForNode(BlockNode):
    '''
    {% for value in iterable %}
    ...
    {% endfor %}
    '''
    name = 'for'

    def __init__(self, argname, iterable, nodelist):
        self.argname = argname
        self.iterable = iterable
        self.nodelist = nodelist

    @classmethod
    def parse(cls, content, parser):
        arg, iterable = content.split(' in ', 1)
        nodelist = []
        node = next(parser.parse())
        while node.name != 'endfor':
            nodelist.append(node)
            node = next(parser.parse())
        return cls(arg.strip(), iterable.strip(), nodelist)

    def render(self, context):
        iterable = digattr(context, self.iterable)
        items = []
        for item in iterable:
            with context.push(**{self.argname: item}):
                items.extend(
                    node.render(context)
                    for node in self.nodelist
                )
        return ''.join(map(str, items))


class EndforNode(BlockNode):
    name = 'endfor'


class IfNode(BlockNode):
    name = 'if'

    def __init__(self, condition, nodelist):
        self.condition = condition
        self.nodelist = nodelist

    @classmethod
    def parse(cls, content, parser):
        nodelist = []
        node = next(parser.parse())
        while node.name != 'endif':
            nodelist.append(node)
            node = next(parser.parse())
        return cls(content, nodelist)

    def render(self, context):
        if self.test_condition(context):
            return ''.join(map(str, [
                node.render(context)
                for node in self.nodelist
            ]))

    def test_condition(self, context):
        cond = self.condition.strip()
        if cond.split(' ', 1)[0].strip() == 'not':
            inv = True
            cond = cond.split(' ', 1)[1].strip()
        else:
            inv = False
        return inv ^ bool(digattr(context, cond))


class EndifNode(BlockNode):
    name = 'endif'
