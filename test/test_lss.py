from lss import D, Traverse, Timeout, init_indicators, get_ls_colors_text
import logging
import time
from pprint import pprint


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
    lsc, _ = init_indicators(get_ls_colors_text())
    pprint(lsc)
