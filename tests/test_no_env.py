import importlib
import io
import json
import os
import sys
import tempfile
import types
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock


def import_without_dotenv(module_name):
    sentinel = object()
    original_dotenv = sys.modules.get("dotenv", sentinel)
    sys.modules.pop(module_name, None)
    if module_name.startswith("Bing."):
        sys.modules.pop("Bing.call_gemini", None)

    sys.modules["dotenv"] = types.SimpleNamespace(load_dotenv=mock.Mock(return_value=False))
    try:
        return importlib.import_module(module_name)
    finally:
        if original_dotenv is sentinel:
            sys.modules.pop("dotenv", None)
        else:
            sys.modules["dotenv"] = original_dotenv


def quiet_call(func, *args, **kwargs):
    with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
        return func(*args, **kwargs)


class NoEnvLogicTest(unittest.TestCase):
    def test_main_import_does_not_start_bot_without_env(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            module = quiet_call(import_without_dotenv, "main")

        self.assertTrue(hasattr(module, "main"))
        self.assertIsNone(module.DISCORD_TOKEN)

    def test_missing_google_credentials_do_not_write_file(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            module = quiet_call(import_without_dotenv, "main")

        with tempfile.TemporaryDirectory() as tmpdir:
            with mock.patch.dict(os.environ, {}, clear=True):
                old_cwd = os.getcwd()
                try:
                    os.chdir(tmpdir)
                    written = quiet_call(module.write_credentials_json)
                finally:
                    os.chdir(old_cwd)

            self.assertFalse(written)
            self.assertFalse(Path(tmpdir, "credentials.json").exists())

    def test_google_credentials_are_rendered_when_env_is_complete(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            module = quiet_call(import_without_dotenv, "main")
        env = {
            "project_id": "project",
            "private_key_id": "key-id",
            "private_key": "line1\\nline2",
            "client_email": "bot@example.com",
            "client_id": "client-id",
        }

        with mock.patch.dict(os.environ, env, clear=True):
            credentials, missing = module.build_credentials_dict()

        self.assertEqual(missing, [])
        self.assertEqual(credentials["private_key"], "line1\nline2")
        self.assertEqual(credentials["client_email"], "bot@example.com")
        self.assertIn("bot@example.com", credentials["client_x509_cert_url"])

    def test_channel_id_parser_rejects_missing_or_invalid_values(self):
        announcements = quiet_call(import_without_dotenv, "cogs.announcements")
        parse_channel_id = announcements.parse_channel_id

        self.assertEqual(parse_channel_id("1234567890"), 1234567890)
        self.assertIsNone(parse_channel_id(""))
        self.assertIsNone(parse_channel_id(None))
        self.assertIsNone(parse_channel_id("abc"))

    def test_pollinations_helpers_encode_prompt_and_skip_missing_key(self):
        image = quiet_call(import_without_dotenv, "Bing.image")
        video = quiet_call(import_without_dotenv, "Bing.video")
        build_pollinations_headers = image.build_pollinations_headers
        build_pollinations_image_url = image.build_pollinations_image_url
        build_video_headers = video.build_pollinations_headers
        build_pollinations_video_url = video.build_pollinations_video_url

        prompt = "貓 / dog? a=b"

        self.assertEqual(
            build_pollinations_image_url(prompt),
            "https://gen.pollinations.ai/image/%E8%B2%93%20%2F%20dog%3F%20a%3Db",
        )
        self.assertEqual(
            build_pollinations_video_url(prompt),
            "https://gen.pollinations.ai/image/%E8%B2%93%20%2F%20dog%3F%20a%3Db",
        )
        self.assertEqual(build_pollinations_headers(None), {})
        self.assertEqual(build_pollinations_headers("secret"), {"Authorization": "Bearer secret"})
        self.assertEqual(build_video_headers(None), {"Accept": "*/*"})
        self.assertEqual(
            build_video_headers("secret"),
            {"Accept": "*/*", "Authorization": "Bearer secret"},
        )

    def test_resolve_chrome_driver_path_prefers_env_then_system_path(self):
        text = quiet_call(import_without_dotenv, "text")

        with mock.patch.dict(os.environ, {"CHROMEDRIVER_PATH": "/custom/chromedriver"}, clear=True):
            self.assertEqual(text.resolve_chrome_driver_path(), "/custom/chromedriver")

        with mock.patch.dict(os.environ, {}, clear=True):
            with mock.patch.object(text.shutil, "which", return_value="/usr/bin/chromedriver"):
                self.assertEqual(text.resolve_chrome_driver_path(), "/usr/bin/chromedriver")

        with mock.patch.dict(os.environ, {}, clear=True):
            with mock.patch.object(text.shutil, "which", return_value=None):
                self.assertIsNone(text.resolve_chrome_driver_path())

    @unittest.skipUnless(
        os.getenv("RUN_LIVE_CRAWLER_TEST") == "1",
        "設定 RUN_LIVE_CRAWLER_TEST=1 才執行真實網站爬蟲測試",
    )
    def test_live_crawler_fetches_school_announcements(self):
        text = quiet_call(import_without_dotenv, "text")

        with tempfile.TemporaryDirectory() as tmpdir:
            old_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                result = quiet_call(text.fetch_announcement)
            finally:
                os.chdir(old_cwd)

        self.assertIsInstance(result, str)
        self.assertTrue(result.strip())
        self.assertIn("公告內容", result)

    def test_gemini_memory_save_is_capped_without_api_key(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            Bing1 = quiet_call(import_without_dotenv, "Bing.Bing1")

        with tempfile.TemporaryDirectory() as tmpdir:
            memory_file = Path(tmpdir, "memory.json")
            prompt_file = Path(tmpdir, "prompt.txt")
            history_file = Path(tmpdir, "history.json")
            prompt_file.write_text("test prompt", encoding="utf-8")

            with mock.patch.object(Bing1, "MEMORY_FILE", str(memory_file)):
                with mock.patch.object(Bing1, "PROMPT_FILE", str(prompt_file)):
                    with mock.patch.object(Bing1, "HISTORY_FILE", str(history_file)):
                        with mock.patch.dict(os.environ, {}, clear=True):
                            cog = quiet_call(Bing1.GeminiChat, bot=None)
                        memory = [
                            {"role": "user", "parts": [str(index)]}
                            for index in range(cog.max_memory_entries + 5)
                        ]
                        cog.save_memory(memory)

            saved = json.loads(memory_file.read_text(encoding="utf-8"))
            self.assertEqual(len(saved), cog.max_memory_entries)
            self.assertEqual(saved[0]["parts"], ["5"])


if __name__ == "__main__":
    unittest.main()
