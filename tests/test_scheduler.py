import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scheduler import compare_algorithms, parse_task_csv, topological_order


SAMPLE = """id,duration,cpu,memory,deadline,dependencies
T1,18,2,2,45,
T2,22,4,4,70,T1
T3,14,2,3,65,T1
T4,26,4,6,105,T2;T3
"""


class SchedulerTests(unittest.TestCase):
    def setUp(self):
        self.tasks = parse_task_csv(SAMPLE)
        self.resources = [
            {"id": 1, "name": "S", "cpu": 2, "ram": 4, "mips": 1200, "cost": .18, "energy": .7},
            {"id": 2, "name": "M", "cpu": 4, "ram": 8, "mips": 2500, "cost": .34, "energy": 1.05},
            {"id": 3, "name": "Eco", "cpu": 4, "ram": 12, "mips": 2100, "cost": .28, "energy": .58},
        ]

    def test_csv_parser_and_dag(self):
        self.assertEqual(len(self.tasks), 4)
        order, _, _ = topological_order(self.tasks)
        self.assertLess(order.index("T1"), order.index("T4"))

    def test_cycle_is_rejected(self):
        invalid = "id,duration,cpu,memory,deadline,dependencies\nT1,1,1,1,5,T2\nT2,1,1,1,5,T1"
        with self.assertRaisesRegex(ValueError, "cycle"):
            parse_task_csv(invalid)

    def test_all_algorithms_return_metrics(self):
        result = compare_algorithms(self.tasks, self.resources, {"time": .3, "cost": .25, "energy": .2, "balance": .25})
        self.assertEqual(set(result["algorithms"]), {"fcfs", "min_min", "heft", "proposed"})
        self.assertEqual(len(result["algorithms"]["proposed"]["schedule"]), 4)
        self.assertGreater(result["algorithms"]["proposed"]["metrics"]["makespan"], 0)


if __name__ == "__main__":
    unittest.main()

