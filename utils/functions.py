import itertools
import gzip
import shutil
from typing import Iterable, Generator, List, Callable, TypeVar, Optional


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


def dict_get_or_default(d: dict, index, default, convert=None):
    if index in d:
        value = d[index]
        return convert(value) if convert is not None else value
    else:
        return default


def list_get_or_default(collection: List, index: int, default, convert=None):
    if len(collection) > index:
        value = collection[index]
        return convert(value) if convert is not None else value
    else:
        return default


def list_get_or_throw(collection: List, index: int, message: str):
    if len(collection) > index:
        return collection[index]
    else:
        raise IndexError(message)


T = TypeVar('T')


def first(predicate: Callable[[T], bool], iterable: Iterable[T]) -> T:
    return next(filter(predicate, iterable))


def find(predicate: Callable[[T], bool], iterable: Iterable) -> Optional[T]:
    return next(filter(predicate, iterable), None)

