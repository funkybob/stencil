stencil
=======

A minimalist template engine for Python

The goal of Stencil is to provide just enough of a template engine in a single file.

Currently weighs in at just under 500 LoC

Quick Start
-----------

1. Make a directory for our templates:

   .. code-block:: bash

      $ mkdir tmpl

2. Create a simple template:

   .. code-block:: html

      Good morning, {{ name|escape }}!

3. Write a script to use it

   .. code-block:: python

      import stencil

      from .utils import escape

      stencil.FILTERS['escape'] = escape
      loader = stencil.TemplateLoader(['tmpl/'])

      t = loader['index.html']
      c = stencil.Context({'name': 'Ruprect'})

      print t.render(c)
      # Should output "Good morning, Ruprect!"


See the `documentation <https://stencil-templates.readthedocs.io/en/latest/>`_ to see more details.
