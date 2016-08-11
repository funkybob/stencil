# stencil
A minimalist template engine for Python


The goal of Stencil is to provide just enough of a template engine in a single file.

## What it can do

{{ var.from.context }}

Django style dotted-lookup variables rendering.

TODO: Filters


{% if condition %}
{% if not condition %}

...
{% endif %}

Boolean condition tests on dotted-lookup expressions.

{% for x in y %}
...
{% endfor %}

Simple look iteration.


## Coming soon

{% extends %} / {% block %}

Allowing template inheritance.
