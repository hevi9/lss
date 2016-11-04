#!/usr/bin/python3

"""
lss - LS Supplement
"""

# TODO: directory sizes along gnu fix
# TODO: permission colors
# TODO: access errors
# TODO: summary
# TODO: dirty git support

import argparse
import logging
import os
import stat
import sys
import time
from datetime import datetime
from fnmatch import fnmatch
from pprint import pprint
from subprocess import check_output
import math
import pwd
import grp

from humanize import naturalsize
from colorama import Fore, Style
from dateutil.relativedelta import relativedelta

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


# from http://git.savannah.gnu.org/cgit/coreutils.git/tree/src/ls.c

default_indicators = {
    "lc": ("\033[", "lc: Left of color sequence"),
    "rc": ("m", "rc: Right of color sequence"),
    "ec": ("0", "ec: End color (replaces lc+rs+rc)"),
    "rs": ("0", "rs: Reset to ordinary colors"),
    "no": ("0", "no: Normal"),
    "fi": ("0", "fi: File: default"),
    "di": ("01;34", "di: Directory: bright blue"),
    "ln": ("01;36", "ln: Symlink: bright cyan"),
    "pi": ("33", "pi: Pipe: yellow/brown"),
    "so": ("01;35", "so: Socket: bright magenta"),
    "bd": ("01;33", "bd: Block device: bright yellow"),
    "cd": ("01;33", "cd: Char device: bright yellow"),
    "mi": ("0", "mi: Missing file: undefined"),
    "or": ("0", "or: Orphaned symlink: undefined"),
    "ex": ("01;32", "ex: Executable: bright green"),
    "do": ("01;35", "do: Door: bright magenta"),
    "su": ("37;41", "su: setuid: white on red"),
    "sg": ("30;43", "sg: setgid: black on yellow"),
    "st": ("37;44", "st: sticky: black on blue"),
    "ow": ("34;42", "ow: other-writable: blue on green"),
    "tw": ("30;42", "tw: ow w/ sticky: black on green"),
    "ca": ("30;41", "ca: black on red"),
    "mh": ("0", "mh: disabled by default"),
    "cl": ("\033[K", "cl: clear to end of line")
}


def get_ls_colors_text():
    try:
        text = os.environ['LS_COLORS']
    except KeyError:
        text = check_output(['dircolors', '-b'])
        text = text.split()[0].decode()
        text = text[text.find("'") + 1:text.rfind("'")]
    return text


def init_indicators(ls_colors_text):
    data = {k: v for k, v in
            [i.split('=') for i in ls_colors_text.split(':') if i]}
    indicators = {k: data[k] if k in data else v[0] for k, v
                  in default_indicators.items()}
    for k in indicators:
        if k in data:
            del data[k]
    return indicators, data


indicator_ctl, indicator_glob = init_indicators(get_ls_colors_text())


def ls_color(key):
    try:
        return indicator_ctl["lc"] + indicator_ctl[key] + indicator_ctl["rc"]
    except KeyError:
        return indicator_ctl["lc"] + indicator_glob[key] + indicator_ctl["rc"]


filetypemap = (
    (stat.S_ISDIR, "di"),
    (stat.S_ISCHR, "cd"),
    (stat.S_ISBLK, "bd"),
    (stat.S_ISFIFO, "so"),
    (stat.S_ISLNK, "ln"),
    (stat.S_ISSOCK, "so"),
    (stat.S_ISREG, "fi")
)


# listing item file attributes format funtions
# fmt_attribute(item) -> formatted_str, color


def fmt_name(item):
    # 1. resolve fnmatch
    for glob in indicator_glob:
        if fnmatch(item.name, glob):
            return item.name, ls_color(glob)
    # 2. resolve fs type
    for pred, colorcode, in filetypemap:
        if pred(item.stat.st_mode):
            break
    return item.name, ls_color(colorcode)


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
    return naturalsize(item.size, gnu=True), colors[min(3, n)]


def fmt_complete(item):
    return "+" if not item.complete else "", Fore.MAGENTA


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


class Column:
    def __init__(self, func, *, align="R", fill=" ", prefix=None):
        self.func = func
        self.align = align
        self.fill = fill
        self.prefix = prefix
        self.maxwidth = 0


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
                value, color = column.func(item)
                if value is not None:
                    width = len(value)
                    row.append((value, color, width))
                    if width > column.maxwidth:
                        column.maxwidth = width
            rows.append(row)

        # write rows
        for row in rows:
            for i, field in enumerate(row):
                if columns[i].prefix:
                    w(columns[i].prefix)
                if columns[i].align == "R":  # align rigth
                    w(" " * (
                        columns[i].maxwidth - field[2]))  # maxwidth - width
                if self.hascolor:
                    w(field[1])  # color
                w(field[0])  # value
                if self.hascolor:
                    w(Style.RESET_ALL)
                if columns[i].align == "L":  # align left
                    w(" " * (
                        columns[i].maxwidth - field[2]))  # maxwidth - width
                w(columns[i].fill)  # fill to next
            w("\n")


class Item:
    """ Listing show item """

    COLUMNS = ("name", "size", "mtime") # ?

    complete = True
    count = 1

    def __init__(self, file):
        self.file = file

    def __repr__(self):
        return "%s(%r, complete=%s, size=%d)" % (
            self.__class__.__name__,
            self.path,
            self.complete,
            self.size
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
    def mode(self):
        return self.file.stat.st_mode

    def is_symlink(self):
        return False


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
    def __init__(self, *, filters=[filter_nodot], follow=False, maxdepth=1,
                 crossmount=False, timeout=0.5):
        self.filters = filters  # --all, --almost-all, --ignore-backups --hide
        self.follow = follow  # -L --dereference
        self.maxdepth = maxdepth
        self.crossmount = crossmount
        self.timeout = Timeout(timeout)

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

class TBD:

    def __getattr__(self, item):
        def stub(*args, **kwds):
            pass
        return stub

TBD = TBD()

ARGS = argparse.ArgumentParser(
    formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    allow_abbrev=True, # because enabling -atB style
    description="ls command suppliment.")

ARGS.add_argument("paths", metavar="path", nargs="*", default=["."],
                  help="paths to list, directories or files")

ARGS.add_argument("--debug", action="store_true",
                  help="set development and debug mode on")

# TODO --version  output version information and exit

GRP = ARGS.add_argument_group("Fields")
GRP.add_argument("--inode", "-i", action="store_true",
                 help="print the index number of each file")
# TODO -c                         with -lt: sort by, and show, ctime (time of last
#                               modification of file status information);
#                               with -l: show ctime and sort by name;
#                               otherwise: sort by ctime, newest first
# TODO -G, --no-group             in a long listing, don't print group names
# TODO -o                         like -l, but do not list group information
# -u                         with -lt: sort by, and show, access time;
#                               with -l: show access time and sort by name;
#                               otherwise: sort by access time, newest first

GRP = ARGS.add_argument_group("Filters")
GRP.add_argument("--all", "-a", action="store_true",
                 help="do not ignore entries starting with '.'")
TBD.add_argument("-A","--almost-all", action="store_true",
                 help="do not list implied . and ..")
# TODO -A
GRP.add_argument("-B", "--ignore-backups", action="store_true",
                 help="do not list implied entries ending with '~'")
# TODO --hide=PATTERN         do not list implied entries matching shell PATTERN
# (overridden by -a or -A)
# TODO -I, --ignore=PATTERN       do not list implied entries matching shell PATTERN



GRP = ARGS.add_argument_group("Listing")
GRP.add_argument("--group-directories-first", "-g", action="store_true",
                 help="group directories before files TBD")
GRP.add_argument("--dereference", "-L", action="store_true",
                 help="""when showing file information for a symbolic
      link, show information for the file the link
      references rather than for the link itself TBD""")
# TODO: -L symlink dereference
GRP.add_argument("--directory", "-d", action="store_true",
                 help="list directories themselves, not their contents TBD")
# TODO: -d flag
GRP.add_argument("--reverse", "-r", action="store_true",
                 help="reverse order while sorting")
GRP.add_argument("-t", "--sort-time", action="store_true",
                 help="sort by modification time, newest first")
GRP.add_argument("-S", "--sort-size", action="store_true",
                 help="sort by file size, largest first")
TBD.add_argument("-X", "--sort-ext", action="store_true",
                 help="TBD sort alphabetically by entry extension")
# TODO: sort alphabetically by entry extension
# TODO: -n, --numeric-uid-gid      like -l, but list numeric user and group IDs
# TODO -Q, --quote-name           enclose entry names in double quotes
# TODO --quoting-style=WORD   use quoting style WORD for entry names:
#                               literal, locale, shell, shell-always,
#                               shell-escape, shell-escape-always, c, escape
# TODO -s, --size                 print the allocated size of each file, in blocks
# TODO --sort=WORD            sort by WORD instead of name: none (-U), size (-S),
#                               time (-t), version (-v), extension (-X)
# TODO --time=WORD            with -l, show time as WORD instead of default
#                               modification time: atime or access or use (-u);
#                               ctime or status (-c); also use specified time
#                               as sort key if --sort=time (newest first)
# TODO -U                         do not sort; list entries in directory order

GRP = ARGS.add_argument_group("Traverse")
GRP.add_argument("--timeout", "-T", default=0.5, metavar="SECS", type=float,
                 help="""timeout to stop traversing on large trees.
                 To scan all files give a 'big' timeout eg. -T 99""")
GRP.add_argument("--dereference-command-line", "-H", action="store_true",
                 help="follow symbolic links listed on the command line TBD")
# TODO: -H dereference command line
GRP.add_argument("--cross-mount", action="store_true",
                 help="cross filesystem mount points")

# Ignored ls options:
# -D, --dired generate output designed for Emacs' dired mode
# --author               with -l, print the author of each file
# -b, --escape               print C-style escapes for nongraphic characters
# --block-size=SIZE      scale sizes by SIZE before printing them; e.g.,
#                               '--block-size=M' prints sizes in units of
#                               1,048,576 bytes; see SIZE format below
# -C                         list entries by columns
# --color[=WHEN]         colorize the output; WHEN can be 'always' (default
#                               if omitted), 'auto', or 'never'; more info below
# -f                         do not sort, enable -aU, disable -ls --color
# -F, --classify             append indicator (one of */=>@|) to entries
# --file-type            likewise, except do not append '*'
# --format=WORD          across -x, commas -m, horizontal -x, long -l,
#                               single-column -1, verbose -l, vertical -C
# --full-time            like -l --time-style=full-iso
# -g                         like -l, but do not list owner
# --group-directories-first
#                             group directories before files;
#                               can be augmented with a --sort option, but any
#                               use of --sort=none (-U) disables grouping
# -h, --human-readable       with -l and/or -s, print human readable sizes
#                               (e.g., 1K 234M 2G)
#  --si                   likewise, but use powers of 1000 not 1024
# --dereference-command-line-symlink-to-dir
#                             follow each command line symbolic link
# --indicator-style=WORD  append indicator with style WORD to entry names:
#                               none (default), slash (-p),
#                               file-type (--file-type), classify (-F)
# -k, --kibibytes            default to 1024-byte blocks for disk usage
# -l                         use a long listing format
# -m                         fill width with a comma separated list of entries
# -N, --literal              print raw entry names (don't treat e.g. control
#                               characters specially)
# -p, --indicator-style=slash
#                             append / indicator to directories
# -q, --hide-control-chars   print ? instead of nongraphic characters
#      --show-control-chars   show nongraphic characters as-is (the default,
#                               unless program is 'ls' and output is a terminal)
# -R, --recursive            list subdirectories recursively
# --time-style=STYLE     with -l, show times using style STYLE:
#                                full-iso, long-iso, iso, locale, or +FORMAT;
#                                FORMAT is interpreted like in 'date'; if FORMAT
#                                is FORMAT1<newline>FORMAT2, then FORMAT1 applies
#                                to non-recent files and FORMAT2 to recent files;
#                                if STYLE is prefixed with 'posix-', STYLE
#                                takes effect only outside the POSIX locale
# -T, --tabsize=COLS         assume tab stops at each COLS instead of 8
# -v                         natural sort of (version) numbers within text
# -w, --width=COLS           set output width to COLS.  0 means no limit
# -x                         list entries by lines instead of by columns
# -Z, --context              print any security context of each file
# -1                         list one file per line.  Avoid '\n' with -q or -b


def main(args=sys.argv[1:]):
    args = ARGS.parse_args(args)
    D("args=%r", args)

    if args.debug:
        logging.basicConfig(level=logging.DEBUG)

    filters = [filter_nodot]
    if args.all:
        filters = [filter_all]
    if args.ignore_backups:
        filters.append(filter_nobak)
    sort_key = "name"
    if args.sort_time:
        sort_key = "mtime"
    if args.sort_size:
        sort_key = "size"

    listing = Listing(show_inode=args.inode,
                      reverse=args.reverse,
                      sort_key=sort_key)
    traverse = Traverse(filters=filters,
                        timeout=args.timeout,
                        crossmount=args.cross_mount)

    for path in args.paths:
        for item in traverse(path):
            listing.add(item)

    listing.list()

# TODO Exit status:
#  0  if OK,
#  1  if minor problems (e.g., cannot access subdirectory),
#  2  if serious trouble (e.g., cannot access command-line argument).

EXIT_OK = 0
EXIT_MINOR = 1
EXIT_MAJOR = 2

# Using color to distinguish file types is disabled both by default and
# with --color=never.  With --color=auto, ls emits color codes only when
# standard output is connected to a terminal.  The LS_COLORS environment
# variable can change the settings.  Use the dircolors command to set it.

if __name__ == "__main__":
    main()


def test_traverse():
    traverse = Traverse()
    for item in [item for item in traverse(".")]:
        D(item)
        pass


def test_timeout():
    timeout = Timeout(0.1)
    while not timeout:
        D(timeout)
        time.sleep(0.01)


def test_ls_colors():
    logging.basicConfig(level=logging.DEBUG)
    lsc = LsColors(get_ls_colors_text())
    pprint(lsc.data)
