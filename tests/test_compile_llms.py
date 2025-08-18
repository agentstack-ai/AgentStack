import os
import shutil
import tempfile
import unittest
from pathlib import Path

import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from docs.compile_llms_txt import compile_llms_txt


class TestCompileLLMsTxt(unittest.TestCase):
    def setUp(self):
        self.original_cwd = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        # Create a temporary directory for test files
        self.test_dir = tempfile.mkdtemp()
        self.docs_dir = Path(self.test_dir)

        # Change to the temporary directory
        os.chdir(self.docs_dir)

    def tearDown(self):
        os.chdir(self.original_cwd)
        shutil.rmtree(self.test_dir)

    def create_test_mdx_file(self, path: str, content: str):
        """Helper to create test MDX files"""
        file_path = self.docs_dir / path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content)

    def test_basic_compilation(self):
        """Test basic MDX file compilation"""
        # Create test MDX files
        self.create_test_mdx_file("test1.mdx", "Test content 1")
        self.create_test_mdx_file("test2.mdx", "Test content 2")

        # Run compilation
        compile_llms_txt()

        # Check output file exists and contains expected content
        output_path = self.docs_dir / "llms.txt"
        self.assertTrue(output_path.exists())

        content = output_path.read_text()
        self.assertIn("## test1.mdx", content)
        self.assertIn("Test content 1", content)
        self.assertIn("## test2.mdx", content)
        self.assertIn("Test content 2", content)

    def test_excluded_directories(self):
        """Test that files in excluded directories are skipped"""
        # Create files in both regular and excluded directories
        self.create_test_mdx_file("regular/file.mdx", "Regular content")
        self.create_test_mdx_file("tool/file.mdx", "Tool content")

        compile_llms_txt()

        content = (self.docs_dir / "llms.txt").read_text()
        self.assertIn("Regular content", content)
        self.assertNotIn("Tool content", content)

    def test_excluded_files(self):
        """Test that excluded files are skipped"""
        self.create_test_mdx_file("regular.mdx", "Regular content")
        self.create_test_mdx_file("tool.mdx", "Tool content")

        compile_llms_txt()

        content = (self.docs_dir / "llms.txt").read_text()
        self.assertIn("Regular content", content)
        self.assertNotIn("Tool content", content)

    def test_nested_directories(self):
        """Test compilation from nested directory structure"""
        self.create_test_mdx_file("dir1/test1.mdx", "Content 1")
        self.create_test_mdx_file("dir1/dir2/test2.mdx", "Content 2")

        compile_llms_txt()

        content = (self.docs_dir / "llms.txt").read_text()
        self.assertIn(f"## dir1{os.path.sep}test1.mdx", content)
        self.assertIn(f"## dir1{os.path.sep}dir2{os.path.sep}test2.mdx", content)
        self.assertIn("Content 1", content)
        self.assertIn("Content 2", content)

    def test_empty_directory(self):
        """Test compilation with no MDX files"""
        compile_llms_txt()

        content = (self.docs_dir / "llms.txt").read_text()
        self.assertEqual(content, "")
