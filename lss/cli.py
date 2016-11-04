import argparse
import sys
import logging

from . import filter_all, filter_nobak, filter_nodot, Traverse, Listing

log = logging.getLogger(__name__)
D = log.debug


class TBD:
    def __getattr__(self, item):
        def stub(*args, **kwds):
            pass

        return stub


TBD = TBD()

ARGS = argparse.ArgumentParser(
    formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    allow_abbrev=True,  # because enabling -atB style
    description="ls command suppliment.")

ARGS.add_argument("paths", metavar="path", nargs="*", default=["."],
                  help="paths to list, directories or files")

ARGS.add_argument("--debug", action="store_true",
                  help="set development and debug mode on")

# TODO --version  output version information and exit

GRP = ARGS.add_argument_group("Fields")
GRP.add_argument("--inode", "-i", action="store_true",
                 help="print the index number of each file")
# TODO -c                         with -lt: sort by, and show, ctime (time of
# last
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
TBD.add_argument("-A", "--almost-all", action="store_true",
                 help="do not list implied . and ..")
# TODO -A
GRP.add_argument("-B", "--ignore-backups", action="store_true",
                 help="do not list implied entries ending with '~'")
# TODO --hide=PATTERN         do not list implied entries matching shell
# PATTERN
# (overridden by -a or -A)
# TODO -I, --ignore=PATTERN       do not list implied entries matching shell
# PATTERN


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
# TODO -s, --size              print the allocated size of each file, in blocks
# TODO --sort=WORD          sort by WORD instead of name: none (-U), size (-S),
#                               time (-t), version (-v), extension (-X)
# TODO --time=WORD            with -l, show time as WORD instead of default
#                             modification time: atime or access or use (-u);
#                               ctime or status (-c); also use specified time
#                               as sort key if --sort=time (newest first)
# TODO -U                       do not sort; list entries in directory order

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
#                             if omitted), 'auto', or 'never'; more info below
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
#                           unless program is 'ls' and output is a terminal)
# -R, --recursive            list subdirectories recursively
# --time-style=STYLE     with -l, show times using style STYLE:
#                                full-iso, long-iso, iso, locale, or +FORMAT;
#                              FORMAT is interpreted like in 'date'; if FORMAT
#                              is FORMAT1<newline>FORMAT2, then FORMAT1 applies
#                              to non-recent files and FORMAT2 to recent files;
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
