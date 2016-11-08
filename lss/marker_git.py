import os
from git import Repo

from .marker import marker, MARK_OK, MARK_MINOR, MARK_MAJOR

@marker
def git(file):
    ret = None, None

    if file.name == ".git":
        # git status fix: on git statu, git updates (and locks) index file,
        # therefore updating directory modification time
        keep_atime = file.atime
        keep_mtime = file.mtime

        repo = Repo(file.path)
        if repo.untracked_files:
            ret = "G", MARK_MINOR
        elif repo.is_dirty():
            ret = "G", MARK_MAJOR
        else:
            ret = "G", MARK_OK

        os.utime(file.path, (keep_atime, keep_mtime))

    return ret
