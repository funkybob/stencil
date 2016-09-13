from __future__ import unicode_literals

import importlib
import io
import os
import re
import tokenize
from collections import defaultdict, deque, namedtuple

TOK_COMMENT = 'comment'
TOK_TEXT = 'text'
TOK_VAR = 'var'
TOK_BLOCK = 'block'

tag_re = re.compile(r'{%\s*(?P<block>.+?)\s*%}|{{\s*(?P<var>.+?)\s*}}|{#\s*(?P<comment>.+?)\s*#}', re.DOTALL)
Token = namedtuple('Token', 'type content')


def tokenise(template):
    upto = 0

    for m in tag_re.finditer(template):
        start, end = m.span()
        if upto < start:
            yield Token(TOK_TEXT, template[upto:start])
        upto = end

        mode = m.lastgroup
        yield Token(mode, m.group(mode).strip())

    if upto < len(template):
        yield Token(TOK_TEXT, template[upto:])


class TemplateLoader(dict):
    def __init__(self, paths):
        self.paths = [os.path.abspath(path) for path in paths]

    def load(self, name):
        for path in self.paths:
            full_path = os.path.join(path, name)
            if os.path.isfile(full_path):
                with io.open(full_path, 'r') as fin:
                    return Template(fin.read(), loader=self)
        raise ValueError(name)

    def __missing__(self, key):
        self[key] = tmpl = self.load(key)
        return tmpl


class Context(object):
    def __init__(self, data, filters=None):
        self._stack = deque({'True': True, 'False': False, 'None': None})
        self.push(**data)
        self.filters = filters or {}

    def push(self, **kwargs):
        self._stack.appendleft(kwargs)

    def pop(self):
        self._stack.popleft()

    def __getitem__(self, key):
        for layer in self._stack:
            if key in layer:
                return layer[key]
        raise KeyError(key)

    def __setitem__(self, key, value):
        self._stack[0][key] = value


class Template(object):
    def __init__(self, src, loader=None):
        self.loader = loader
        self.tokens = tokenise(src)
        self.nodelist = Nodelist(self, ())

    def parse(self):
        for token in self.tokens:
            if token.type == TOK_TEXT:
                yield TextTag(token.content)
            elif token.type == TOK_VAR:
                yield VarTag(token.content)
            elif token.type == TOK_BLOCK:
                m = re.match('\w+', token.content)
                if not m:
                    raise SyntaxError(token)
                yield BlockNode.__tags__[m.group(0)].parse(token.content[m.end(0):].strip(), self)

    def render(self, context, output=None):
        if not isinstance(context, Context):
            context = Context(context)
        if output is None:
            output = io.StringIO()
        self.nodelist.render(context, output)
        return output.getvalue()


class Expression(object):
    def __init__(self, expr):
        self.tokens = tokenize.generate_tokens(io.StringIO(expr).readline)
        tok = next(self.tokens)

        value, tok = self.parse_argument(tok)
        self.value = value

        filters = []
        while tok[0] == tokenize.OP and tok[1] == '|':
            tok = next(self.tokens)
            assert tok[0] == tokenize.NAME, "Invalid syntax in expression at %d.  Expected name." % (tok[2][1],)
            filt = tok[1]
            args = []
            tok = next(self.tokens)
            if tok[0] == tokenize.OP and tok[1] == ':':
                value, tok = self.parse_argument(tok)
                args.append(value)
                while tok[0] == tokenize.OP and tok[1] == ',':
                    arg, tok = self.parse_argument(tok)
                    args.append(arg)
            filters.append((filt, args))

        self.filters = filters
        assert tok[0] == tokenize.ENDMARKER, "Unexpected extra in expression at %d: %s" % (tok[2][1], tok[1])

    def parse_argument(self, tok):
        if tok[0] == tokenize.STRING:
            return tok[1][1:-1], next(self.tokens)
        elif tok[0] == tokenize.NUMBER:
            try:
                value = int(tok[1])
            except ValueError:
                value = float(tok[1])
            return value, next(self.tokens)
        elif tok[0] == tokenize.NAME:
            var = [tok[1]]
            tok = next(self.tokens)
            while tok[0] == tokenize.OP and tok[1] == ':':
                tok = next(self.tokens)
                assert tok[0] in (tokenize.NAME, tokenize.NUMBER), "Invalid syntax in expression at %d: %r" % (
                    tok[2][1], tok[-1],
                )
                var.append(tok[1])
                tok = next(self.tokens)
            return var, tok

    def resolve(self, context):
        value = self.resolve_lookup(context, self.value)

        for filt, args in self.filters:
            args = [self.resolve_lookup(context, arg) for arg in args]
            try:
                func = context.filters[filt]
            except KeyError:
                raise SyntaxError("Unknown filter function %s : %s -> %s" % (filt, self.value, self.filters))
            else:
                value = func(value, *args)
        return value

    def resolve_lookup(self, context, parts, default=''):
        if isinstance(parts, (int, float, basestring)):
            return parts
        parts = iter(parts)
        try:
            obj = context[next(parts)]
        except KeyError:
            return default
        for step in parts:
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


class Node(object):
    name = None

    def __init__(self, content):
        self.content = content

    def render(self, context, output):
        pass  # pragma: no cover


class TextTag(Node):
    def render(self, context, output):
        output.write(self.content)


class VarTag(Node):
    def __init__(self, content):
        self.expr = Expression(content)

    def render(self, context, output):
        output.write(unicode(self.expr.resolve(context)))


class BlockMeta(type):
    def __new__(mcs, name, bases, attrs):
        cls = super(BlockMeta, mcs).__new__(mcs, name, bases, attrs)
        if 'name' in attrs:
            BlockNode.__tags__[attrs['name']] = cls
        return cls


class BlockNode(Node):
    __metaclass__ = BlockMeta
    __tags__ = {}
    child_nodelists = ('nodelist',)

    @classmethod
    def parse(cls, content, parser):
        return cls(content)

    def nodes_by_type(self, node_type):
        for attr in self.child_nodelists:
            nodelist = getattr(self, attr, None)
            if nodelist:
                for node in nodelist.nodes_by_type(node_type):
                    yield node


class Nodelist(list):
    def __init__(self, parser, ends):
        node = next(parser.parse())
        try:
            while node.name not in ends:
                self.append(node)
                node = next(parser.parse())
        except StopIteration:
            node = None
        self.endnode = node

    def render(self, context, output):
        for node in self:
            node.render(context, output)

    def nodes_by_type(self, node_type):
        for node in self:
            if isinstance(node, node_type):
                yield node
            if isinstance(node, BlockNode):
                for child in node.nodes_by_type(node_type):
                    yield child


class ForTag(BlockNode):
    name = 'for'
    child_nodelists = ('nodelist', 'elselist')

    def __init__(self, argname, iterable, nodelist, elselist):
        self.argname = argname
        self.iterable = Expression(iterable)
        self.nodelist = nodelist
        self.elselist = elselist

    @classmethod
    def parse(cls, content, parser):
        arg, iterable = content.split(' in ', 1)
        nodelist = Nodelist(parser, ['endfor', 'else'])
        if nodelist.endnode.name == 'else':
            elselist = Nodelist(parser, ['endfor'])
        else:
            elselist = None
        return cls(arg.strip(), iterable.strip(), nodelist, elselist)

    def render(self, context, output):
        iterable = self.iterable.resolve(context)
        if self.elselist and not iterable:
            self.elselist.render(context, output)
        else:
            context.push()
            for idx, item in enumerate(iterable):
                context['loopcounter'] = idx
                context[self.argname] = item
                self.nodelist.render(context, output)
            context.pop()


class ElseTag(BlockNode):
    name = 'else'


class EndforTag(BlockNode):
    name = 'endfor'


class IfTag(BlockNode):
    name = 'if'
    child_nodelists = ('nodelist', 'elselist')

    def __init__(self, condition, nodelist, elselist):
        condition, inv = re.subn(r'^not\s+', '', condition, count=1)
        self.inv = bool(inv)
        self.condition = Expression(condition)
        self.nodelist = nodelist
        self.elselist = elselist

    @classmethod
    def parse(cls, content, parser):
        nodelist = Nodelist(parser, ['endif', 'else'])
        if nodelist.endnode.name == 'else':
            elselist = Nodelist(parser, ['endif'])
        else:
            elselist = None
        return cls(content, nodelist, elselist)

    def render(self, context, output):
        if self.test_condition(context):
            self.nodelist.render(context, output)
        elif self.elselist:
            self.elselist.render(context, output)

    def test_condition(self, context):
        return self.inv ^ bool(self.condition.resolve(context))


class EndifTag(BlockNode):
    name = 'endif'


class IncludeTag(BlockNode):
    name = 'include'

    def __init__(self, template_name, kwargs, loader):
        self.template_name = Expression(template_name)
        self.kwargs = kwargs
        self.loader = loader

    @classmethod
    def parse(cls, content, parser):
        assert parser.loader is not None, "Can't use {% include %} without a bound Loader"
        bits = content.split()
        kwargs = {}
        for kwarg in bits[1:]:
            key, expr = kwarg.split('=')
            kwargs[key] = Expression(expr)
        return cls(bits[0], kwargs, parser.loader)

    def render(self, context, output):
        tmpl = self.loader[self.template_name.resolve(context)]
        kwargs = {key: expr.resolve(context) for key, expr in self.kwargs.items()}
        context.push(**kwargs)
        tmpl.render(context, output)
        context.pop()


class LoadTag(BlockNode):
    name = 'load'

    @classmethod
    def parse(cls, content, parser):
        importlib.import_module(content)
        return cls(None)


class ExtendsTag(BlockNode):
    name = 'extends'

    def __init__(self, parent, loader, nodelist):
        self.parent = Expression(parent)
        self.loader = loader
        self.nodelist = nodelist

    @classmethod
    def parse(cls, content, parser):
        parent = content.split()[0].strip()
        nodelist = Nodelist(parser, [])
        return cls(parent, parser.loader, nodelist)

    def render(self, context, output):
        parent = self.loader[self.parent.resolve(context)]

        block_context = getattr(context, 'block_context', None)
        if block_context is None:
            block_context = context.block_context = defaultdict(deque)

        for block in self.nodelist.nodes_by_type(BlockTag):
            block_context[block.block_name].append(block)

        if not isinstance(parent.nodelist[0], ExtendsTag):
            for block in parent.nodelist.nodes_by_type(BlockTag):
                block_context[block.block_name].append(block)

        parent.render(context, output)


class BlockTag(BlockNode):
    name = 'block'

    def __init__(self, name, nodelist):
        self.block_name = name
        self.nodelist = nodelist

    @classmethod
    def parse(cls, content, parser):
        name = re.match('\w+', content).group(0)
        nodelist = Nodelist(parser, ['endblock'])
        return cls(name, nodelist)

    def render(self, context, output):
        block_context = getattr(context, 'block_context', None)
        if block_context is None:
            block_context = context.block_context = defaultdict(deque)
        if not block_context:
            block = self
        else:
            block = block_context[self.block_name].popleft()
        context.push()
        block.nodelist.render(context, output)
        context.pop()


class EndBlockTag(BlockNode):
    name = 'endblock'
