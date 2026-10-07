import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import create_app, db


class AppTests(unittest.TestCase):
    def setUp(self):
        handle, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(handle)
        self.app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///" + self.db_path, "WTF_CSRF_ENABLED": False})
        self.client = self.app.test_client()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def login(self, email, password):
        return self.client.post("/login", data={"email": email, "password": password}, follow_redirects=True)

    def test_public_pages_and_admin_login(self):
        self.assertEqual(self.client.get("/").status_code, 200)
        response = self.login("admin@cloudflow.local", "admin123")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Cloud intelligence at a glance", response.data)

    def test_user_creates_and_schedules_workflow(self):
        self.login("user@cloudflow.local", "user123")
        csv_data = "id,duration,cpu,memory,deadline,dependencies\nT1,10,2,2,30,\nT2,12,2,2,60,T1"
        response = self.client.post("/workflow/new", data={"name": "Test DAG", "deadline": "100", "budget": "50", "objective": "balanced", "tasks_csv": csv_data}, follow_redirects=True)
        self.assertIn(b"Test DAG", response.data)
        response = self.client.post("/workflow/1/schedule", follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"SCHEDULING COMPLETE", response.data)


if __name__ == "__main__":
    unittest.main()

