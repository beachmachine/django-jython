# -*- coding: utf-8 -*-

import doj.monkey.django_utils_functional_lazy
import doj.monkey.django_http_response_streaminghttpresponse


def install_monkey_patches():
    doj.monkey.django_utils_functional_lazy.install()
    doj.monkey.django_http_response_streaminghttpresponse.install()