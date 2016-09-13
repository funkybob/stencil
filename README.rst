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

1. Create a simple template:

   .. code-block:: html

      Good morning, {{ name }}!

1. Write a script to use it

   .. code-block:: python

      import stencil

      from .utils import escape

      loader = stencil.TemplateLoader(['tmpl/'])

      t = loader['index.html']
      c = stencil.Contxt({'name': 'Ruprect'}, filters={'escape': escape})

      print t.render(c)
      # Should output "Good morning, Ruprect!"


See the `documentation <stencil-templates.readthedocs.io/en/latest/>`_ to see more details.
