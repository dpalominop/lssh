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

import sys
import shlex
import os
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
            print('*** Connect failed: ' + str(e))
            traceback.print_exc()
            sys.exit(1)

    def closeConnection(self):
        if(self.client != None):
            self.client.close()
            self.transport.close()
            #self.sftp.close()

    def openShell(self, term='vt100', width=80, height=24, width_pixels=0, height_pixels=0, environment=None):
        self.shell = self.client.invoke_shell(term=term, width=width, height=height, width_pixels=width_pixels, height_pixels=height_pixels, environment=environment)
        self.printShell('')

    def verifyCommand(self, command):
        #if self.userconf['config_mtime'] != os.path.getmtime(self.userconf['configfile']):
        self.userconf = CheckConfig(self.credentials).returnconf()
        #self.prompt = '%s:~$ ' % self.setprompt(self.userconf)
        self.log = self.userconf['logpath']


        if self.tokenize(command)[0] in self.userconf['allowed']:
            return True
        else:
            return False

    def sendCommand(self, command):
        if(self.shell):
            # Extract command name and arguments from tokens
            cmd_tokens = self.tokenize(command)
            cmd_name = cmd_tokens[0]
            cmd_args = cmd_tokens[1:]

            # If the command is a built-in command, invoke its function with arguments
            if cmd_name in self.built_in_cmds:
                return self.built_in_cmds[cmd_name](cmd_args, obj=self)

            self.shell.send(command)
            self.printShell(command)

            return SHELL_STATUS_RUN
        else:
            print("Shell not opened.")
            return SHELL_STATUS_STOP

    def printShell(self, command):
        strdata = ''
        while not strdata.endswith('$ '):
            # Print data when available
            if self.shell != None and self.shell.recv_ready():
                alldata = self.shell.recv(1024)
                while self.shell.recv_ready():
                    alldata += self.shell.recv(1024)
                strdata += str(alldata)

        #strdata = strdata.encode("utf-8")
        strdata.replace('\r', '')
        self.directory = strdata.rsplit('\n', 1)[1]

        print strdata.lstrip(command).rstrip(self.directory).strip('\n\r')

    def interactive_shell(self, chan):
        if has_termios:
            self.posix_shell(chan)
        else:
            self.windows_shell(chan)


    def posix_shell(self, chan):
        import select

        oldtty = termios.tcgetattr(sys.stdin)
        command = ''
        tab = False
        try:
            tty.setraw(sys.stdin.fileno())
            tty.setcbreak(sys.stdin.fileno())
            chan.settimeout(0.0)

            while True:
                r, w, e = select.select([chan, sys.stdin], [], [])
                if chan in r:
                    try:
                        x = u(chan.recv(1024))
                        if len(x) == 0:
                            sys.stdout.write('\r\n*** EOF\r\n')
                            break

                        if tab:
                            tab = False
                            if '\n' not in x:
                                command = command + x

                        sys.stdout.write(x)
                        sys.stdout.flush()
                    except socket.timeout:
                        pass

                if sys.stdin in r:
                    x = sys.stdin.read(1)
                    if len(x) == 0:
                        sys.stdout.write('\r\n***--------')
                        break

                    if x == chr(13): #Carriage Return
                        #sys.stdout.write('\ncomando:')
                        #sys.stdout.write(command)
                        #sys.stdout.flush()
                        if len(command) and not self.verifyCommand(command):
                            for i in command:
                                chan.send(chr(127))
                            sys.stdout.flush()

                        command = ''
                    elif x == chr(9): #Horizontal Tab
                        tab = True
                    elif x == chr(127): #BackSpace
                        command = command[:-1]
                    else:
                        command = command + x

                    chan.send(x)

        finally:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, oldtty)


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
            print('Trying ssh-agent key %s' % hexlify(key.get_fingerprint()))
            try:
                transport.auth_publickey(username, key)
                print('... success!')
                return
            except paramiko.SSHException:
                print('... nope.')


    def manual_auth(self, username, hostname):
        default_auth = 'p'
        auth = input('Auth by (p)assword, (r)sa key, or (d)ss key? [%s] ' % default_auth)
        if len(auth) == 0:
            auth = default_auth

        if auth == 'r':
            default_path = os.path.join(os.environ['HOME'], '.ssh', 'id_rsa')
            path = input('RSA key [%s]: ' % default_path)
            if len(path) == 0:
                path = default_path
            try:
                key = paramiko.RSAKey.from_private_key_file(path)
            except paramiko.PasswordRequiredException:
                password = getpass.getpass('RSA key password: ')
                key = paramiko.RSAKey.from_private_key_file(path, password)
            self.transport.auth_publickey(username, key)
        elif auth == 'd':
            default_path = os.path.join(os.environ['HOME'], '.ssh', 'id_dsa')
            path = input('DSS key [%s]: ' % default_path)
            if len(path) == 0:
                path = default_path
            try:
                key = paramiko.DSSKey.from_private_key_file(path)
            except paramiko.PasswordRequiredException:
                password = getpass.getpass('DSS key password: ')
                key = paramiko.DSSKey.from_private_key_file(path, password)
            self.transport.auth_publickey(username, key)
        else:
            try:
                pw = getpass.getpass('Password for %s@%s: ' % (username, hostname))
                self.transport.auth_password(username, pw)
            except paramiko.AuthenticationException:
                print('*** Authentication failed. ***')
                sys.exit(1)

    def startConnection(self):
        try:
            self.transport = paramiko.Transport(self.sock)
            #self.sftp = paramiko.SFTPClient.from_transport(self.transport)

            try:
                self.transport.start_client()
            except paramiko.SSHException:
                print('*** SSH negotiation failed.')
                sys.exit(1)

            try:
                keys = paramiko.util.load_host_keys(os.path.expanduser('~/.ssh/known_hosts'))
            except IOError:
                try:
                    keys = paramiko.util.load_host_keys(os.path.expanduser('~/ssh/known_hosts'))
                except IOError:
                    print('*** Unable to open host keys file')
                    keys = {}

            # check server's host key -- this is important.
            key = self.transport.get_remote_server_key()
            if self.credentials['hostname'] not in keys:
                print('*** WARNING: Unknown host key!')
            elif key.get_name() not in keys[self.credentials['hostname']]:
                print('*** WARNING: Unknown host key!')
            elif keys[self.credentials['hostname']][key.get_name()] != key:
                print('*** WARNING: Host key has changed!!!')
                sys.exit(1)
            else:
                print('*** Host key OK.')

            # get username
            if self.credentials['username'] == '':
                default_username = getpass.getuser()
                self.credentials['username'] = input('Username [%s]: ' % default_username)
                if len(self.credentials['username']) == 0:
                    self.credentials['username'] = default_username

            self.agent_auth(self.transport, self.credentials['username'])
            if not self.transport.is_authenticated():
                self.manual_auth(self.credentials['username'], self.credentials['hostname'])
            if not self.transport.is_authenticated():
                print('*** Authentication failed. ***')
                self.transport.close()
                sys.exit(1)

            chan = self.transport.open_session()
            chan.get_pty()
            chan.invoke_shell()
            print('*** Here we go!\n')
            self.interactive_shell(chan)
            chan.close()
            self.transport.close()

        except Exception as e:
            print('*** Caught exception: ' + str(e.__class__) + ': ' + str(e))
            traceback.print_exc()
            try:
                self.transport.close()
            except:
                pass
            sys.exit(1)

        # try:
        #     self.client.connect(host, username=username, password=password, look_for_keys=False)
        #     self.transport = paramiko.Transport((host, port))
        #     self.transport.connect(username=username, password=password)

        #     self.sftp = paramiko.SFTPClient.from_transport(self.transport)

        # except paramiko.BadHostKeyException:
        #     print "Server host key could not be verified."
        #     return False
        # except paramiko.AuthenticationException:
        #     print "Authentication Failed"
        #     return False
        # except paramiko.SSHException:
        #     print "Any other error connecting or establishing an SSH session"
        #     return False
        # except:
        #     print "Other Error, maybe in socket creation."
        #     return False

        # return True

    def tokenize(self, cmd):
        return shlex.split(cmd)

    # Register a built-in function to built-in command hash map
    def registerCommand(self, name, func):
        self.built_in_cmds[name] = func

    def shell_loop(self):
        status = SHELL_STATUS_RUN

        while status == SHELL_STATUS_RUN:
            #Display a command prompt
            sys.stdout.write(self.directory)
            sys.stdout.flush()

            #Read command input
            cmd = sys.stdin.readline()
            if cmd == chr(10):
                sys.stdout.flush()
            else:
                if self.verifyCommand(cmd):
                    status = self.sendCommand(cmd)
                else:
                    print "Command Not Permitted"

        self.closeConnection()
