from __future__ import with_statement
from fabric.state import env
from fabric.api import local, run, abort, task
from fabric.context_managers import settings


@task
def allow_dirty():
    '''allow pushing even when the working copy is dirty'''
    env.gitric_allow_dirty = True


@task
def force_push():
    '''allow pushing even when history will be lost'''
    env.gitric_force_push = True


def git_seed(repo_path, commit=None):
    '''seed a remote git repository'''
    commit = _get_commit(commit)
    force = ('gitric_force_push' in env) and '-f' or ''
    dirty_working_copy = local('git status --porcelain', capture=True)
    if dirty_working_copy and 'gitric_allow_dirty' not in env:
        abort(
            'Working copy is dirty. This check can be overridden by\n'
            'importing gitric.api.allow_dirty and adding allow_dirty to your '
            'call.')
    # initialize the remote repository (idempotent)
    run('git init %s' % repo_path)
    # silence git complaints about pushes coming in on the current branch
    # the pushes only seed the immutable object store and do not modify the
    # working copy
    run('GIT_DIR=%s/.git git config receive.denyCurrentBranch ignore' %
        repo_path)
    # a target doesn't need to keep track of which branch it is on so we always
    # push to its "master"
    with settings(warn_only=True):
        push = local(
            'git push git+ssh://%s@%s:%s%s %s:refs/heads/master %s' % (
                env.user, env.host, env.port, repo_path, commit, force))
    if push.failed:
        abort(
            '%s is a non-fast-forward\n'
            'push. The seed will abort so you don\'t lose information. '
            'If you are doing this\nintentionally import '
            'gitric.api.force_push and add it to your call.' % commit)


def git_reset(repo_path, commit=None):
    '''checkout a sha1 on a remote git repo'''
    commit = _get_commit(commit)
    run('cd %s && git reset --hard %s' % (repo_path, commit))


def _get_commit(commit):
    if commit is None:
        # if no commit is specified we will push HEAD
        commit = local('git rev-parse HEAD', capture=True)
    return commit
