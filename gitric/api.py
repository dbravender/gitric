from __future__ import with_statement
from fabric.state import env
from fabric.api import (local, run, sudo, abort, task, cd, puts)
from fabric.context_managers import settings
from fabric.contrib.files import exists
from fabric.colors import green


@task
def allow_dirty():
    """ allow pushing even when the working copy is dirty """
    env.gitric_allow_dirty = True


@task
def force_push():
    """ allow pushing even when history will be lost """
    env.gitric_force_push = True


def git_init(repo_path, use_sudo=False):
    """ create a git repository if necessary [remote] """

    # check if it is a git repository yet
    if exists('%s/.git' % repo_path):
        return

    puts(green('Creating new git repository ') + repo_path)

    func = sudo if use_sudo else run

    # create repository folder if necessary
    func('mkdir -p %s' % repo_path, quiet=True)

    with cd(repo_path):
        # initialize the remote repository
        run('git init')

        # silence git complaints about pushes coming in on the current branch
        # the pushes only seed the immutable object store and do not modify the
        # working copy
        func('git config receive.denyCurrentBranch ignore')


def git_seed(repo_path, commit=None, ignore_untracked_files=False,
             use_sudo=False):
    """ seed a git repository (and create if necessary) [remote] """

    # check if the local repository is dirty
    dirty_working_copy = git_is_dirty(ignore_untracked_files)
    if dirty_working_copy:
        abort(
            'Working copy is dirty. This check can be overridden by\n'
            'importing gitric.api.allow_dirty and adding allow_dirty to your '
            'call.')

    # check if the remote repository exists and create it if necessary
    git_init(repo_path, use_sudo=use_sudo)

    # use specified commit or HEAD
    commit = commit or git_head_rev()

    # finish execution if remote repository has commit already
    if git_exists(repo_path, commit, use_sudo=use_sudo):
        puts(green('Commit ') + commit + green(' exists already'))
        return

    # push the commit to the remote repository
    #
    # (note that pushing to the master branch will not change the contents
    # of the working directory)

    puts(green('Pushing commit ') + commit)

    with settings(warn_only=True):
        force = ('gitric_force_push' in env) and '-f' or ''
        push = local(
            'git push git+ssh://%s@%s:%s%s %s:refs/heads/master %s' % (
                env.user, env.host, env.port, repo_path, commit, force))

    if push.failed:
        abort(
            '%s is a non-fast-forward\n'
            'push. The seed will abort so you don\'t lose information. '
            'If you are doing this\nintentionally import '
            'gitric.api.force_push and add it to your call.' % commit)


def git_exists(repo_path, commit, use_sudo=False):
    """ check if the specified commit exists in the repository [remote] """

    with cd(repo_path):
        func = sudo if use_sudo else run
        if func('git rev-list --max-count=1 %s' % commit,
                warn_only=True, quiet=True).succeeded:
            return True


def git_reset(repo_path, commit=None, use_sudo=False):
    """ reset the working directory to a specific commit [remote] """

    # use specified commit or HEAD
    commit = commit or git_head_rev()

    puts(green('Resetting to commit ') + commit)

    # reset the repository and working directory
    with cd(repo_path):
        func = sudo if use_sudo else run
        func('git reset --hard %s' % commit)


def git_head_rev():
    """ find the commit that is currently checked out [local] """
    return local('git rev-parse HEAD', capture=True)


def git_is_dirty(ignore_untracked_files):
    """ check if there are modifications in the repository [local] """

    if 'gitric_allow_dirty' in env:
        return False

    untracked_files = '--untracked-files=no' if ignore_untracked_files else ''
    return local('git status %s --porcelain' % untracked_files,
                 capture=True) != ''
