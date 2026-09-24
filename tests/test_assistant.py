"""
Unit and regression test suite for MyAssistant.
Tests safety boundaries, action validation, path traversal prevention,
app/folder allow-lists, and multi-action processing.
"""

import os
import sys
import unittest
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import main


class TestActionValidation(unittest.TestCase):
    """Test validation layer in main.py."""

    def test_allowed_actions(self):
        valid_actions = [
            {"action": "open_app", "target": "notepad"},
            {"action": "close_app", "target": "calculator"},
            {"action": "move_mouse", "target": "100,100"},
            {"action": "open_folder", "target": "downloads"},
            {"action": "list_files", "target": "documents"},
            {"action": "count_files", "target": "desktop"},
            {"action": "list_running_apps", "target": ""},
            {"action": "create_folder", "target": "MyTestProject"},
            {"action": "time", "target": ""},
            {"action": "help", "target": ""},
            {"action": "remember", "target": "user_name", "value": "Alice"},
            {"action": "recall", "target": "user_name"},
            {"action": "chat", "target": "", "response": "Hello"},
        ]
        for act in valid_actions:
            with self.subTest(action=act["action"]):
                self.assertTrue(main.validate_action(act))

    def test_rejected_unknown_actions(self):
        invalid_actions = [
            {"action": "delete_file", "target": "test.txt"},
            {"action": "execute_shell", "target": "dir"},
            {"action": "format_disk", "target": "C:"},
            {"action": "install_program", "target": "malware.exe"},
            {"action": "download_file", "target": "http://evil.com"},
        ]
        for act in invalid_actions:
            with self.subTest(action=act["action"]):
                self.assertFalse(main.validate_action(act))

    def test_allowed_application_targets(self):
        for app in ["chrome", "notepad", "calculator", "calculator app", "explorer", "file explorer"]:
            self.assertTrue(main.validate_action({"action": "open_app", "target": app}))
            self.assertTrue(main.validate_action({"action": "close_app", "target": app}))

    def test_rejected_application_targets(self):
        dangerous_apps = ["cmd", "cmd.exe", "powershell", "regedit", "format", "curl", "python"]
        for app in dangerous_apps:
            self.assertFalse(main.validate_action({"action": "open_app", "target": app}))
            self.assertFalse(main.validate_action({"action": "close_app", "target": app}))

    def test_allowed_folder_targets(self):
        for folder in ["downloads", "documents", "desktop", "pictures", "videos", "music"]:
            self.assertTrue(main.validate_action({"action": "open_folder", "target": folder}))
            self.assertTrue(main.validate_action({"action": "list_files", "target": folder}))
            self.assertTrue(main.validate_action({"action": "count_files", "target": folder}))

    def test_rejected_folder_targets(self):
        unapproved = ["c:\\windows", "system32", "program files", "appdata", ".."]
        for folder in unapproved:
            self.assertFalse(main.validate_action({"action": "open_folder", "target": folder}))
            self.assertFalse(main.validate_action({"action": "list_files", "target": folder}))
            self.assertFalse(main.validate_action({"action": "count_files", "target": folder}))

    def test_multi_action_validation(self):
        valid_multi = {
            "actions": [
                {"action": "open_app", "target": "notepad"},
                {"action": "open_folder", "target": "downloads"},
                {"action": "time", "target": ""}
            ]
        }
        self.assertTrue(main.validate_action(valid_multi))

        invalid_multi = {
            "actions": [
                {"action": "open_app", "target": "notepad"},
                {"action": "execute_shell", "target": "whoami"}
            ]
        }
        self.assertFalse(main.validate_action(invalid_multi))

    def test_malformed_actions(self):
        self.assertFalse(main.validate_action("not a dict"))
        self.assertFalse(main.validate_action([]))
        self.assertFalse(main.validate_action({"actions": []}))
        self.assertFalse(main.validate_action({"actions": "not a list"}))


class TestSecurityHardening(unittest.TestCase):
    """Test safety barriers added in Phase 1."""

    def test_explorer_kill_protection(self):
        # explorer shell termination must be explicitly guarded
        import io
        from contextlib import redirect_stdout

        f = io.StringIO()
        with redirect_stdout(f):
            main.close_application("explorer")
        output = f.getvalue()
        self.assertIn("restricted for system safety", output)

        f = io.StringIO()
        with redirect_stdout(f):
            main.close_application("file explorer")
        output = f.getvalue()
        self.assertIn("restricted for system safety", output)

    def test_create_folder_path_traversal_prevention(self):
        import io
        from contextlib import redirect_stdout

        # Test traversal via ..
        f = io.StringIO()
        with redirect_stdout(f):
            main.create_folder("../../Desktop/UnsafeHackedFolder")
        output = f.getvalue()
        self.assertTrue(
            "Blocked folder creation outside your Documents folder" in output
            or "invalid characters" in output
        )

        # Test traversal via invalid characters
        f = io.StringIO()
        with redirect_stdout(f):
            main.create_folder("folder:with*stars")
        output = f.getvalue()
        self.assertIn("invalid characters", output)

        # Test empty folder name
        f = io.StringIO()
        with redirect_stdout(f):
            main.create_folder("   ")
        output = f.getvalue()
        self.assertIn("Please provide a folder name", output)


class TestMouseControls(unittest.TestCase):
    """Test mouse coordinate handling."""

    def test_out_of_bounds_mouse(self):
        # Moving to negative or astronomical coordinates should fail safely
        self.assertFalse(main.move_mouse(-100, 500))
        self.assertFalse(main.move_mouse(500, -100))
        self.assertFalse(main.move_mouse(999999, 999999))


class TestPersonalMemory(unittest.TestCase):
    """Test memory get and save operations."""

    def test_memory_roundtrip(self):
        test_key = "test_framework_key"
        test_val = "PyTestUnit"
        main.save_personal_memory(test_key, test_val)
        self.assertEqual(main.get_personal_memory(test_key), test_val)
        # Clean up
        if test_key in main.personal_memory:
            del main.personal_memory[test_key]
            with open(main.PERSONAL_MEMORY_FILE, "w", encoding="utf-8") as file:
                main.json.dump(main.personal_memory, file, indent=2)


class TestPhase2Optimizations(unittest.TestCase):
    """Test Phase 2 optimizations: sub-millisecond process listing and multi-action results."""

    def test_list_running_applications(self):
        apps = main.list_running_applications()
        self.assertIsInstance(apps, list)

    def test_count_files(self):
        # Documents should exist and count should be >= 0
        count = main.count_files("documents")
        self.assertIsInstance(count, int)
        self.assertGreaterEqual(count, 0)

    def test_multi_action_result_aggregation(self):
        res = main.execute_action({
            "actions": [
                {"action": "time", "target": ""},
                {"action": "help", "target": ""}
            ]
        })
        self.assertIsInstance(res, list)
        self.assertEqual(len(res), 2)
        self.assertTrue(any("time" in r.lower() for r in res))
        self.assertIn("Displayed help", res)

    def test_web_search(self):
        results = main.web_search("Python programming", num_results=2)
        self.assertIsInstance(results, list)
        self.assertGreater(len(results), 0)
        self.assertIn("title", results[0])
        self.assertIn("url", results[0])
        self.assertIn("snippet", results[0])
        
if __name__ == "__main__":
    unittest.main()
