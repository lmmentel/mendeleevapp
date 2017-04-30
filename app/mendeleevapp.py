
# -*- coding: utf-8 -*-

from flask import Flask

from config import Configuration

__version__ = '0.2.0'

app = Flask(__name__)
app.config.from_object(Configuration)
