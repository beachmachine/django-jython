# -*- coding: utf-8 -*-

import warnings

from django.conf import settings


class DojDeprecationWarning(DeprecationWarning):
    pass


def install_monkey_patches():
    if settings.DEBUG:
        warnings.simplefilter('always', DojDeprecationWarning)
        warnings.warn(u"The call of `install_monkey_patches` is deprecated "
                      u"and should be removed.", DojDeprecationWarning, 2)
