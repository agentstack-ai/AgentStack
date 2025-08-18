import os
import shutil
from pathlib import Path
import unittest
from parameterized import parameterized
from unittest.mock import patch, MagicMock
from agentstack import conf
from agentstack import repo
from agentstack.repo import TrackingDisabledError
from agentstack.exceptions import EnvironmentError
import git


BASE_PATH = Path(__file__).parent


class TestRepo(unittest.TestCase):
    def setUp(self):
        self.framework = os.getenv('TEST_FRAMEWORK')
        self.test_dir = BASE_PATH / 'tmp' / self.framework / 'test_repo'
        os.chdir(str(BASE_PATH))  # Change directory before cleanup to avoid Windows file locks
        os.makedirs(self.test_dir, exist_ok=True)
        os.chdir(self.test_dir)  # gitpython needs a cwd
        conf.set_path(self.test_dir)

    def tearDown(self):
        # Close any open git repo before cleanup
        try:
            git_repo = git.Repo(self.test_dir)
            git_repo.close()
        except (git.exc.InvalidGitRepositoryError, git.exc.NoSuchPathError):
            pass

        # Change directory out before removing
        os.chdir(str(BASE_PATH))

        # Remove the test directory
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_init(self):
        repo.init(force_creation=True)

        # Check if a git repository was created
        self.assertTrue((self.test_dir / '.git').is_dir())
        # Check if the repository has the correct initial branch
        git_repo = git.Repo(self.test_dir)
        self.assertEqual(git_repo.active_branch.name, repo.MAIN_BRANCH_NAME)
        # Check if an initial commit was made
        commits = list(git_repo.iter_commits())
        self.assertEqual(len(commits), 1)
        self.assertEqual(commits[0].message, f"{repo.INITIAL_COMMIT_MESSAGE}{repo.AUTOMATION_NOTE}")

    def test_init_parent_repo_exists(self):
        os.makedirs(self.test_dir.parent / '.git', exist_ok=True)
        repo.init(force_creation=False)
        self.assertFalse((self.test_dir / '.git').is_dir())

    def test_get_repo_nonexistent(self):
        with self.assertRaises(EnvironmentError):
            repo._get_repo()

    def test_get_repo_existent(self):
        repo.init(force_creation=True)

        result = repo._get_repo()
        self.assertIsInstance(result, git.Repo)
        self.assertEqual(result.working_tree_dir, str(self.test_dir))

    def test_get_uncommitted_files_new_file(self):
        repo.init(force_creation=True)

        new_file = self.test_dir / "new_file.txt"
        new_file.touch()

        # Check if the new file is in the list
        uncommitted = repo.get_uncommitted_files()
        self.assertIn("new_file.txt", uncommitted)

    def test_get_uncommitted_files_modified_file(self):
        repo.init(force_creation=True)

        # Create and commit an initial file
        initial_file = self.test_dir / "initial_file.txt"
        initial_file.write_text("Initial content")

        with repo.Transaction() as transaction:
            transaction.add_message("Add initial file")

        # Modify the file
        initial_file.write_text("Modified content")

        # Check if the modified file is in the list
        uncommitted = repo.get_uncommitted_files()
        self.assertIn("initial_file.txt", uncommitted)

    @patch('agentstack.repo.conf.ConfigFile')
    def test_should_track_changes_default(self, mock_config_file):
        mock_config = MagicMock()
        mock_config.use_git = True
        mock_config_file.return_value = mock_config

        self.assertTrue(repo.should_track_changes())

    @patch('agentstack.repo.conf.ConfigFile')
    def test_should_track_changes_disabled(self, mock_config_file):
        mock_config = MagicMock()
        mock_config.use_git = False
        mock_config_file.return_value = mock_config

        self.assertFalse(repo.should_track_changes())

    @patch('agentstack.repo.conf.ConfigFile')
    def test_should_track_changes_file_not_found(self, mock_config_file):
        mock_config_file.side_effect = FileNotFoundError

        self.assertTrue(repo.should_track_changes())

    def test_dont_track_changes(self):
        # Ensure tracking is enabled initially
        repo._USE_GIT = None
        self.assertTrue(repo.should_track_changes())

        # Disable tracking
        repo.dont_track_changes()
        self.assertFalse(repo.should_track_changes())

        # Reset _USE_GIT for other tests
        repo._USE_GIT = None

    @patch('agentstack.repo.should_track_changes', return_value=False)
    def test_require_git_when_disabled(self, mock_should_track):
        with self.assertRaises(TrackingDisabledError):
            repo._require_git()

    def test_require_git_when_disabled_manually(self):
        # Disable git tracking
        repo.dont_track_changes()

        with self.assertRaises(repo.TrackingDisabledError):
            repo._require_git()

        # Reset _USE_GIT for other tests
        repo._USE_GIT = None

    @parameterized.expand(
        [
            ("apt", "/usr/bin/apt", "Hint: run `sudo apt install git`"),
            ("brew", "/usr/local/bin/brew", "Hint: run `brew install git`"),
            ("port", "/opt/local/bin/port", "Hint: run `sudo port install git`"),
            ("none", None, ""),
        ]
    )
    @patch('agentstack.repo.should_track_changes', return_value=True)
    @patch('agentstack.repo.shutil.which')
    def test_require_git_not_installed(
        self, name, package_manager_path, expected_hint, mock_which, mock_should_track
    ):
        mock_which.side_effect = lambda x: None if x != name else package_manager_path

        with self.assertRaises(EnvironmentError) as context:
            repo._require_git()

        error_message = str(context.exception)
        self.assertIn("git is not installed.", error_message)

        if expected_hint:
            self.assertIn(expected_hint, error_message)

    @patch('agentstack.repo.should_track_changes', return_value=True)
    @patch('agentstack.repo.shutil.which', return_value='/usr/bin/git')
    def test_require_git_installed(self, mock_which, mock_should_track):
        # This should not raise an exception
        repo._require_git()

    def test_transaction_context_manager(self):
        repo.init(force_creation=True)
        mock_commit = MagicMock()

        with patch('agentstack.repo.commit', mock_commit):
            with repo.Transaction() as transaction:
                (self.test_dir / "test_file.txt").touch()
                transaction.add_message("Test message")

            mock_commit.assert_called_once_with("Test message", ["test_file.txt"], automated=True)

    def test_transaction_multiple_messages(self):
        repo.init(force_creation=True)
        mock_commit = MagicMock()

        with patch('agentstack.repo.commit', mock_commit):
            with repo.Transaction() as transaction:
                (self.test_dir / "test_file.txt").touch()
                transaction.add_message("First message")
                (self.test_dir / "test_file_2.txt").touch()
                transaction.add_message("Second message")

            mock_commit.assert_called_once_with(
                "First message, Second message", ["test_file.txt", "test_file_2.txt"], automated=True
            )

    def test_transaction_no_changes(self):
        repo.init(force_creation=True)
        mock_commit = MagicMock()

        with patch('agentstack.repo.commit', mock_commit):
            with repo.Transaction() as transaction:
                transaction.add_message("No changes")

                assert repo.get_uncommitted_files() == []

            mock_commit.assert_not_called()

    def test_transaction_with_exception(self):
        repo.init(force_creation=True)
        mock_commit = MagicMock()

        with patch('agentstack.repo.commit', mock_commit):
            try:
                with repo.Transaction() as transaction:
                    (self.test_dir / "test_file.txt").touch()
                    transaction.add_message("This message should not be committed")
                    raise ValueError("Test exception")
            except ValueError:
                pass

            mock_commit.assert_not_called()

        # Verify that the file was created but not committed
        self.assertTrue((self.test_dir / "test_file.txt").exists())
        self.assertIn("test_file.txt", repo.get_uncommitted_files())

    def test_init_when_git_disabled(self):
        repo.dont_track_changes()
        result = repo.init(force_creation=True)
        self.assertIsNone(result)
        repo._USE_GIT = None  # Reset for other tests

    def test_commit_when_git_disabled(self):
        repo.dont_track_changes()
        result = repo.commit("Test message", ["test_file.txt"])
        self.assertIsNone(result)
        repo._USE_GIT = None  # Reset for other tests

    def test_commit_all_changes_when_git_disabled(self):
        repo.dont_track_changes()
        result = repo.commit_all_changes("Test message")
        self.assertIsNone(result)
        repo._USE_GIT = None  # Reset for other tests

    def test_get_uncommitted_files_when_git_disabled(self):
        repo.dont_track_changes()
        result = repo.get_uncommitted_files()
        self.assertEqual(result, [])
        repo._USE_GIT = None  # Reset for other tests

    def test_commit_user_changes(self):
        repo.init(force_creation=True)

        # Create a new file
        test_file = self.test_dir / "user_file.txt"
        test_file.write_text("User content")

        # Commit user changes
        repo.commit_user_changes()

        # Check if the file was committed
        git_repo = git.Repo(self.test_dir)
        commits = list(git_repo.iter_commits())

        self.assertEqual(len(commits), 2)  # Initial commit + user changes commit
        self.assertEqual(commits[0].message, f"{repo.USER_CHANGES_COMMIT_MESSAGE}{repo.AUTOMATION_NOTE}")

        # Check if the file is no longer in uncommitted files
        self.assertNotIn("user_file.txt", repo.get_uncommitted_files())
