# gitric #

Very simple git-based deployment for fabric.

Git pulling from a remote repository requires that you open your repository to the world and it means your deployment process relies on one more moving piece. Since git is distributed you can push from your local repository and rely on one fewer external resource and limit access to your private repositories to your internal network but still get lightning fast git deployments.

## Installation ##

    pip install gitric

## Features ##

* Uses git push instead of git pull.
    * Pre-seeds your target's immutable git object store so you can stop and restart your server before and after the working copy is modified instead of waiting for network IO and the working copy to update.
* Won't let you deploy from a dirty working copy (can be overridden for testing).
* Won't let you lose history (can be overridden for rollbacks).

<pre>
cd example
virtualenv .env --no-site-packages
source .env/bin/activate
pip install -r requirements.txt
fab -l
Available commands:
    
    allow_dirty  allow pushing even when the working copy is dirty
    deploy       an example deploy action
    force_push   allow pushing even when history will be lost
    prod         an example production deployment
</pre>

After creating a test-deploy user on my server:

    fab prod deploy
    ...
    [yourserverhere] out: HEAD is now at b2db04e Initial commit

    
    Done.
    Disconnecting from yourserverhere... done.

You can't deploy when your working copy is dirty:

    touch dirty_working_copy
    fab prod deploy
    ...
    Fatal error: Working copy is dirty. This check can be overridden by
    importing gitric.api.allow_dirty and adding allow_dirty to your call.
    
    Aborting.

And it (well git) won't let you deploy when you would lose history unless overridden with a force_push:

    # simulate a divergent history
    echo "#hello" >> requirements.txt
    git add requirements.txt
    git commit --amend
    fab prod deploy
    ....
    Fatal error: 11485c970d21ea2003c0be3be820905220d34631 is a non-fast-forward
    push. The seed will abort so you don't lose information. If you are doing this
    intentionally import gitric.api.force_push and add it to your call.
