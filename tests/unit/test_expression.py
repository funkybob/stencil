import unittest

from stencil import Template


class ExpressionTests(unittest.TestCase):

    def test_function(self):
        t = Template('Test {{f("abc")}}').render({"f": lambda x: x.title() })

        self.assertEqual(t, 'Test Abc')

    def test_function_argument(self):
        def double(a):
            return a * 2

        t = Template('Test {{double(double(1))}}').render({"double": double})

        self.assertEqual(t, 'Test 4')
