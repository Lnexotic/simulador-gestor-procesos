import unittest
import sys
import os

# Ajustar ruta para importar src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.scheduler import Scheduler, SchedulingAlgorithm
from src.core.resource import ResourcePool

class TestScheduler(unittest.TestCase):
    def setUp(self):
        self.resources = ResourcePool(cpu_cores=1, ram_mb=1024)
        self.scheduler = Scheduler(self.resources, None, SchedulingAlgorithm.FCFS)

    def test_initialization(self):
        self.assertEqual(self.scheduler.clock, 0)
        self.assertEqual(len(self.scheduler.ready_queue), 0)

if __name__ == '__main__':
    unittest.main()
