from __future__ import unicode_literals

import importlib

import io
import os
import re

from collections import namedtuple, deque

TOK_COMMENT = 'comment'
TOK_TEXT = 'text'
TOK_VAR = 'var'
TOK_BLOCK = 'block'

tag_re = re.compile(r'{%\s*(?P<block>.+?)\s*%}|{{\s*(?P<var>.+?)\s*}}|{#\s*(?P<comment>.+?)\s*#}', re.DOTALL)
nodename_re = re.compile(r'\w+')
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
        self.paths = map(os.path.abspath, paths)

    def load(self, name):
        for path in self.paths:
            full_path = os.path.join(path, name)
            if os.path.isfile(full_path):
                with io.open(full_path, 'r') as fin:
                    return Template(fin.read(), loader=self)

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
        self.src = src
        self.loader = loader
        self.tokens = tokenise(src)
        self.nodes = list(self.parse())

    def parse(self):
        for token in self.tokens:
            if token.type == TOK_TEXT:
                yield TextTag(token.content)
            elif token.type == TOK_VAR:
                yield VarTag(token.content)
            elif token.type == TOK_BLOCK:
                m = nodename_re.match(token.content)
                if not m:
                    raise SyntaxError(token)
                yield BlockNode.__tags__[m.group(0)].parse(token.content[m.end(0):].strip(), self)

    def render(self, context, output=None):
        if isinstance(context, dict):
            context = Context(context)
        if output is None:
            output = output = io.StringIO()
        for node in self.nodes:
            node.render(context, output)
        return output.getvalue()


class Expression(object):
    def __init__(self, expr):
        parts = expr.split('|')
        self.var = parts[0]
        filters = parts[1:]
        self.filters = []
        for filt in filters:
            bits = filt.split(':', 1)
            args = bits[1].split(',') if len(bits) > 1 else []
            self.filters.append((bits[0], args))

    def resolve(self, context):
        value = self.resolve_lookup(context, self.var)

        for filt, args in self.filters:
            args = [self.resolve_lookup(arg) for arg in args]
            try:
                func = context.filters[filt]
            except KeyError:
                raise SyntaxError("Unknown filter function %s : %s -> %s" % (filt, self.var, self.filters))
            else:
                value = func(value, *args)
        return value

    def resolve_lookup(self, context, key, default=''):
        parts = iter(key.split('.'))
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

    @classmethod
    def parse(cls, content, parser):
        return cls(content)


class Nodelist(list):
    def __init__(self, parser, end):
        node = next(parser.parse())
        while node.name != end:
            self.append(node)
            node = next(parser.parse())

    def render(self, context, output):
        for node in self:
            node.render(context, output)


class ForTag(BlockNode):
    name = 'for'

    def __init__(self, argname, iterable, nodelist):
        self.argname = argname
        self.iterable = Expression(iterable)
        self.nodelist = nodelist

    @classmethod
    def parse(cls, content, parser):
        arg, iterable = content.split(' in ', 1)
        nodelist = Nodelist(parser, 'endfor')
        return cls(arg.strip(), iterable.strip(), nodelist)

    def render(self, context, output):
        iterable = self.iterable.resolve(context)
        context.push()
        for idx, item in enumerate(iterable):
            context['loopcounter'] = idx
            context[self.argname] = item
            self.nodelist.render(context, output)
        context.pop()


class EndforTag(BlockNode):
    name = 'endfor'


class IfTag(BlockNode):
    name = 'if'

    def __init__(self, condition, nodelist):
        if condition.split(' ', 1)[0].strip() == 'not':
            inv = True
            condition = condition.split(' ', 1)[1].strip()
        else:
            inv = False
        self.inv = inv
        self.condition = Expression(condition)
        self.nodelist = nodelist

    @classmethod
    def parse(cls, content, parser):
        nodelist = Nodelist(parser, 'endif')
        return cls(content, nodelist)

    def render(self, context, output):
        if self.test_condition(context):
            self.nodelist.render(context, output)

    def test_condition(self, context):
        return self.inv ^ bool(self.condition.resolve(context))


class EndifTag(BlockNode):
    name = 'endif'


class IncludeTag(BlockNode):
    name = 'include'

    def __init__(self, template_name, kwargs, loader):
        self.template_name = template_name
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
        tmpl = self.loader[self.template_name]
        kwargs = {key: expr.resolve(context) for key, expr in self.kwargs.items()}
        context.push(**kwargs)
        tmpl.render(context, output)
        context.pop()


class LoadTag(BlockNode):
    name = 'load'

    def __init__(self, module):
        self.module = module

    @classmethod
    def parse(cls, content, parser):
        module = importlib.import_module(content)
        return cls(module)
