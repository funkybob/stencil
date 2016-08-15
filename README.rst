stencil
=======

A minimalist template engine for Python

The goal of Stencil is to provide just enough of a template engine in a single file.

Currently weighs in at under 300 LoC

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
      # Should output "Good morning, Rupprect!"

What it can do
--------------

1. Variable rendering

   .. code-block:: html

      {{ var.from.context }}

   Django style dotted-lookup variables rendering.

   Filters are also supported, if passed to the Context.

   .. code-block:: html

      {{ foo.bar|escape }}

   Filers can take an arbitrary number of arguments:

   .. code-block:: html

      {{ foo.bar|mangle:foo.baz,quz,wibble.pencil }}

2. If conditions

   No expression support, just simple boolean testing:

   .. code-block:: html

      {% if condition %}
      ...
      {% endif %}
      {% if not condition %}
      ...
      {% endif %}


3. For loops

   .. code-block:: html

      {% for x in y %}
      ...
      {% endfor %}

   This will also inject a 0-based `loopcounter` into the context.

4. Include

   .. code-block:: html

      {% include other.tpl %}

   Note: the template using include must be loaded using a TemplateLoader.

   You can also add extra values to the context for the included template:

   .. code-block:: html

      {% include other.tpl key=value other=some.thing|woo %}

5. Load

   .. code-block:: html

      {% load libname %}

   Additional tag types can be loaded.

   Custom block tags can be written by extending ``stencil.BlockNode``.

   .. code-block:: python

      class MyTag(BlockNode):
          name = 'foo'  # The name matched in {% %}

          @classmethod
          def parse(cls, content, parser):
              '''
              Parse the string between "{% foo " and "%}"
              '''
              ...

          def render(self, context, output):
              '''
              Render your tag, and write it to the file-like `output`
              '''
              ...


Python 3
--------

Because of requirements, this project was written as Python2 compatible only.

For Python3 I would have used knights-templater and never tried this project at
all.

Currently to make this work on Python3 the steps are:

1. Replace "unicode" with "str"
2. Wrap the one use of map() with list()
3. Change the syntax for the one use of __metaclass__
