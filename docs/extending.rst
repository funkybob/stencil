=================
Extending stencil
=================

Stencil allows you to easily add new tags.

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

To have an argument resolved as an expression, use the ``Expression.parse()``
function.  This will parse then value passed, and construct an ``Expression``
instance.

Then in render, call the expression's ``.resolve(context)`` to get its value.

For more fine grained parsing, and to parse ``key=expr`` syntax, create an
``Expression`` instance:

.. code-block:: python

   expr = Expression(content)

This provides several useful methods:

.. code-block:: python

   value = tokens._parse()

Parses a single argument, be it a string, float or int literal, or a lookup.

.. code-block:: python

   kwargs = expr.parse_kwargs()

Parse `key=expression` sequences, and construct a dict of
`key: Expression()` items.
