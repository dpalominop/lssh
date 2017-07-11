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

from distutils.core import setup

# import lssh specifics
from src.variables import __version__

if __name__ == '__main__':

    setup(name='lssh',
          version='%s' % __version__,
          description='Limited Secure SHell',
          long_description="""Limited Secure SHell (lssh) is lets you restrict the \
environment of any user. It provides an easily configurable shell: just \
choose a list of allowed commands for every limited account.""",
          author='Daniel Palomin',
          author_email='dapalominop@gmail.com',
          maintainer='Daniel Palomino',
          maintainer_email='dapalominop@gmail.com',
          keywords=['limited', 'shell', 'ssh', 'security', 'python'],
          url='https://github.com/dpalominop/lssh',
          license='GPL',
          platforms='UNIX',
          scripts=['bin/lssh'],
          package_dir={'lssh': 'lssh'},
          packages=['lssh'],
          data_files=[('/etc', ['etc/lssh.conf']),
                      ('/etc/logrotate.d', ['etc/logrotate.d/lssh']),
                      ('share/doc/lssh', ['README.md',
                                            'COPYING',
                                            'CHANGES']),
                      ('share/man/man1/', ['man/lssh.1'])],
          classifiers=[
            'Development Status :: 5 - Production/Stable',
            'Environment :: Console'
            'Intended Audience :: Advanced End Users',
            'Intended Audience :: System Administrators',
            'License :: OSI Approved :: GNU General Public License v3',
            'Operating System :: POSIX',
            'Programming Language :: Python',
            'Topic :: Security',
            'Topic :: System Shells',
            'Topic :: Terminals'
            ],
          )
