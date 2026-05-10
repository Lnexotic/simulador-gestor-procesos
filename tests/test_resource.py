import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.resource import ResourcePool

class TestResourcePool(unittest.TestCase):
    def setUp(self):
        self.pool = ResourcePool(cpu_cores=2, ram_mb=2048)

    def test_initial_resources(self):
        self.assertEqual(self.pool.available_cpu, 2)
        self.assertEqual(self.pool.available_ram, 2048)

if __name__ == '__main__':
    unittest.main()
