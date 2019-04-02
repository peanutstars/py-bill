
import time
import unittest

from core.cache import FileCache
from pysp.sbasic import SSingleton


class TestCache(unittest.TestCase):

    def test_file_cache(self):
        # Create
        cache = FileCache()
        cache.set_cache('1', 'first', duration=6)
        cache.set_cache('2', 'second', duration=6)
        del SSingleton._instances[FileCache]
        del cache
        # Load from file
        cache = FileCache()
        self.assertTrue('first' == cache.get_cache('1'))
        cache.set_cache('3', 'three', duration=2)
        del SSingleton._instances[FileCache]
        del cache
        # Expired
        time.sleep(2.1)
        cache = FileCache()
        self.assertIsNone(cache.get_cache('3'))
        self.assertTrue('first' == cache.get_cache('1'))
        self.assertTrue('second' == cache.get_cache('2'))
        del SSingleton._instances[FileCache]
        del cache
        # Clean up
        time.sleep(5)
        FileCache().cleanup()
        del SSingleton._instances[FileCache]