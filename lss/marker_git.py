import os
from git import Repo
from colorama import Fore

from .marker import marker, MARK_OK, MARK_MINOR, MARK_MAJOR

@marker
def git(file):
    if file.name == ".git":
        repo = Repo(file.path)
        if repo.untracked_files:
            return "G", MARK_MINOR
        elif repo.is_dirty():
            return "G", MARK_MAJOR
        else:
            return "G", MARK_OK
    else:
        return None, None
