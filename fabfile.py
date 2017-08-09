from fabistrano.deploy import *
from fabric.api import cd

usernme =  raw_input('Servers Username')
password = raw_input('Servers Password')
env.user = username
env.password = password
env.hosts = ["10.123.120.196","10.123.120.197","10.123.120.198","10.123.120.199"]
env.base_dir = '/usr/local/src' # Set to your app's directory
env.app_name = 'lssh' # This will deploy the app to /www/app_name.com/
env.remote_owner = username
env.remote_group = username
env.pip_install_command = 'pip install -r requirements.txt'
env.git_clone = 'git@github.com:dpalominop/lssh.git' # Your git url
env.restart_cmd = "python %(current_release)s/setup.py install"# Restart command

@task
@with_defaults
def build_code():
    """Build code on all servers"""
    with cd("%s/%s/current"%(env.base_dir, env.app_name)):
        sudo_run('python setup.py build install')
# or
# env.wsgi_path = "app_name/apache.wsgi" # Relative path to the wsgi file to be touched on restart