# -*- coding: utf-8 -*-

from doj.monkey import install_monkey_patches

__VERSION = (1, 7, 0, 'b', 2)


def get_version():
    """
    Gets the version of the library
    :return: Version
    """
    return tuple(__VERSION)


install_monkey_patches()
