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
        #self.register_command("cd", cd)
        self.register_command("exit", exit)

        #self.cl_ssh = paramiko.SSHClient()
        #self.cl_ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        self.client = paramiko.client.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.client.AutoAddPolicy())

    def closeConnection(self):
        if(self.client != None):
            self.client.close()
            self.transport.close()

    def openShell(self):
        self.shell = self.client.invoke_shell(term='vt100')
        self.printShell('')

    #def verifyCommand(self, commands):
    #    return True

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
        #global connection
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
        #print "last char: "+strdata[len(strdata)-1]

    def startConnection(self, host='10.118.181.126', username='dpalominop', password='T3v3r1rt0p', port=22):
        
        try:
            #self.cl_ssh.connect(host, username=username, password=password)

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

    ##def SSHCommand(self, cmd_tokens):
        # Extract command name and arguments from tokens
        ##cmd_name = cmd_tokens[0]
        ##cmd_args = cmd_tokens[1:]

        # If the command is a built-in command, invoke its function with arguments
        ##if cmd_name == "exit":
        ##    self.SSHClose()
        ##    return SHELL_STATUS_STOP

        ##stdin, stdout, stderr = self.cl_ssh.exec_command(' '.join(cmd_tokens))
        ##for line in stdout:
        ##    print(line.strip('\n'))

        ##return SHELL_STATUS_RUN
        
    #def SSHClose(self):
        #self.cl_ssh.close()

    def tokenize(self, cmd):
        return shlex.split(cmd)

    def execute(self, cmd_tokens):
        # Extract command name and arguments from tokens
        cmd_name = cmd_tokens[0]
        cmd_args = cmd_tokens[1:]

        # If the command is a built-in command, invoke its function with arguments
        if cmd_name in self.built_in_cmds:
            return self.built_in_cmds[cmd_name](cmd_args)

        #Fork a child shell process
        # If the current process is a child process, its `pid` is set to `0`
        # else the current process is a parent process and the value of `pid`
        # is the process id of its child process.
        pid = os.fork()

        if pid==0:
        #Child process
            #Replace the child shell process with the program with exec
            os.execvp(cmd_name,cmd_args or [cmd_name])
        elif pid>0:
        #Parent process
            while True:
                # Wait response status from its child process (identified with pid)
                pid, status = os.waitpid(pid, 0)

                # Finish waiting if its child process exits normally
                # or is terminated by a signal
                if os.WIFEXITED(status) or os.WIFSIGNALED(status):
                    break

        # Return status indicating to wait for next command in shell_loop
        return SHELL_STATUS_RUN

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

                #tokenize command input
                #cmd_tokens = self.tokenize(cmd)

                #Excute the command and retrieve new status
                ##status = self.execute(cmd_tokens)
                #status = self.SSHCommand(cmd_tokens)
                #if self.verifyCommand(cmd):
                status = self.sendCommand(cmd)
                #else:
                #    print "Command Not Permitteds"

            except (KeyboardInterrupt, SystemExit, EOFError):
                print "KeyboardInterrupt"
            except:
                print "Error Unknown"

    #def main(self):
        #self.shell_loop()

if __name__=="__main__":
    ssh = lssh()

    if len(sys.argv) == 1:
        print "usage: python -m lssh.shell username@host"
    else:
        password = getpass(prompt=sys.argv[1]+' password: ')

        if ssh.startConnection(host=sys.argv[1].split('@')[1], username=sys.argv[1].split('@')[0], password=password):
            ssh.openShell()
            ssh.shell_loop()
