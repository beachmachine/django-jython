from django import VERSION

if VERSION[0] == 1 and VERSION[1] == 5:
    from doj.monkey.dj15_lazy import *
