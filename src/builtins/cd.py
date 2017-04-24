import os
from src.constants import *

def cd(args):
    if args:
        os.chdir(args[0])
    else:
        from os.path import expanduser
        os.chdir(expanduser("~"))
    
    return SHELL_STATUS_RUN