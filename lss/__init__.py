#!/usr/bin/python3

"""
lss - LS Supplement
"""

# TODO: directory sizes along gnu fix
# TODO: permission colors
# TODO: access errors
# TODO: summary

import logging
import os
import stat
import sys
import time
from datetime import datetime
from fnmatch import fnmatch
import math
import pwd
import grp
import pprint
import pkg_resources

from humanize import naturalsize
from colorama import Fore, Style
from dateutil.relativedelta import relativedelta

from .lscolor import indicator_glob, ls_color, filetypemap
from .marker import get_markers, get_color
from .util import is_iterable

from . import marker_git

NAME = "lss"

try:
    __version__ = pkg_resources.get_distribution(NAME).version
except pkg_resources.DistributionNotFound:
    __version__ = "0.0.0"


log = logging.getLogger(__name__)
D = log.debug




class Timeout:
    def __init__(self, delay):
        self.delay = delay
        self.start_time = time.monotonic()

    def __bool__(self):
        return time.monotonic() >= self.start_time + self.delay

    def __str__(self):
        return "Timeout(%f/%f)" % (
            time.monotonic() - self.start_time, self.delay)


def is_tty(stream):
    """ Is stream TTY ? """
    isatty = getattr(stream, 'isatty', None)
    return isatty and isatty()


# listing item file attributes format funtions
# fmt_attribute(item) -> iterable of (formatted_str, color)


def fmt_name(item):
    # 1. resolve fnmatch
    for glob in indicator_glob:
        if fnmatch(item.name, glob):
            return item.name, ls_color(glob)
    # 2. resolve fs type
    for pred, colorcode, in filetypemap:
        if pred(item.stat.st_mode):
            break
    return [item.name, ls_color(colorcode)]

# TODO ? new colorscale: seconds, minutes, hours, days, weeks, months, years
# TODO % time alternative iso-datetime

def fmt_time(item):
    """ Represent timestamp oldness in max 6 characters. """
    delta = relativedelta(datetime.now(),
                          datetime.fromtimestamp(item.mtime))
    if delta.years:
        return "%dY%dM" % (delta.years, delta.months), Fore.BLUE
    if delta.months:
        return "%dM%dd" % (delta.months, delta.days), Fore.CYAN
    if delta.days:
        return "%dd%dh" % (delta.days, delta.hours), Fore.GREEN
    if delta.hours:
        return "%dh%dm" % (delta.hours, delta.minutes), Fore.YELLOW
    if delta.minutes:
        return "%dm%ds" % (delta.minutes, delta.seconds), Fore.RED
    return "%5.2fs" % (
        (delta.seconds if delta.seconds else 0) + (
            delta.microseconds / 1000000)), Fore.MAGENTA


def fmt_count(item):
    return "%d" % item.count, Style.NORMAL


def fmt_size(item):
    n = math.floor(math.log(item.size, 2) / 10) if item.size else 0
    colors = (
        Style.NORMAL,
        Fore.BLUE,
        Fore.YELLOW,
        Fore.RED
    )
    return [naturalsize(item.size, gnu=True), colors[min(3, n)]]


def fmt_complete(item):
    return ["+" if not item.complete else "", Fore.MAGENTA]


def fmt_perm(item):
    return stat.filemode(item.mode), Fore.WHITE


def fmt_user(item):
    uid = item.file.stat.st_uid
    if uid == 0:
        color = Fore.RED
    elif 0 < uid < 1000:
        color = Fore.BLUE
    elif uid == 65534:
        color = Fore.MAGENTA
    else:
        color = Fore.WHITE
    return pwd.getpwuid(uid).pw_name, color


def fmt_group(item):
    gid = item.file.stat.st_gid
    if gid == 0:
        color = Fore.RED
    elif 0 < gid < 1000:
        color = Fore.BLUE
    elif gid == 65534:
        color = Fore.MAGENTA
    else:
        color = Fore.WHITE
    return grp.getgrgid(gid).gr_name, color


def fmt_inode(item):
    return str(item.file.stat.st_ino), Style.NORMAL


def fmt_symlink(item):
    if item.is_symlink():
        try:
            return item.linked_path(), fmt_name(item.linked_file())[1]
        except FileNotFoundError:
            return item.linked_path(), ls_color("or")
    else:
        return None, None


def fmt_markers(item):
    return tuple(
        (k, get_color(item.markers[k])) for k in sorted(item.markers.keys()))


class Column:
    def __init__(self, func, *, align="R", fill=" ", prefix=None):
        self.func = func
        self.align = align
        self.fill = fill
        self.prefix = prefix
        self.maxwidth = 0


class View:
    def __init__(self):
        self.width = 0  # sum of len(value)
        self.viewseq = []  # value, color

    def __repr__(self):
        return "".join(i[0] for i in self.viewseq)

    def append(self, value, color):
        if value is not None:
            self.width += len(value)
            self.viewseq.append((value, color))


class Listing:
    def __init__(self, *, show_inode=False, reverse=False, sort_key="name"):
        self.hascolor = is_tty(sys.stdout)
        self.items = set()
        self.reverse = reverse
        self.sort_func = lambda item: getattr(item, sort_key)

        self.columns = [
            Column(fmt_perm, align="L"),
            Column(fmt_user),
            Column(fmt_group),
            Column(fmt_count),
            Column(fmt_size, fill=""),
            Column(fmt_complete),
            Column(fmt_time),
            Column(fmt_markers),
            Column(fmt_name, align="", fill=""),
            Column(fmt_symlink, align="", fill="", prefix=" -> ")
        ]
        if show_inode:
            self.columns.insert(0, Column(fmt_inode))

    def add(self, item):
        self.items.add(item)

    def list(self):
        w = sys.stdout.write

        columns = self.columns
        rows = []  # row

        # sort items
        items = sorted(self.items, key=self.sort_func)
        if self.reverse:
            items.reverse()

        # format values and colors and find column maxwidth
        for item in items:
            row = []  # (value, color, width)
            for column in self.columns:
                specs = column.func(item) # call format function
                if specs and not is_iterable(specs[0]):
                    specs = [specs]
                view = View()
                for spec in specs:
                    view.append(*spec)
                row.append(view)
                if view.width > column.maxwidth:
                    column.maxwidth = view.width
            rows.append(row)

        # write rows
        for row in rows:
            last_fill = ""
            for i, view in enumerate(row):
                if view.width and columns[i].prefix:
                    w(columns[i].prefix)
                if columns[i].align == "R":  # align rigth
                    w(" " * (columns[i].maxwidth - view.width))
                for field in view.viewseq:
                    if self.hascolor:
                        w(field[1])  # color
                        D("value=%r color=%r", field[0], field[1])
                    w(field[0])  # value
                    if self.hascolor:
                        w(Style.RESET_ALL)
                if columns[i].align == "L":  # align left
                    w(" " * (columns[i].maxwidth - view.width))

                if columns[i].maxwidth or not last_fill:
                    w(columns[i].fill)  # fill to next
                    last_fill = columns[i].fill
            w("\n")


class Item:
    """ Listing show item """

    complete = True
    count = 1

    def __init__(self, file):
        self.file = file
        self.markers = {}

    def __repr__(self):
        return "%s(%r, complete=%s, size=%d, mtime=%r)" % (
            self.__class__.__name__,
            self.path,
            self.complete,
            self.size,
            self.mtime
        )

    @property
    def name(self):
        return self.file.name

    @property
    def path(self):
        return self.file.path

    @property
    def stat(self):
        return self.file.stat

    @property
    def size(self):
        return self.file.stat.st_size

    @property
    def mtime(self):
        return self.file.stat.st_mtime

    @property
    def atime(self):
        return self.file.stat.st_atime

    @property
    def ctime(self):
        return self.file.stat.st_ctime


    @property
    def mode(self):
        return self.file.stat.st_mode

    def is_symlink(self):
        return False

    def set_mark(self, mark, level):
        if not mark:
            return
        D("set_mark %r %r", mark, level)
        level_cur = self.markers.setdefault(mark, level)
        if level > level_cur:
            self.markers[mark] = level


class Regular(Item):
    """ Regular file """

    def __init__(self, file):
        super().__init__(file)


class Dir(Item):
    """ Directory """

    _size = 0
    count = 0
    complete = False
    _mtime = 0

    def __init__(self, file):
        super().__init__(file)
        self._mtime = file.mtime

    @property
    def size(self):
        return self._size

    @property
    def mtime(self):
        return self._mtime

    def contribute(self, file):
        self._size += file.stat.st_size
        self.count += 1
        if file.mtime > self._mtime:
            self._mtime = file.mtime


class Link(Item):
    """ Symlink or door to somewhere """

    def __init__(self, file):
        super().__init__(file)
        self._linked_path = None
        self._linked_file = None

    def is_symlink(self):
        return True

    def linked_path(self):
        if not self._linked_path:
            self._linked_path = os.readlink(self.file.path)
        return self._linked_path

    def linked_file(self):
        if not self._linked_file:
            path = self.linked_path()
            if not os.path.isabs(path):
                path = os.path.join(os.path.dirname(self.path), path)
            self._linked_file = File(path)
        return self._linked_file


class File:
    is_mount = False

    def __init__(self, path, *, stat=None):
        self.path = path
        self.stat = stat if stat else os.lstat(path)

    def __repr__(self):
        return "File(%r)" % self.path

    @property
    def name(self):
        return os.path.basename(self.path)

    @property
    def dev(self):
        return self.stat.st_dev

    @property
    def mtime(self):
        return self.stat.st_mtime

    @property
    def atime(self):
        return self.stat.st_atime

    @property
    def ctime(self):
        return self.stat.st_ctime


    def is_dir(self):
        return stat.S_ISDIR(self.stat.st_mode)

    def is_file(self):
        return stat.S_ISREG(self.stat.st_mode)

    def is_char_device(self):
        return stat.S_ISCHR(self.stat.st_mode)

    def is_block_device(self):
        return stat.S_ISBLK(self.stat.st_mode)

    def is_fifo(self):
        return stat.S_ISFIFO(self.stat.st_mode)

    def is_symlink(self):
        return stat.S_ISLNK(self.stat.st_mode)

    def is_socket(self):
        return stat.S_ISSOCK(self.stat.st_mode)


def filter_nodot(name):
    return name.startswith(".")


def filter_all(name):
    return False


def filter_nobak(name):
    return name.endswith("~")


class Traverse:
    def __init__(self, *, filters=(filter_nodot,), follow=False, maxdepth=1,
                 crossmount=False, timeout=0.5):
        self.filters = filters  # --all, --almost-all, --ignore-backups --hide
        self.follow = follow  # -L --dereference
        self.maxdepth = maxdepth
        self.crossmount = crossmount
        self.timeout = Timeout(timeout)
        self.markers = get_markers()

    def __call__(self, path):
        updir = File(path)
        try:
            for entry in os.scandir(path):
                if not self._ignore(entry.name):
                    yield from self._traverse(entry.path, depth=1, updir=updir)
        except PermissionError as ex:
            log.error("%s", str(ex))
        except NotADirectoryError as ex:
            yield from self._traverse(path)

    def _ignore(self, name):
        for filter in self.filters:
            if filter(name):
                return True
        return False

    def _traverse(self, path, *, stat=None, updir=None, depth=0, item=None):
        """ Traverse path and yield listing items. Note: yielded listing item
        is not complete until this call is fully done. """

        D("%d %s", depth, path)

        # reduce filters

        #
        file = File(path, stat=stat)

        # create listing item or contribute sub files to item
        if depth <= self.maxdepth:
            if file.is_dir():
                item = Dir(file)
            elif file.is_symlink():
                item = Link(file)
            else:
                item = Regular(file)
            item.depth = depth
            yield item  # yield item now and update it along traversing
        else:
            item and item.contribute(file)

        # don't cross fs mounts and mark is_mount for file
        if updir is not None and file.dev != updir.dev:
            file.is_mount = True
            if not self.crossmount:
                return

        # traverse recursively
        if file.is_dir():
            for marker in self.markers:
                item.set_mark(*marker(file))
            try:
                for entry in os.scandir(file.path):
                    # cancel traversing if timeout
                    if self.timeout:
                        D("%s depth=%d item=%r entry=%r", self.timeout, depth,
                          item, entry)
                        return
                    yield from self._traverse(
                        os.path.join(file.path, entry.name),
                        stat=entry.stat(follow_symlinks=False),
                        updir=file,
                        depth=depth + 1,
                        item=item)
                if item and depth == item.depth:
                    item.complete = True
            except NotADirectoryError as ex:
                log.error("%s", str(ex))
            except PermissionError as ex:
                log.error("%s", str(ex))
