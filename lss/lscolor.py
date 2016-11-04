import os
import stat

from subprocess import check_output

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
