=================
Writing Templates
=================

Templates are just plain text files, with special notation (called 'tags') to
indicate where the engine should take action.

There are 3 basic types of tags:

- var
- block
- comment

Comments
========

Comment tags are discarded during parsing, and are only for the benefit of
future template editors.  They have no impact on rendering performance.


Variables
=========

Var tags are used to display the values of variables.  They look like this:

.. code-block:: html

   Hello {{ name }}

In this case, the ``{{ name }}`` block will render as the value of the `name`
value in the Context.

You can delve into data strucures using a "dot notation", for instance:

.. code-block:: html

   {{ user.first_name.title }}

If the ``user`` object has a string attribute of ``first_name``, this will
render the output of calling its ``title`` method.

Additionally, the values can be pushed through `filters`.  An example might be
if you wrote a tool for format a number as a dollar string.

.. code-block:: html

   {{ product.price|dollar_format }}

Which might render as:

.. code-block:: html

    $129.95

Filters can also take extra arguments:

.. code-block:: html

   {{ product.price|float_format,%0.2f,$ }}

There are currently no built in filters.  You can add them to your render
Context at run time.

Block Tags
==========

Block tags perform some action, may render some output, and may "contain" other tags.

.. code-block:: html

   {% include another.html %}

-------------
Built In Tags
-------------

for
---

The ``for`` tag allows you to loop over a sequence.

.. code-block:: html

    {% for x in y %}
    ...
    {% endfor %}

The ``for`` tag also support and ``else`` block.  It will be used if sequence
to be iterated is empty.

.. code-block:: html

   {% for x in empty_list %}
   ...
   {% else %}
   Nothing to show.
   {% endfor %}

if
--

The ``if`` tag allows for simple flow control based on a truthy test.

.. code-block:: html

   {% if something %}
   Success!
   {% endif %}

It also supports negative cases:

.. code-block:: html

   {% if not something %}
   Failure!
   {% endif %}

And, like the ``for`` tag, it supports an ``else`` block:

.. code-block:: html

   {% if something %}
   Success!
   {% else %}
   Failure!
   {% endif %}

"Truthiness" is based on the Pythocept.  Here are some things that are "truthy":

- True
- non-empty strings
- non-empty lists or dicts
- non-zero values

Conversely, things that are "falsey" are:

- False
- empty strings
- 0 and 0.0
- empty lists and dicts

include
-------

The ``include`` tag lets you render another template inline, using the current
context.

.. code-block:: html

    {% include side_menu.html %}

Additionally, you can pass extra expressions to be added to the
context whilst the other template is being rendered.

.. code-block:: html

   {% include form_field.html field=current_field %}

load
----

This tag lets you load other code modules to add new tags to use in this
template.  See _extending for more details.

.. code-block:: html

   {% load myproject.tags %}

The value passed is a Python import path.

extends and block
-----------------

The ``extends`` tag allows the use of template inheritance.  A `base` template
can denote ``blocks`` of content which can be overridden by templates which
``extend`` it.

Say we have the following base template:

.. code-block:: html

    <!DOCTYPE html>
    <html lan="en">
        <head>
            <title>{% block title %}Welcome!{% endblock %}</title>
            <link rel="stylesheet" type="text/css" href="/static/css/base.css">
            {% block extra_head %}{% endblock %}
        </head>
        <body>
            <header>
                <h1>{% block header %}Welcome!{% endblock %}</h1>
            </header>
            <main>
            {% block content %}{% endblock %}
            </main>
            <footer>
                <p>&copy; 2016 Me!</p>
            </footer>
            {% block footer_scripts %}{% endblock %}
        </body>
    </html>

Now, when rendered itself, it will show as:

.. code-block:: html

    <!DOCTYPE html>
    <html lan="en">
        <head>
            <title>Welcome!</title>
            <link rel="stylesheet" type="text/css" href="/static/css/base.css">

        </head>
        <body>
            <header>
                <h1>Welcome!</h1>
            </header>
            <main>

            </main>
            <footer>
                <p>&copy; 2016 Me!</p>
            </footer>

        </body>
    </html>

However, if we write another template which extends this one, we just have to
write now the ``blocks`` we want to override:

.. code-block:: html

    {% extends base.html %}

    {% block title %}My Title!{% endblock %}

    {% block content %}
    Welcome to my first page!
    {% endblock %}

This will override only the two given blocks content.

Any content outside of ``block`` tags will be ignored.
