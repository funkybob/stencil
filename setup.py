# -*- coding: utf-8 -*-

import unittest

from setuptools import setup


def test_suite():
    """Return tests suite."""
    test_loader = unittest.defaultTestLoader
    return test_loader.discover('tests', pattern='test*.py')


setup(
    name='stencil-template',
    version='4.0.1',
    description='A template engine light enough to embed in your project.',
    url='https://github.com/funkybob/stencil/',
    author='Curtis Maloney',
    license='CC BY-SA 3.0',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Programming Language :: Python :: 3',
    ],
    keywords='template',
    py_modules=['stencil'],
    test_suite='__main__.test_suite',
)
