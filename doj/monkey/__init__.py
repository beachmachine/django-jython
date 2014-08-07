# -*- coding: utf-8 -*-

import doj.monkey.django_utils_functional_lazy
import doj.monkey.django_http_response_streaminghttpresponse
import doj.monkey.inspect_getcallargs


def install_monkey_patches():
    # Make sure we install monkey patches only once
    if not getattr(install_monkey_patches, 'installed', False):
        setattr(install_monkey_patches, 'installed', True)

        doj.monkey.django_utils_functional_lazy.install()
        doj.monkey.django_http_response_streaminghttpresponse.install()
        doj.monkey.inspect_getcallargs.install()