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

.. _custom_filters:

Custom filters
--------------

Filtering functions for applying to values in expressions can be included in
the context.
