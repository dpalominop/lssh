from fabistrano.deploy import *
from fabric.api import cd

"""create file .fabricrc with arguments:
user = ''
password = ''
remote_owner = ''
remote_group = ''
base_dir = ''
app_name = ''
env.restart_cmd = ''
And execute: fab -c .fabricrc my_task"""


env.hosts = ["10.123.120.196","10.123.120.197","10.123.120.198","10.123.120.199"]
env.pip_install_command = 'pip install -r requirements.txt'
env.git_clone = 'https://github.com/dpalominop/lssh.git'

@task
@with_defaults
def build_code():
    """Build code on all servers"""
    with cd("%s/%s/current"%(env.base_dir, env.app_name)):
        sudo_run('python setup.py clean')
        sudo_run('python setup.py build')
        sudo_run('python setup.py install')
# or
# env.wsgi_path = "app_name/apache.wsgi" # Relative path to the wsgi file to be touched on restart
