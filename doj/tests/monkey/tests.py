# -*- coding: utf-8 -*-

from django.test import TestCase


class MonkeyTestCase(TestCase):

    def setUp(self):
        pass

    def test_getcallargs(self):
        from inspect import getcallargs  # gets monkey-patched by DOJ

        f1 = lambda a, b, c: True
        f2 = lambda a, b, c, d=4, e=5, f=6: True
        f3 = lambda *args, **kwargs: True
        f4 = lambda: True

        self.assertRaises(TypeError, getcallargs, (f1,))
        self.assertRaises(TypeError, getcallargs, (f2,))
        self.assertRaises(TypeError, getcallargs, (f4, 1, 2, 3,))

        self.assertEqual(getcallargs(f1, 1, 2, 3), {'a': 1, 'c': 3, 'b': 2})
        self.assertEqual(getcallargs(f2, 1, 2, 3), {'a': 1, 'c': 3, 'b': 2, 'e': 5, 'd': 4, 'f': 6})
        self.assertEqual(getcallargs(f2, 1, 2, 3, d=7, e=8, f=9), {'a': 1, 'c': 3, 'b': 2, 'e': 8, 'd': 7, 'f': 9})
        self.assertEqual(getcallargs(f3, 1, 2, 3), {'args': (1, 2, 3), 'kwargs': {}})
        self.assertEqual(getcallargs(f3, 1, 2, 3, d=4, e=5, f=6), {'args': (1, 2, 3), 'kwargs': {'e': 5, 'd': 4, 'f': 6}})
        self.assertEqual(getcallargs(f4), {})

    def test_lazy(self):
        from django.utils import functional
        from django.utils.encoding import force_text

        lazy_unicode = functional.lazy(lambda: u'abc', unicode)()
        lazy_string = functional.lazy(lambda: 'abc', str)()

        self.assertEqual(force_text(lazy_unicode), 'abc')
        self.assertEqual(force_text(lazy_string), 'abc')
        self.assertEqual(unicode(lazy_unicode), 'abc')
        self.assertEqual(unicode(lazy_string), 'abc')
        self.assertEqual(str(lazy_unicode), 'abc')
        self.assertEqual(str(lazy_string), 'abc')

    def test_streaminghttpresponse(self):
        from django.http.response import StreamingHttpResponse

        streaming_content = []
        for _ in range(0, 100):
            streaming_content.append(b'The quick brown fox jumps over the lazy dog')

        streaming_response = StreamingHttpResponse(streaming_content)

        for l in streaming_response:
            self.assertEqual(l, b'The quick brown fox jumps over the lazy dog')