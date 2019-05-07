=================
Writing Templates
=================

Templates are just plain text files, with special notation (called 'tags') to
indicate where the engine should take action.

There are 3 basic types of tags:

- var
- block
- comment


Expressions
===========

At several points in the syntax, an Expression can be used.

They start with a value, optionally followed by a series of filters.

A value can be:

- an integer
- a float
- a string
- a lookup

A lookup will try to delve into the Context.  For example the expression
``name`` will look for Context['name'].

However, lookups can delve deeper.  They will attempt dict lookups, attribute
lookup, and list indexing (in that order).  Also, if the resulting value is
callable, it will be called.

So, to get the ``name`` attribute of your ``user`` object, and call its
``title`` method, the expression would be ``name:user:title``.

Filters allow you to pass the value (and possibly more arguments) to helper
functions.  For example, you might have a dollar format function:

.. code-block:: python

    def dollar_format(value, currency_symbol='$'):
        return "%s%0.2f" % (currency_symbol, float(value))

Then by passing this into your `Context`, you can in your templates use the
expression ``product:price|dollar_format``, or even override the currency
symbol using ``product:price|dollar_format:'¥'``.

Filters can be chained, one after another.

There are currently no default filters provided with Stencil.

Comments
========

Comment tags are discarded during parsing, and are only for the benefit of
future template editors.  They have no impact on rendering performance.

Variables
=========

Var tags are used to display the values of variables.  They look like this:

.. code-block:: html

   Hello {{ expr }}

Block Tags
==========

Block tags perform some action, may render some output, and may "contain" other tags.

.. code-block:: html

   {% include 'another.html' %}

-------------
Built In Tags
-------------

for
---

The ``for`` tag allows you to loop over a sequence.

.. code-block:: html

    {% for x in expr %}
    …
    {% endfor %}

The ``for`` tag also support and ``else`` block.  It will be used if sequence
to be iterated is empty.

.. code-block:: html

   {% for x in empty_list %}
   …
   {% else %}
   Nothing to show.
   {% endfor %}

if
--

The ``if`` tag allows for simple flow control based on a truthy test.

.. code-block:: html

   {% if expr %}
   Success!
   {% endif %}

It also supports negative cases:

.. code-block:: html

   {% if not expr %}
   Failure!
   {% endif %}

And, like the ``for`` tag, it supports an ``else`` block:

.. code-block:: html

   {% if expr %}
   Success!
   {% else %}
   Failure!
   {% endif %}

"Truthiness" is based on the Python concept. Here are some things that are
"truthy":

- True
- non-empty strings
- non-empty lists or dicts
- non-zero values

Conversely, things that are "falsy" are:

- False
- empty strings
- 0 and 0.0
- empty lists and dicts

include
-------

The ``include`` tag lets you render another template inline, using the current
context.

.. code-block:: html

    {% include expr %}

Additionally, you can pass extra expressions to be added to the
context whilst the other template is being rendered.

.. code-block:: html

   {% include form_field.html field=current_field %}

load
----

This tag lets you load other code modules to add new tags to use in this
template.  See :ref:`extending_tags` for more details.

.. code-block:: html

   {% load 'myproject.tags' %}

The value passed is a Python import path.

extends and block
-----------------

The ``extends`` tag allows the use of template inheritance.  A `base` template
can denote ``blocks`` of content which can be overridden by templates which
``extend`` it.

.. caution::

   The ``extends`` tag only works properly if it is the *very first* thing in
   your template.

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

    {% extends 'base.html' %}

    {% block title %}My Title!{% endblock %}

    {% block content %}
    Welcome to my first page!
    {% endblock %}

This will override only the two given blocks content.

Any content outside of ``block`` tags will be ignored.

with
----

Using ``with`` you can temporarily assign new values in the context from
expressions.  This can help avoid repeated work.

.. code-block:: html

   {% with url=page|make_url %}
   <a href="{{ url }}" class="link {% if url|is_current_url %}current{% endif %}">{{ page:title }}</a>
   {% endwith %}


case/when
---------

Allows switching between multiple blocks of template depending on the value of
a variable.

.. code-block:: html

   {% case foo.bar %}
   {% when 1 %}
   You got one!
   {% when 2 %}
   You got two!
   {% else %}
   You got some!
   {% endcase %}

The optional `{% else %}` clause is used if no when cases match.
