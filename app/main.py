# -*- coding: utf-8 -*-

'''Entry point to all things to avoid circular imports.'''

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))


from mendeleevapp import app
from views import *


if __name__ == '__main__':

    app.run(debug=True)
