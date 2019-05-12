import importlib
import re
import token
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
        yield Token(mode, m[mode].strip())
    if upto < len(template):
        yield Token(TOK_TEXT, template[upto:])


class TemplateLoader(dict):
    def __init__(self, paths):
        self.paths = [Path(path).resolve() for path in paths]

    def load(self, name, encoding='utf8'):
        for path in self.paths:
            full_path = path / name
            if full_path.is_file():
                return Template(full_path.read_text(encoding), loader=self, name=name)
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
    def __init__(self, src, loader=None, name=None):
        self.tokens, self.loader = tokenise(src), loader
        self.name = name  # So we can report where the fault was
        self.nodelist = self.parse_nodelist([])

    def parse(self):
      try:
        for tok in self.tokens:
            if tok.type == TOK_TEXT:
                yield TextTag(tok.content)
            elif tok.type == TOK_VAR:
                yield VarTag(tok.content)
            elif tok.type == TOK_BLOCK:
                m = re.match(r'\w+', tok.content)
                if not m:
                    raise SyntaxError(tok)
                yield BlockNode.__tags__[m.group(0)].parse(tok.content[m.end(0):].strip(), self)
      except Exception as ex:
        raise RuntimeError(f"Error parsing template {self.name}") from ex

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
            dest = StringIO()
        else:
            dest = output
        self.nodelist.render(context, dest)
        if output is None:
            return dest.getvalue()


class AstLiteral:
    def __init__(self, arg):
        self.arg = arg

    def resolve(self, context):
        return self.arg


class AstContext:
    def __init__(self, arg):
        self.arg = arg

    def resolve(self, context):
        return context.get(self.arg, '')


class AstLookup:
    def __init__(self, left, right):
        self.left = left
        self.right = right

    def resolve(self, context):
        left = self.left.resolve(context)
        right = self.right.resolve(context)

        return left[right]


class AstAttr:
    def __init__(self, left, right):
        self.left = left
        self.right = right

    def resolve(self, context):
        left = self.left.resolve(context)

        return getattr(left, self.right)


class AstCall:
    def __init__(self, func):
        self.func = func
        self.args = []

    def add_arg(self, arg):
        self.args.append(arg)

    def resolve(self, context):
        func = self.func.resolve(context)
        args = [arg.resolve(context) for arg in self.args]

        return func(*args)


class Expression:
    def __init__(self, source):
        self.tokens = tokenize.generate_tokens(StringIO(source).readline)
        self.next()  # prime the first token

    def next(self):
        self.current = next(self.tokens)
        return self.current

    @staticmethod
    def parse(s):
        p = Expression(s)
        result = p._parse()

        if p.current.exact_type not in (token.NEWLINE, token.ENDMARKER):
            raise SyntaxError(f'Parse ended unexpectedly: {p.current}')

        return result

    def parse_kwargs(self):
        kwargs = {}

        tok = self.current

        while tok.exact_type != token.ENDMARKER:
            if tok == token.NEWLINE:
                tok = self.next()
                continue

            if tok.exact_type != token.NAME:
                raise SyntaxError(f'Expected name, found {tok}')
            name = tok.string
            tok = self.next()

            if tok.exact_type != token.EQUAL:
                raise SyntaxError(f'Expected =, found {tok}')
            tok = self.next()

            kwargs[name] = self._parse()

            tok = self.next()

        return kwargs

    def _parse(self):
        tok = self.current

        if tok.exact_type in (token.ENDMARKER, token.COMMA):
            return  # TODO

        if tok.exact_type == token.STRING:
            self.next()
            return AstLiteral(tok.string[1:-1])

        if tok.exact_type == token.NUMBER:
            self.next()
            try:
                value = int(tok.string)
            except ValueError:
                value = float(tok.string)
            return AstLiteral(value)

        if tok.exact_type == token.NAME:
            state = AstContext(tok.string)

            while True:
                tok = self.next()

                if tok.exact_type == token.DOT:
                    tok = self.next()
                    if tok.exact_type != token.NAME:
                        raise SyntaxError(f"Invalid attr lookup: {tok}")
                    state = AstAttr(state, tok.string)

                elif tok.exact_type == token.LSQB:
                    self.next()
                    right = self._parse()
                    state = AstLookup(state, right)
                    if self.current.exact_type != token.RSQB:
                        raise SyntaxError(f"Expected ] but found {self.current}")

                elif tok.exact_type == token.LPAR:
                    state = AstCall(state)
                    self.next()
                    while self.current.exact_type != token.RPAR:
                        arg = self._parse()
                        state.add_arg(arg)
                        if self.current.exact_type != token.COMMA:
                            break
                        self.next()

                    if self.current.exact_type != token.RPAR:
                        raise SyntaxError(f"Expected ( but found {self.current}")

                    self.next()

                else:
                    break

            return state

        raise SyntaxError(f'Unexpected token: {tok}')


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
        self.expr = Expression.parse(content)

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
        return cls(argname.strip(), Expression.parse(iterable.strip()), nodelist, elselist)

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
        self.inv, self.condition = bool(inv), Expression.parse(condition)
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
        tokens = Expression(content)
        template_name = tokens._parse()
        kwargs = tokens.parse_kwargs()
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
        parent = Expression.parse(content)
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
        name = re.match(r'\w+', content).group(0)
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
        kwargs = Expression(content).parse_kwargs()
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
        term = Expression.parse(content)
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
        term = Expression.parse(content)
        nodelist = parser.parse_nodelist()
        return cls(term, nodelist)

    def render(self, context, output):
        self.nodelist.render(context, output)


class EndCaseTag(BlockNode, name='endcase'):
    pass
