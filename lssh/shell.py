import sys
import shlex
import os
from constants import *
from builtins import *

import paramiko
from getpass import getpass

class lssh:
    shell = None
    client = None
    transport = None
    directory = None

    def __init__(self):
        # Hash map to store built-in function name and reference as key and value
        self.built_in_cmds = {}

        # Register all built-in commands here
        self.register_command("exit", exit)

        self.client = paramiko.client.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.client.AutoAddPolicy())

    def closeConnection(self):
        if(self.client != None):
            self.client.close()
            self.transport.close()

    def openShell(self, term='vt100', width=80, height=24, width_pixels=0, height_pixels=0, environment=None):
        self.shell = self.client.invoke_shell(term=term, width=width, height=height, width_pixels=width_pixels, height_pixels=height_pixels, environment=environment)
        self.printShell('')

    def verifyCommand(self, commands):
        return True

    def sendCommand(self, command):
        if(self.shell):
            # Extract command name and arguments from tokens
            cmd_tokens = self.tokenize(command)
            cmd_name = cmd_tokens[0]
            cmd_args = cmd_tokens[1:]

            # If the command is a built-in command, invoke its function with arguments
            if cmd_name in self.built_in_cmds:
                return self.built_in_cmds[cmd_name](cmd_args)

            self.shell.send(command)
            self.printShell(command)

            return SHELL_STATUS_RUN
        else:
            print("Shell not opened.")
            return SHELL_STATUS_STOP

    def printShell(self, command):
        strdata = ''
        while "$" not in strdata:
            # Print data when available
            if self.shell != None and self.shell.recv_ready():
                alldata = self.shell.recv(1024)
                while self.shell.recv_ready():
                    alldata += self.shell.recv(1024)
                strdata += str(alldata).encode("utf-8")

        strdata.replace('\r', '')
        self.directory = strdata.rsplit('\n', 1)[1]
        print strdata.lstrip(command).rstrip(self.directory).strip('\n\r')

    def startConnection(self, host='192.168.0.1', username='username', password='password', port=22):
        
        try:
            self.client.connect(host, username=username, password=password, look_for_keys=False)
            self.transport = paramiko.Transport((host, port))
            self.transport.connect(username=username, password=password)

        except paramiko.BadHostKeyException:
            print "Server host key could not be verified."
            return False
        except paramiko.AuthenticationException:
            print "Authentication Failed"
            return False
        except paramiko.SSHException:
            print "Any other error connecting or establishing an SSH session"
            return False
        except:
            print "Other Error, maybe in socket creation."
            return False
        
        return True

    def tokenize(self, cmd):
        return shlex.split(cmd)

    # Register a built-in function to built-in command hash map
    def register_command(self, name, func):
        self.built_in_cmds[name] = func

    def shell_loop(self):
        status = SHELL_STATUS_RUN

        while status == SHELL_STATUS_RUN:
            try:
                #Display a command prompt
                sys.stdout.write(self.directory)
                sys.stdout.flush()

                #Read command input
                cmd = sys.stdin.readline()

                if self.verifyCommand(cmd):
                    status = self.sendCommand(cmd)
                else:
                    print "Command Not Permitteds"

            except (KeyboardInterrupt, SystemExit, EOFError):
                print "KeyboardInterrupt"

            except:
                print "Error Unknown"


if __name__=="__main__":
    ssh = lssh()

    if len(sys.argv) == 1:
        print "usage: python -m lssh.shell username@host"
    else:
        password = getpass(prompt=sys.argv[1]+' password: ')

        if ssh.startConnection(host=sys.argv[1].split('@')[1], username=sys.argv[1].split('@')[0], password=password):
            ssh.openShell()
            ssh.shell_loop()
