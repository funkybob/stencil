import importlib
import re
import tokenize
from io import StringIO
from pathlib import Path
from collections import defaultdict, deque, namedtuple, ChainMap

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
        self.paths = [Path(path).resolve() for path in paths]

    def load(self, name, encoding='utf8'):
        for path in self.paths:
            full_path = path / name
            if full_path.is_file():
                return Template(full_path.read_text(encoding), loader=self)
        raise LookupError(name)

    def __missing__(self, key):
        self[key] = tmpl = self.load(key)
        return tmpl


class Context(ChainMap):
    def __init__(self, *args):
        super().__init__(*args)
        self.maps.append({'True': True, 'False': False, 'None': None})

    def push(self, data=None):
        self.maps.insert(0, data or {})
        return self

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, tb):
        self.maps.pop(0)


class Nodelist(list):
    def render(self, context, output):
        for node in self:
            node.render(context, output)

    def nodes_by_type(self, node_type):
        for node in self:
            if isinstance(node, node_type):
                yield node
            if isinstance(node, BlockNode):
                yield from node.nodes_by_type(node_type)


class Template:
    def __init__(self, src, loader=None):
        self.tokens, self.loader = tokenise(src), loader
        self.nodelist = self.parse_nodelist([])

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

    def parse_nodelist(self, ends):
        nodelist = Nodelist()
        try:
            node = next(self.parse())
            while node.name not in ends:
                nodelist.append(node)
                node = next(self.parse())
        except StopIteration:
            node = None
        nodelist.endnode = node
        return nodelist

    def render(self, context, output=None):
        if not isinstance(context, Context):
            context = Context(context)
        if output is None:
            output = StringIO()
        self.nodelist.render(context, output)
        return output.getvalue()


class Tokens:
    def __init__(self, source):
        self.tokens = tokenize.generate_tokens(StringIO(source).readline)
        self.next()

    def next(self):
        self.current = next(self.tokens)

    def parse_filter_expression(self, end=False):
        value = self.parse_argument()
        filters = []
        while self.current[0:2] == (tokenize.OP, '|'):
            self.next()
            if self.current[0] != tokenize.NAME:
                raise SyntaxError(f"Invalid syntax in expression at {self.current[2][1]}.  Expected name.")
            filt = self.current[1]
            args = []
            self.next()
            if self.current[0] == tokenize.OP and self.current[1] == ':':
                self.next()
                term = self.parse_argument()
                args.append(term)
                while self.current[0] == tokenize.OP and self.current[1] == ',':
                    args.append(self.parse_argument())
            filters.append((filt, args))
        if end:
            self.assert_end()
        return Expression(value, filters)

    def parse_argument(self):
        ''' Parse either a string literal, int/float literal, or lookup sequence '''
        if self.current[0] == tokenize.STRING:
            value = self.current[1][1:-1]
            self.next()
            return value
        elif self.current[0] == tokenize.NUMBER:
            try:
                value = int(self.current[1])
            except ValueError:
                value = float(self.current[1])
            self.next()
            return value
        elif self.current[0] == tokenize.NAME:
            var = [self.current[1]]
            self.next()
            if self.current[0] == tokenize.OP and self.current[1] == u':':
                self.next()
                if self.current[0] not in (tokenize.NAME, tokenize.NUMBER):
                    raise SyntaxError(
                        f"Invalid syntax in expression at {self.current[2][1]}: {self.current[-1]}"
                    )
                var.append(self.current[1])
                self.next()
            return var
        raise SyntaxError(f'Unexpected token: {self.current}')

    def parse_kwargs(self, end=False):
        kwargs = {}
        while self.current[0] != tokenize.ENDMARKER:
            if self.current[0] == tokenize.NEWLINE:
                self.next()
                continue
            if self.current[0] != tokenize.NAME:
                raise SyntaxError(f'Syntax error parsing kwargs ({self.current[2][0]}): {self.current[-1]}')
            key = self.current[1]
            self.next()
            if not (self.current[0] == tokenize.OP and self.current[1] == '='):
                raise SyntaxError(f'Syntax error parsing kwargs ({self.current[2][0]}): {self.current[-1]}')
            self.next()
            kwargs[key] = self.parse_filter_expression()
        if end:
            self.assert_end()
        return kwargs

    def assert_end(self):
        while self.current[0] == tokenize.NEWLINE:
            self.next()  # Python now adds a NEWLINE even if we didn't pass one.
        if self.current[0] != tokenize.ENDMARKER:
            raise SyntaxError(f"Error parsing arguments ({self.current[2][0]}): {self.current[-1]}")

    @staticmethod
    def parse_expression(source):
        return Tokens(source).parse_filter_expression(end=True)


class Expression:
    def __init__(self, value, filters):
        self.value, self.filters = value, filters

    def resolve(self, context):
        value = resolve_lookup(context, self.value)
        for filt, args in self.filters:
            try:
                func = context[filt]
            except KeyError:
                raise ValueError(f'Filter {filt} is not defined!')
            if not callable(func):
                raise TypeError(f"Filter '{filt}' is not callable!")
            value = func(value, *[resolve_lookup(context, arg) for arg in args])
        return value


def resolve_lookup(context, parts, default=''):
    if isinstance(parts, (int, float, str)):
        return parts
    parts = iter(parts)
    try:
        obj = context[next(parts)]
    except KeyError:
        return default
    if callable(obj):
        obj = obj()
    for step in parts:
        try:
            obj = obj[step]
        except (TypeError, AttributeError, KeyError):
            try:
                obj = getattr(obj, step)
            except (TypeError, AttributeError):
                try:
                    obj = obj[int(step)]
                except (IndexError, ValueError, KeyError, TypeError):
                    return default
        if callable(obj):
            obj = obj()
    return obj


class Node:
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
        self.expr = Tokens.parse_expression(content)

    def render(self, context, output):
        output.write(str(self.expr.resolve(context)))


class BlockNode(Node):
    __tags__ = {}
    child_nodelists = ('nodelist',)

    def __init_subclass__(cls, *, name):
        super().__init_subclass__()
        cls.name = name
        BlockNode.__tags__[name] = cls
        return cls

    @classmethod
    def parse(cls, content, parser):
        return cls(content)

    def nodes_by_type(self, node_type):
        for attr in self.child_nodelists:
            nodelist = getattr(self, attr, None)
            if nodelist:
                yield from nodelist.nodes_by_type(node_type)


class ForTag(BlockNode, name='for'):
    child_nodelists = ('nodelist', 'elselist')

    def __init__(self, argname, iterable, nodelist, elselist):
        self.argname, self.iterable, self.nodelist, self.elselist = argname, iterable, nodelist, elselist

    @classmethod
    def parse(cls, content, parser):
        argname, iterable = content.split(' in ', 1)
        nodelist = parser.parse_nodelist({'endfor', 'else'})
        elselist = parser.parse_nodelist({'endfor'}) if nodelist.endnode.name == 'else' else None
        return cls(argname.strip(), Tokens.parse_expression(iterable.strip()), nodelist, elselist)

    def render(self, context, output):
        iterable = self.iterable.resolve(context)
        if self.elselist and not iterable:
            self.elselist.render(context, output)
        else:
            with context.push():
                for idx, item in enumerate(iterable):
                    context.update({'loopcounter': idx, self.argname: item})
                    self.nodelist.render(context, output)


class ElseTag(BlockNode, name='else'):
    pass


class EndforTag(BlockNode, name='endfor'):
    pass


class IfTag(BlockNode, name='if'):
    child_nodelists = ('nodelist', 'elselist')

    def __init__(self, condition, nodelist, elselist):
        condition, inv = re.subn(r'^not\s+', '', condition, count=1)
        self.inv, self.condition = bool(inv), Tokens.parse_expression(condition)
        self.nodelist, self.elselist = nodelist, elselist

    @classmethod
    def parse(cls, content, parser):
        nodelist = parser.parse_nodelist({'endif', 'else'})
        elselist = parser.parse_nodelist({'endif'}) if nodelist.endnode.name == 'else' else None
        return cls(content, nodelist, elselist)

    def render(self, context, output):
        if self.test_condition(context):
            self.nodelist.render(context, output)
        elif self.elselist:
            self.elselist.render(context, output)

    def test_condition(self, context):
        return self.inv ^ bool(self.condition.resolve(context))


class EndifTag(BlockNode, name='endif'):
    pass


class IncludeTag(BlockNode, name='include'):

    def __init__(self, template_name, kwargs, loader):
        self.template_name, self.kwargs, self.loader = template_name, kwargs, loader

    @classmethod
    def parse(cls, content, parser):
        if parser.loader is None:
            raise RuntimeError("Can't use {% include %} without a bound Loader")
        tokens = Tokens(content)
        template_name = tokens.parse_filter_expression()
        kwargs = tokens.parse_kwargs(end=True)
        return cls(template_name, kwargs, parser.loader)

    def render(self, context, output):
        name = self.template_name.resolve(context)
        tmpl = self.loader[name]
        kwargs = {key: expr.resolve(context) for key, expr in self.kwargs.items()}
        with context.push(kwargs):
            tmpl.render(context, output)


class LoadTag(BlockNode, name='load'):

    @classmethod
    def parse(cls, content, parser):
        importlib.import_module(content)
        return cls(None)


class ExtendsTag(BlockNode, name='extends'):

    def __init__(self, parent, loader, nodelist):
        self.parent, self.loader, self.nodelist = parent, loader, nodelist

    @classmethod
    def parse(cls, content, parser):
        parent = Tokens.parse_expression(content)
        nodelist = parser.parse_nodelist([])
        return cls(parent, parser.loader, nodelist)

    def render(self, context, output):
        parent = self.loader[self.parent.resolve(context)]
        block_context = getattr(context, 'block_context', None)
        if block_context is None:
            block_context = context.block_context = defaultdict(deque)
        for block in self.nodelist.nodes_by_type(BlockTag):
            block_context[block.block_name].append(block)
        if parent.nodelist[0].name != 'extends':
            for block in parent.nodelist.nodes_by_type(BlockTag):
                block_context[block.block_name].append(block)
        parent.render(context, output)


class BlockTag(BlockNode, name='block'):

    def __init__(self, name, nodelist):
        self.block_name, self.nodelist = name, nodelist

    @classmethod
    def parse(cls, content, parser):
        name = re.match('\w+', content).group(0)
        nodelist = parser.parse_nodelist({'endblock'})
        return cls(name, nodelist)

    def render(self, context, output):
        block_context = getattr(context, 'block_context', None)
        if not block_context:
            block = self
        else:
            block = block_context[self.block_name].popleft()
        with context.push():
            block.nodelist.render(context, output)


class EndBlockTag(BlockNode, name='endblock'):
    pass


class WithTag(BlockNode, name='with'):

    def __init__(self, kwargs, nodelist):
        self.kwargs, self.nodelist = kwargs, nodelist

    @classmethod
    def parse(cls, content, parser):
        kwargs = Tokens(content).parse_kwargs(end=True)
        nodelist = parser.parse_nodelist({'endwith'})
        return cls(kwargs, nodelist)

    def render(self, context, output):
        kwargs = {key: value.resolve(context) for key, value in self.kwargs.items()}
        with context.push(kwargs):
            self.nodelist.render(context, output)


class EndWithTag(BlockNode, name='endwith'):
    pass


class CaseTag(BlockNode, name='case'):

    def __init__(self, term, nodelist):
        self.term, self.nodelist = term, nodelist

    @classmethod
    def parse(cls, content, parser):
        term = Tokens.parse_expression(content)
        nodelist = parser.parse_nodelist(['endcase'])
        else_found = False
        for node in nodelist:
            if node.name not in {'when', 'else'}:
                raise SyntaxError(f"Only 'when' and 'else' allowed as children of case. Found: {node}")
            if node.name == 'else':
                if else_found:
                    raise SyntaxError('Case tag can only have one else child')
                else_found = True
        nodelist.sort(key=lambda x: x.name, reverse=True)
        return cls(term, nodelist)

    def render(self, context, output):
        value = self.term.resolve(context)
        for node in self.nodelist:
            if node.name == 'when':
                other = node.term.resolve(context)
            else:
                other = value
            if value == other:
                node.render(context, output)
                return


class WhenTag(BlockNode, name='when'):

    def __init__(self, term, nodelist):
        self.term, self.nodelist = term, nodelist

    @classmethod
    def parse(cls, content, parser):
        term = Tokens.parse_expression(content)
        nodelist = parser.parse_nodelist()
        return cls(term, nodelist)

    def render(self, context, output):
        self.nodelist.render(context, output)


class EndCaseTag(BlockNode, name='endcase'):
    pass
