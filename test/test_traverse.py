from lss import Traverse
from pprint import pprint

def test_traverse():
    traverse = Traverse()
    pprint([item for item in traverse("../..")])

