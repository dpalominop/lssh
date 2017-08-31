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
from __future__ import print_function
import sys
import shlex
import os
import subprocess
from src.constants import *
from src.builtins import *
from src.checkconfigdb import CheckConfig

import paramiko
import base64
from binascii import hexlify
import getpass
import select
import socket
import time
import traceback
from paramiko.py3compat import input, u

# windows does not have termios...
try:
    import termios
    import tty
    has_termios = True
except ImportError:
    has_termios = False


class lssh:
    shell = None
    client = None
    transport = None
    directory = None

    def __init__(self, credentials):
        self.credentials = credentials
        self.userconf = CheckConfig(self.credentials).returnconf()
        # Hash map to store built-in function name and reference as key and value
        self.built_in_cmds = {}

        # Register all built-in commands here
        self.registerCommand("exit", exit)
        self.registerCommand("vim", vim)

        #self.client = paramiko.client.SSHClient()
        #self.client.set_missing_host_key_policy(paramiko.client.AutoAddPolicy())

        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self.credentials['hostname'], self.credentials['port']))
        except Exception as e:
            print('*** Connect failed: ' + e.args[1])
            #traceback.print_exc()
            sys.exit(1)

    def verifyCommand(self, command):
        #if self.userconf['config_mtime'] != os.path.getmtime(self.userconf['configfile']):
        self.userconf = CheckConfig(self.credentials).returnconf()
        #self.prompt = '%s:~$ ' % self.setprompt(self.userconf)
        self.log = self.userconf['logpath']

        if self.tokenize(command)[0] in self.userconf['allowed']:
            return True
        else:
            return False

    def interactive_shell(self, chan):
        if has_termios:
            self.posix_shell(chan)
        else:
            self.windows_shell(chan)


    def posix_shell(self, chan):

        # get the current TTY attributes to reapply after
        # the remote shell is closed
        oldtty = termios.tcgetattr(sys.stdin)

        def resize_pty():
            # resize to match terminal size
            tty_height, tty_width = \
                    subprocess.check_output(['stty', 'size']).split()

            # try to resize, and catch it if we fail due to a closed connection
            try:
                chan.resize_pty(width=int(tty_width), height=int(tty_height))
            except paramiko.ssh_exception.SSHException:
                pass

        # wrap the whole thing in a try/finally construct to ensure
        # that exiting code for TTY handling runs
        try:
            stdin_fileno = sys.stdin.fileno()
            tty.setraw(stdin_fileno)
            tty.setcbreak(stdin_fileno)

            chan.settimeout(0.0)

            is_alive = True
            command = ''
            tab = False

            while is_alive:
                # resize on every iteration of the main loop
                resize_pty()

                # use a unix select call to wait until the remote shell
                # and stdin are ready for reading
                # this is the block until data is ready
                r, w, e = select.select([chan, sys.stdin], [], [])

                # if the channel is one of the ready objects, print
                # it out 1024 chars at a time
                if chan in r:
                    # try to do a read from the remote end and print to screen
                    try:
                        x = u(chan.recv(1024))

                        # remote close
                        if len(x) == 0:
                            is_alive = False
                        else:
                            # rely on 'print' to correctly handle encoding
                            if tab:
                                tab = False
                                if '\n' not in x:
                                    command = command + x

                            # rely on 'print' to correctly handle encoding
                            print(x, end='')
                            sys.stdout.flush()

                    # do nothing on a timeout, as this is an ordinary condition
                    except socket.timeout:
                        pass

                # if stdin is ready for reading
                if sys.stdin in r and is_alive:
                    # send a single character out at a time
                    # this is typically human input, so sending it one character at
                    # a time is the only correct action we can take

                    # use an os.read to prevent nasty buffering problem with shell
                    # history
                    x = os.read(stdin_fileno, 1)

                    # if this side of the connection closes, shut down gracefully
                    if len(x) == 0:
                        is_alive = False
                    else:

                        if x == chr(13): #Carriage Return
                            #Si el comando no está registrado:
                            if len(command) and not self.verifyCommand(command):
                                for i in command:
                                    chan.send(chr(127))
                                sys.stdout.flush()

                            command = ''
                        elif x == chr(9): #Horizontal Tab
                            tab = True
                        elif x == chr(127): #BackSpace
                            command = command[:-1]
                        elif x == chr(27): #Teclas direccion
                            pass
                        else:
                            command = command + x

                        chan.send(x)
            # close down the channel for send/recv
            # this is an explicit call most likely redundant with the operations
            # that caused an exit from the REPL, but unusual exit conditions can
            # cause this to be reached uncalled
            chan.shutdown(2)

        finally:
            termios.tcsetattr(sys.stdin, termios.TCSAFLUSH, oldtty)


    # thanks to Mike Looijmans for this code
    def windows_shell(self,chan):
        import threading

        sys.stdout.write("Line-buffered terminal emulation. Press F6 or ^Z to send EOF.\r\n\r\n")

        def writeall(sock):
            while True:
                data = sock.recv(256)
                if not data:
                    sys.stdout.write('\r\n*** EOF ***\r\n\r\n')
                    sys.stdout.flush()
                    break
                sys.stdout.write(data)
                sys.stdout.flush()

        writer = threading.Thread(target=writeall, args=(chan,))
        writer.start()

        try:
            while True:
                d = sys.stdin.read(1)
                if not d:
                    break
                chan.send(d)
        except EOFError:
            # user hit ^Z or F6
            pass

    def agent_auth(self, transport, username):
        """
        Attempt to authenticate to the given transport using any of the private
        keys available from an SSH agent.
        """

        agent = paramiko.Agent()
        agent_keys = agent.get_keys()
        if len(agent_keys) == 0:
            return

        for key in agent_keys:
            #print('Trying ssh-agent key %s' % hexlify(key.get_fingerprint()))
            try:
                transport.auth_publickey(username, key)
                os.write(sys.stdout.fileno(), '... success!\n')
                return
            except paramiko.SSHException:
                #print('... nope.')
                pass


    def manual_auth(self, username, hostname):
        try:
            pw = getpass.getpass('Password for %s@%s: ' % (username, hostname))
            self.transport.auth_password(username, pw)
        except paramiko.AuthenticationException:
            os.write(sys.stdout.fileno(), '*** Authentication failed. ***\n')
            sys.exit(1)

    def startConnection(self):
        try:
            self.transport = paramiko.Transport(self.sock)

            try:
                self.transport.start_client()
            except paramiko.SSHException:
                os.write(sys.stdout.fileno(), '*** SSH negotiation failed.\n')
                sys.exit(1)

            try:
                keys = paramiko.util.load_host_keys(os.path.expanduser('~/.ssh/known_hosts'))
            except IOError:
                try:
                    keys = paramiko.util.load_host_keys(os.path.expanduser('~/ssh/known_hosts'))
                except IOError:
                    os.write(sys.stdout.fileno(), '*** Unable to open host keys file\n')
                    keys = {}

            # check server's host key -- this is important.
            key = self.transport.get_remote_server_key()

            if self.credentials['hostname'] not in keys:
                os.write(sys.stdout.fileno(), '*** WARNING: Unknown host key!\n')
            elif key.get_name() not in keys[self.credentials['hostname']]:
                os.write(sys.stdout.fileno(), '*** WARNING: Unknown host key!\n')
            elif keys[self.credentials['hostname']][key.get_name()] != key:
                os.write(sys.stdout.fileno(), '*** WARNING: Host key has changed!!!\n')
                sys.exit(1)
            else:
                os.write(sys.stdout.fileno(), '*** Host key OK.\n')

            # get username
            if self.credentials['username'] == '':
                default_username = getpass.getuser()
                os.write(sys.stdout.fileno(), 'Username [%s]: ' % default_username)
                self.credentials['username'] = input()

                if len(self.credentials['username']) == 0:
                    self.credentials['username'] = default_username

            self.agent_auth(self.transport, self.credentials['username'])
            if not self.transport.is_authenticated():
                self.manual_auth(self.credentials['username'], self.credentials['hostname'])
            if not self.transport.is_authenticated():
                os.write(sys.stdout.fileno(), '*** Authentication failed. ***\n')
                self.transport.close()
                sys.exit(1)

            chan = self.transport.open_session()
            chan.get_pty()
            chan.invoke_shell()

            self.interactive_shell(chan)
            chan.close()
            self.transport.close()

        except Exception as e:
            os.write(sys.stdout.fileno(), '*** Caught exception: ' + str(e.__class__) + ': ' + str(e) + '\n')
            traceback.print_exc()
            try:
                self.transport.close()
            except:
                pass
            sys.exit(1)

    def tokenize(self, cmd):
        return shlex.split(cmd)

    # Register a built-in function to built-in command hash map
    def registerCommand(self, name, func):
        self.built_in_cmds[name] = func
