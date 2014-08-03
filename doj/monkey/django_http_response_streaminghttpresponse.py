# -*- coding: utf-8 -*-
"""
In Jython 2.7b2 a class' __iter__ method cannot return `itertools.map(f, l)`
or `itertools.imap(f, l)` so such objects cannot be processed in a for loop.

Refers to bug: http://bugs.jython.org/issue2015
"""

from django.http.response import StreamingHttpResponse


def install():
    # replacing the original function
    StreamingHttpResponse.__iter__ = lambda o: iter(o.streaming_content)