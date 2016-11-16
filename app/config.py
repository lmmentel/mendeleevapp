# -*- coding: utf-8 -*-

import os


def parent_dir(path):
    '''Return the parent of a directory.'''

    return os.path.abspath(os.path.join(path, os.pardir))


class Configuration(object):

    APPLICATION_DIR = os.path.dirname(os.path.realpath(__file__))
    DEBUG = True
