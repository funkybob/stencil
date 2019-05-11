.. Stencil documentation master file, created by
   sphinx-quickstart on Mon Aug 15 19:18:31 2016.

Welcome to Stencil's documentation!
===================================

Contents:

.. toctree::
   :maxdepth: 2

   writing
   using
   extending

Why?
----

There are plenty of template engines in Python, and I've even written my own
powerful, super-fast one (knights-templater), so why write another?

I was experimenting with AWS' Serverless concept, and was saddened to learn it
only supports Python 2.7 currently.  I wanted templating, but felt back-porting
K-T to Py2 just wasn't warranted.

So I figured, why not see how small I can make a functional template language?

Apparently, "under 400 lines of code" is the answer... (it's grown a little
since then :)
