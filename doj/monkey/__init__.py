# -*- coding: utf-8 -*-


def install_monkey_patches():
    # Make sure we install monkey patches only once
    if not getattr(install_monkey_patches, 'installed', False):
        setattr(install_monkey_patches, 'installed', True)

        import doj.monkey.datetime_tojava
        doj.monkey.datetime_tojava.install()

        import doj.monkey.django_utils_functional_lazy
        doj.monkey.django_utils_functional_lazy.install()

        import doj.monkey.django_http_response_streaminghttpresponse
        doj.monkey.django_http_response_streaminghttpresponse.install()

        import doj.monkey.inspect_getcallargs
        doj.monkey.inspect_getcallargs.install()
