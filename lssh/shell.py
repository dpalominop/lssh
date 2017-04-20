import sys
import shlex
import os
from constants import *
from builtins import *

class LShell():
    def __init__(self):
        # Hash map to store built-in function name and reference as key and value
        self.built_in_cmds = {}

        # Register all built-in commands here
        self.register_command("cd", cd)
        self.register_command("exit", exit)

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
                sys.stdout.write('> ')
                sys.stdout.flush()

                #Read command input
                cmd = sys.stdin.readline()

                #tokenize command input
                cmd_tokens = self.tokenize(cmd)

                #Excute the command and retrieve new status
                status = self.execute(cmd_tokens)
            except (KeyboardInterrupt, SystemExit, EOFError):
                print "KeyboardInterrupt"
            except:
                print "Error Unknown"

    def main(self):
        self.shell_loop()

if __name__=="__main__":
    lshell = LShell()
    lshell.main()
