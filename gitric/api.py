from __future__ import with_statement

import os
from operator import itemgetter
import re

from fabric.api import cd, run, puts, sudo, task, abort, local, require
from fabric.state import env
from fabric.colors import green
from fabric.contrib.files import exists
from fabric.context_managers import settings
import posixpath


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

    with cd(repo_path), settings(warn_only=True):
        # initialize the remote repository
        if func('git init').failed:
            func('git init-db')

        # silence git complaints about pushes coming in on the current branch
        # the pushes only seed the immutable object store and do not modify the
        # working copy
        func('git config receive.denyCurrentBranch ignore')


def git_seed(repo_path, commit=None, ignore_untracked_files=False,
             use_sudo=False, submodules=False):
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

    if submodules:
        git_seed_submodules(repo_path, commit, ignore_untracked_files, use_sudo)


def git_reset(repo_path, commit=None, use_sudo=False, submodules=False):
    """ reset the working directory to a specific commit [remote] """

    # use specified commit or HEAD
    commit = commit or git_head_rev()

    puts(green('Resetting to commit ') + commit)

    # reset the repository and working directory
    with cd(repo_path):
        func = sudo if use_sudo else run
        func('git reset --hard %s' % commit)

    if submodules:
        git_reset_submodules(repo_path, commit, use_sudo)


def git_local_submodules(commit=None):
    """ get all submodules in local repository """
    modules_path = [itemgetter(0, 1)(x.split(' ')) for x in local(
        "git submodule --quiet foreach 'echo $name $path $sha1 $toplevel'", capture=True).split('\n')]

    # use specified commit or HEAD
    commit = commit or git_head_rev()
    submodules = {}  # key is a tuple of (full_path, module path) value is module revision which is corresponding with parent commit.
    for full_path, module_path in modules_path:
        module_rev = re.compile(r'\s+?').split(local('git ls-tree %s %s' % (commit, module_path), capture=True))[2]
        submodules[(full_path, module_path)] = module_rev
    return submodules


def git_seed_submodule(repo_path, submodule_path, commit, ignore_untracked_files=False, use_sudo=False):

    # check if the local repository is dirty
    dirty_working_copy = git_is_dirty(ignore_untracked_files)
    if dirty_working_copy:
        abort(
            'Working copy is dirty. This check can be overridden by\n'
            'importing gitric.api.allow_dirty and adding allow_dirty to your '
            'call.')

    # check if the remote repository exists and create it if necessary
    git_init(repo_path, use_sudo=use_sudo)

    # push the commit to the remote repository
    #
    # (note that pushing to the master branch will not change the contents
    # of the working directory)

    puts(green('Pushing commit ') + commit)

    with settings(warn_only=True):
        force = ('gitric_force_push' in env) and '-f' or ''
        push = local(
            'git submodule --quiet foreach \'[ $path != "%s" ] || git push git+ssh://%s@%s:%s%s %s:refs/heads/master %s\'' % (
                submodule_path, env.user, env.host, env.port, repo_path, commit, force))

    if push.failed:
        abort(
            '%s is a non-fast-forward\n'
            'push. The seed will abort so you don\'t lose information. '
            'If you are doing this\nintentionally import '
            'gitric.api.force_push and add it to your call.' % commit)


def git_seed_submodules(repo_path, commit=None, ignore_untracked_files=False, use_sudo=False):
    """ seed submodules in a git repository (and create if necessary) [remote] """
    submodules = git_local_submodules(commit)
    for full_path, path in submodules:
        commit = submodules[(full_path, path)]
        puts(green('Pushing submodule ') + path)
        git_seed_submodule(repo_path + os.path.sep + full_path,
                           path, commit,
                           ignore_untracked_files=ignore_untracked_files,
                           use_sudo=use_sudo)


def git_reset_submodules(repo_path, commit=None, use_sudo=False):
    """ reset submodules in the working directory to a specific commit [remote] """

    submodules = git_local_submodules(commit)
    for full_path, path in submodules:
        rev = submodules[(full_path, path)]
        puts(green('Resetting submodule ' + full_path + ' to commit ') + rev)
        # reset the repository and working directory
        with cd(repo_path + os.path.sep + full_path):
            func = sudo if use_sudo else run
            func('git reset --hard %s' % rev)


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


def init_bluegreen():
    require('bluegreen_root', 'bluegreen_ports')
    env.green_path = posixpath.join(env.bluegreen_root, 'green')
    env.blue_path = posixpath.join(env.bluegreen_root, 'blue')
    env.next_path_abs = posixpath.join(env.bluegreen_root, 'next')
    env.live_path_abs = posixpath.join(env.bluegreen_root, 'live')
    run('mkdir -p %(bluegreen_root)s %(blue_path)s %(green_path)s '
        '%(blue_path)s/etc %(green_path)s/etc' % env)
    if not exists(env.live_path_abs):
        run('ln -s %(blue_path)s %(live_path_abs)s' % env)
    if not exists(env.next_path_abs):
        run('ln -s %(green_path)s %(next_path_abs)s' % env)
    env.next_path = run('readlink -f %(next_path_abs)s' % env)
    env.live_path = run('readlink -f %(live_path_abs)s' % env)
    env.virtualenv_path = posixpath.join(env.next_path, 'env')
    env.pidfile = posixpath.join(env.next_path, 'etc', 'app.pid')
    env.nginx_conf = posixpath.join(env.next_path, 'etc', 'nginx.conf')
    env.color = posixpath.basename(env.next_path)
    env.bluegreen_port = env.bluegreen_ports.get(env.color)


def swap_bluegreen():
    require('next_path', 'live_path', 'live_path_abs', 'next_path_abs')
    run('ln -nsf %(next_path)s %(live_path_abs)s' % env)
    run('ln -nsf %(live_path)s %(next_path_abs)s' % env)
