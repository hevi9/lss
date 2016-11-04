from colorama import Fore

_markers = {}


def marker(func):
    _markers[func.__name__] = func


def get_markers():
    return _markers.values()

MARK_ERROR = 100
MARK_MAJOR = 20
MARK_MINOR = 10
MARK_OK = 0

_markcolormap = {
    MARK_ERROR: Fore.RED,
    MARK_MAJOR: Fore.MAGENTA,
    MARK_MINOR: Fore.YELLOW,
    MARK_OK: Fore.GREEN
}

def get_color(mark):
    return _markcolormap[mark]
