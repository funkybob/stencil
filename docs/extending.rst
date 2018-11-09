=================
Extending stencil
=================

Stencil allows you to easily add new tags and filters.

Filters
=======

As noted in :ref:`custom_filters`, you can easily register new filter
functions.

Here is an example of adding an ``escape`` filter:

.. code-block:: python

    escape_html = lambda text: (
        text.replace('&', '&amp;')
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#x27;")
    )


    _js_escapes = {
        ord('\\'): '\\u005C',
        ord("'"): '\\u0027',
        ord('"'): '\\u0022',
        ord('>'): '\\u003E',
        ord('<'): '\\u003C',
        ord('&'): '\\u0026',
        ord('='): '\\u003D',
        ord('-'): '\\u002D',
        ord(';'): '\\u003B',
        ord('\u2028'): '\\u2028',
        ord('\u2029'): '\\u2029'
    }

    # Escape every ASCII character with a value less than 32.
    _js_escapes.update((ord('%c' % z), '\\u%04X' % z) for z in range(32))


    escape_js = lambda text: text.translate(_js_escapes)

    def escape(value, mode='html'):
        if mode == 'html':
            return escape_html(value)
        elif mode == 'js':
            return escape_js(value)
        raise ValueError('Invalid escape mode: %r' % mode)

And we use it in our template:

.. code-block:: html

   <input type="text" value="{{ value|escape }}">

Now we can use it by passing it in the context:

.. code-block:: python

   >>> from stencil import TemplateLoader, Context
   >>> ctx = Context({'value': '<script>alert("BOO");</script>', 'escape': escape})
   >>> tmp.render(ctx)
   u'<input type="text" value="&lt;script&gt;alert(&quot;BOO&quot;);&lt;/script&gt;">'


.. _extending_tags:

Tags
====

All tags derive from the ``stencil.BlockNode`` class, and self-register with
``stencil`` on declaration.

.. code-block:: python

    from stencil import BlockNode

    class MyTag(BlockNode, name='my'):  # This is matched in {% my %}

When ``stencil`` finds a tag matching this name, it will call the
``BlockNode.parse`` classmethod, passing it the rest of the tag content, and
the template instance.  This method must return a BlockNode sub-class instance.

.. code-block:: python

   class MyTag(BlockNode):

       @classmethod
       def parse(cls, content, parser):
           return cls(content)

The default action is to just return an instance of the class, passed the tag
content.

When a template is rendered, a blocks ``render`` method will be called, passed
a ``Context`` instance, and a file-like object to output to.

Tags with children
------------------

Some tags contain `child` nodes (e.g. ``for``, ``if``, ``block``).

To do this they build a ``Nodelist``:

.. code-block:: python

    class MyBlock(BlockNode):

        @classmethod
        def parse(self, content, parser):
            nodelist = parser.parse_nodelist({'endmyblock',})
            return cls(nodelist)

This will consume tags until it reaches one with a name found in the list. The
tags are added to a ``Nodelist`` instance, except the matching one which it
stored in ``Nodelist.endnode``.

A ``Nodelist`` can be rendered easily by calling their ``render`` method, which
works just like a ``BlockNode``.

.. code-block:: python

   nodelist.render(context, output)

Expressions
-----------

To have an argument resolved as an expression, use the ``parse_expression``
function.  This will parse then value passed, and construct an ``Expression``
instance.

Then in render, call ``Expression.resolve(context)`` to get its value.

For more fine grained parsing, and to parse ``key=expr`` syntax, use a
``Tokens`` class.

.. code-block:: python

   tokens = Tokens(content)

This provides several useful methods:

.. code-block:: python

   value = tokens.parse_argument()

Parses a single argument, be it a string, float or int literal, or a lookup.
The result is suitable for passing as the second argument to
``resolve_lookup``, or as the first to ``Expression``.

.. code-block:: python

    value = resolve_lookup(value)

.. code-block:: python

   value, filters = tokens.parse_filter_expression()

Parse a filter expression, returning a value (as from ``parse_argument``, and a
list of (filter name, \*args) tuples.

.. code-block:: python

   kwargs = tokens.parse_kwargs()

Parse `key=filter-expression` sequences, and construct a dict of
`key: Expression()` items.


.. code-block:: python

   tokens.assert_end()

Asserts the current token to be parsed is an end marker, or raises and
assertion error with a message showing where the token was.
