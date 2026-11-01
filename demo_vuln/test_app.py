import os
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from app import app


class TestVulnerableDemo(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.previous_dir = os.getcwd()
        os.chdir(self.temp_dir.name)

        connection = sqlite3.connect("app.db")
        connection.execute(
            "CREATE TABLE items (id INTEGER PRIMARY KEY, name TEXT)"
        )
        connection.execute(
            "INSERT INTO items (name) VALUES (?)",
            ("alice",),
        )
        connection.commit()
        connection.close()

        app.config["TESTING"] = True
        self.client = app.test_client()

    def tearDown(self):
        os.chdir(self.previous_dir)
        self.temp_dir.cleanup()

    def test_health_returns_ok(self):
        response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_data(as_text=True), "ok")

    def test_search_returns_matching_item(self):
        response = self.client.get("/search?q=alice")

        self.assertEqual(response.status_code, 200)
        self.assertIn("alice", response.get_data(as_text=True))


    @patch("app.os.system")
    def test_ping_calls_system_command(self, mock_system):
        from flask import Flask

        test_app = Flask("ping_test")
        test_app.add_url_rule(
            "/ping",
            view_func=app.view_functions["ping"],
            methods=["POST"],
        )

        with test_app.test_client() as client:
            response = client.post(
                "/ping",
                data={"host": "127.0.0.1"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_data(as_text=True), "ok")
        mock_system.assert_called_once_with("ping -c 1 127.0.0.1")


if __name__ == "__main__":
    unittest.main()
