import sys
sys.path.append('../')
from fabric.api import task
from fabric.state import env
from gitric.api import git_seed, git_reset, allow_dirty, force_push  # noqa


@task
def prod():
    '''an example production deployment'''
    env.user = 'test-deployer'


@task
def deploy(commit=None):
    '''an example deploy action'''
    repo_path = '/home/test-deployer/test-repo'
    git_seed(repo_path, commit)
    # stop your service here
    git_reset(repo_path, commit)
    # restart your service here
