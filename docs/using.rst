===============
Using Templates
===============

To use stencil templates there is very little to do.

From Strings
============

To build a template from a string, just create a ``stencil.Template`` instance:

.. code-block:: python

   >>> from stencil import Template

   >>> t = Template('''Hello, {{name}}!''')

And to render it:

.. code-block:: python

   >>> t.render({'name': 'Bob'})
   'Hello, Bob!'

From a file
===========

First you'll need to create a ``TemplateLoader``, passing it a list of paths to
search for templates.

.. code-block:: python

    >>> from stencil import TemplateLoader
    >>> loader = TemplateLoader(['templates/'])

You can ask it to load a template freshly calling ``TemplateLoader.load``

    >>> t = loader.load('base.html')

The ``TemplateLoader`` can also cache loaded, parsed templates if you treat it
as a dict:

    >>> t = loader['base.html']
    # Loads template from file.
    >>> s = loader['base.html']
    # Returns the same template instance.

Context
=======

When rendering a template, you need to pass it a ``Context`` - this is the
limit of information the template can access.

When instantiating a Context, you can pass it the information you want
available to the template.

    >>> ctx = stencil.Context({'a': True})

Rendering
=========

Finally, to render a template, call its ``render()`` method, passing a context.

    >>> output = t.render(ctx)

Additionally, you can pass a file-like object for the template to write into:

    >>> with open('output.html', 'w') as fout:
    ...     t.render(ctx, fout)

Escaping
========

By default, all variables (e.g. ``{{ var }}``) will be `escaped`, using
``html.escape``.

Values can be marked as "safe", and thus not requiring escaping, by wrapping
them in ``stencil.SafeStr``.

Alternatively, any object whose ``__safe__`` attribute is Truethy will not be
escaped.

Alternate Escaping
------------------

You can override the escaping function used when constructing the ``Context``.

    >>> ctx = Context({...}, escape=my_escape)
