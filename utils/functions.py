import itertools
import gzip
import shutil
from typing import Iterable, Generator


def gzip_unpack(input_file: str, output_file: str):
    with gzip.open(input_file, "rb") as packed:
        with open(output_file, "wb") as unpacked:
            shutil.copyfileobj(packed, unpacked)


def groupby(collection, key):
    """
    :param list collection: collection to group
    :param function, lambda key: lambda describe how to group
    :rtype: dict
    """
    # groupby wants sorted collection
    sort = sorted(collection, key=key)
    groups = itertools.groupby(sort, key)
    return {key: list(value) for key, value in groups}


def split(collection, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(collection), n):
        yield collection[i:i + n]


def flatten(collection: Iterable[Iterable]) -> Generator:
    """Flatten list of lists in one plane list"""
    return (item for sublist in collection for item in sublist)
