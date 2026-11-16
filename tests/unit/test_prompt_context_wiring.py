"""
Unit tests for the context that analysis steps receive from previous steps.

Issue #29: analysis steps make up details when they do not get the results
of earlier steps. A step declares "context" in prompts.json, but the
analyzer puts that context into the prompt only where the prompt file has a
{previous_context} placeholder. These tests make sure that the declared
context reaches the model.
"""

import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from investigator.core.claude_analyzer import ClaudeAnalyzer, ensure_context_placeholder


PROMPTS_DIR = Path(__file__).parent.parent.parent / "prompts"

# These steps had no context before issue #29. The high-level overview
# tells them the technology stack, so that they do not guess it.
STEPS_THAT_NEED_OVERVIEW = [
    "core_entities",
    "DBs",
    "APIs",
    "events",
    "authentication",
    "authorization",
    "data_mapping",
    "security_check",
    "monitoring",
]


def _load_steps():
    """Return (step, prompt_path) for each step of each prompt type."""
    steps = []
    for type_config in sorted(PROMPTS_DIR.glob("*/prompts.json")):
        type_dir = type_config.parent
        config = json.loads(type_config.read_text())
        step_list = []
        if "extends" in config:
            base = json.loads((type_dir / config["extends"]).read_text())
            step_list.extend(base.get("processing_order", []))
        step_list.extend(config.get("processing_order", []))
        step_list.extend(config.get("additional_prompts", []))
        for step in step_list:
            steps.append((type_dir.name, step, (type_dir / step["file"]).resolve()))
    return steps


class TestDeclaredContextReachesPrompt(unittest.TestCase):
    """Each step that declares context must have a place for it in its prompt."""

    def test_every_step_with_context_has_placeholder(self):
        missing = []
        for type_name, step, prompt_path in _load_steps():
            if not step.get("context"):
                continue
            if "{previous_context}" not in prompt_path.read_text():
                missing.append(f"{type_name}/{step['name']}")
        self.assertEqual(
            missing, [],
            "These steps declare context, but their prompt has no {previous_context} placeholder"
        )

    def test_isolated_steps_get_overview_context(self):
        base = json.loads((PROMPTS_DIR / "base_prompts.json").read_text())
        steps = {step["name"]: step for step in base["processing_order"]}
        for name in STEPS_THAT_NEED_OVERVIEW:
            with self.subTest(step=name):
                context = steps[name].get("context", [])
                self.assertIn({"type": "step", "val": "hl_overview"}, context)

    def test_context_steps_run_before_the_step(self):
        base = json.loads((PROMPTS_DIR / "base_prompts.json").read_text())
        order = [step["name"] for step in base["processing_order"]]
        for step in base["processing_order"]:
            for ctx in step.get("context", []):
                with self.subTest(step=step["name"], context=ctx["val"]):
                    self.assertLess(order.index(ctx["val"]), order.index(step["name"]))


class TestEnsureContextPlaceholder(unittest.TestCase):
    """The analyzer must not drop context when the placeholder is missing."""

    TEMPLATE = (
        "Analyze the databases.\n"
        "\n"
        "---\n"
        "\n"
        "## Repository Structure and Files\n"
        "\n"
        "{repo_structure}\n"
    )

    def test_no_change_without_context(self):
        self.assertEqual(ensure_context_placeholder(self.TEMPLATE, None), self.TEMPLATE)
        self.assertEqual(ensure_context_placeholder(self.TEMPLATE, ""), self.TEMPLATE)

    def test_no_change_when_placeholder_exists(self):
        template = "Intro\n\n{previous_context}\n\n{repo_structure}"
        self.assertEqual(ensure_context_placeholder(template, "ctx"), template)

    def test_placeholder_goes_before_repository_structure(self):
        result = ensure_context_placeholder(self.TEMPLATE, "ctx")
        self.assertIn("{previous_context}", result)
        self.assertLess(
            result.index("{previous_context}"),
            result.index("## Repository Structure and Files"),
        )
        self.assertLess(result.index("Analyze the databases."), result.index("{previous_context}"))

    def test_placeholder_goes_at_end_without_structure_section(self):
        result = ensure_context_placeholder("Only instructions.", "ctx")
        self.assertTrue(result.rstrip().endswith("{previous_context}"))

    def test_warning_is_logged(self):
        logger = Mock()
        ensure_context_placeholder(self.TEMPLATE, "ctx", logger)
        logger.warning.assert_called_once()


class TestAnalyzerSendsContext(unittest.TestCase):
    """analyze_with_context must send the context to the model."""

    def setUp(self):
        self.analyzer = ClaudeAnalyzer("test-api-key", Mock())
        response = Mock()
        response.content = [Mock(text="result")]
        self.analyzer.client = Mock()
        self.analyzer.client.messages.create.return_value = response

    def _sent_prompt(self):
        kwargs = self.analyzer.client.messages.create.call_args.kwargs
        return kwargs["messages"][0]["content"]

    def test_context_is_sent_for_prompt_without_placeholder(self):
        db_prompt = (PROMPTS_DIR / "shared" / "db.md").read_text()
        db_prompt = db_prompt.replace("{previous_context}", "")
        self.analyzer.analyze_with_context(db_prompt, "src/app.py", "Stack: PostgreSQL")
        prompt = self._sent_prompt()
        self.assertIn("## Previous Analysis Context", prompt)
        self.assertIn("Stack: PostgreSQL", prompt)
        self.assertLess(prompt.index("Stack: PostgreSQL"), prompt.index("src/app.py"))

    def test_no_context_section_without_context(self):
        db_prompt = (PROMPTS_DIR / "shared" / "db.md").read_text()
        self.analyzer.analyze_with_context(db_prompt, "src/app.py", None)
        prompt = self._sent_prompt()
        self.assertNotIn("{previous_context}", prompt)
        self.assertNotIn("## Previous Analysis Context", prompt)


if __name__ == "__main__":
    unittest.main()
