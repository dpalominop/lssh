#!/usr/bin/env python
#
#  Copyright (C) 2017-2018 Daniel Palomino (@dpalominop) <dapalominop@gmail.com>
#
#  This file is part of lssh
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os
from src.constants import *
from subprocess import call, Popen, PIPE
import datetime

def vim(args, obj=None):
    path = obj.directory.rsplit(":")[1].rsplit('$')[0]+'/'

    if path.startswith('~'):
        path=path[2:]

    try:
        obj.sftp.get(path+args[0], '/tmp/'+args[0])
        p = Popen('rvim /tmp/'+args[0],shell=True)
        p.communicate()

        obj.sftp.put('/tmp/'+args[0], path+args[0])
        os.system('rm /tmp/'+args[0])
    except IOError:
        print "File not exists"

    return SHELL_STATUS_RUN