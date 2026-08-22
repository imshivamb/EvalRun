"""Unit and integration tests for Python, HTTP, and CLI agent adapters."""

import json
import os
import shutil
import sys
import tempfile
import unittest
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

from cli.resolver import resolve_agent
from framework.core.adapters import PythonAgentAdapter, HttpAgentAdapter, CliAgentAdapter
from framework.llms.openai_compatible import OpenAICompatibleLLM
from framework.models import AgentOutput


class MockAgentHandler(BaseHTTPRequestHandler):
    """Mock HTTP server handler returning JSON agent output."""

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8")
        req_data = json.loads(body) if body else {}

        response_data = {
            "content": f"HTTP Agent Response to: {req_data.get('prompt', '')}",
            "metadata": {"status": "ok", "latency": 0.05},
        }

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(response_data).encode("utf-8"))

    def log_message(self, format, *args):
        pass


class TestAgentAdapters(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.server = HTTPServer(("localhost", 8989), MockAgentHandler)
        cls.server_thread = threading.Thread(target=cls.server.serve_forever)
        cls.server_thread.daemon = True
        cls.server_thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.llm = OpenAICompatibleLLM("mock-model", "http://localhost:8000/v1", "EMPTY")

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_python_agent_adapter(self):
        class DummyInnerAgent:
            def run(self, prompt):
                return AgentOutput(content=f"Python Echo: {prompt}", metadata={"source": "python"})

        adapter = PythonAgentAdapter(DummyInnerAgent())
        output = adapter.run("Hello World")
        self.assertEqual(output.content, "Python Echo: Hello World")
        self.assertEqual(output.metadata.get("source"), "python")

    def test_http_agent_adapter(self):
        adapter = HttpAgentAdapter("http://localhost:8989/predict")
        output = adapter.run("Test Prompt")
        self.assertIn("HTTP Agent Response to: Test Prompt", output.content)
        self.assertEqual(output.metadata.get("status"), "ok")

    def test_cli_agent_adapter(self):
        # Create temporary executable python script for CLI agent mock
        script_path = os.path.join(self.temp_dir, "cli_agent_mock.py")
        with open(script_path, "w", encoding="utf-8") as f:
            f.write("import sys, json\n")
            f.write("prompt = sys.stdin.read().strip()\n")
            f.write("res = {'content': f'CLI Agent Output for: {prompt}', 'metadata': {'cli': True}}\n")
            f.write("print(json.dumps(res))\n")

        cli_cmd = f"{sys.executable} {script_path}"
        adapter = CliAgentAdapter(command=cli_cmd)
        output = adapter.run("CLI Test Input")

        self.assertIn("CLI Agent Output for: CLI Test Input", output.content)
        self.assertTrue(output.metadata.get("cli"))

    def test_resolver_http_specifier(self):
        resolved = resolve_agent("http://localhost:8989/predict", self.llm)
        self.assertIsInstance(resolved, HttpAgentAdapter)
        output = resolved.run("Resolver HTTP Test")
        self.assertIn("HTTP Agent Response to: Resolver HTTP Test", output.content)

    def test_resolver_cli_specifier(self):
        script_path = os.path.join(self.temp_dir, "cli_agent_mock.py")
        with open(script_path, "w", encoding="utf-8") as f:
            f.write("import sys, json\n")
            f.write("prompt = sys.stdin.read().strip()\n")
            f.write("res = {'content': f'CLI Resolver Output for: {prompt}', 'metadata': {'resolver': True}}\n")
            f.write("print(json.dumps(res))\n")

        cli_spec = f"cli:{sys.executable} {script_path}"
        resolved = resolve_agent(cli_spec, self.llm)
        self.assertIsInstance(resolved, CliAgentAdapter)

        output = resolved.run("Resolver CLI Test")
        self.assertIn("CLI Resolver Output for: Resolver CLI Test", output.content)


if __name__ == "__main__":
    unittest.main()
