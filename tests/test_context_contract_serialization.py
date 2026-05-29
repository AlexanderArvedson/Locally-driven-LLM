import json
import os
import tempfile
import unittest

from src.retrieval.contracts.context_contract import (
    build_repository_context_payload,
    format_repository_context_for_prompt,
    validate_repository_context_payload,
)
from src.retrieval.contracts.types import ContextPackage, DependencyEdge


class TestContextContractSerialization(unittest.TestCase):
    def test_payload_json_roundtrip_with_repo_relative_paths(self):
        with tempfile.TemporaryDirectory() as repo:
            a_path = os.path.join(repo, "a.py")
            b_path = os.path.join(repo, "b.py")

            pkg = ContextPackage(
                primary_file=a_path,
                related_files=[b_path, a_path],
                related_symbols={
                    b_path: ["helper"],
                    a_path: ["x"],
                },
                dependency_summary=[
                    DependencyEdge(from_path=a_path, to_path=b_path, import_text="import b"),
                ],
                total_symbols=2,
            )

            payload = build_repository_context_payload(
                pkg,
                selected_files=[b_path, a_path, b_path],
                repo_path=repo,
            )

            is_valid, reason = validate_repository_context_payload(payload)
            self.assertTrue(is_valid, msg=reason)

            # Target-first + repo-relative normalization should be preserved.
            self.assertEqual(payload["primary_file"], "a.py")
            self.assertEqual(payload["selected_files"], ["a.py", "b.py"])

            encoded = json.dumps(payload, sort_keys=True)
            decoded = json.loads(encoded)
            self.assertEqual(decoded, payload)

            is_valid_after, reason_after = validate_repository_context_payload(decoded)
            self.assertTrue(is_valid_after, msg=reason_after)

            prompt_block = format_repository_context_for_prompt(decoded)
            self.assertIn("[REPOSITORY CONTEXT]", prompt_block)
            self.assertIn("- selected_files:", prompt_block)

    def test_payload_json_roundtrip_handles_nullable_import_text(self):
        pkg = ContextPackage(
            primary_file="a.py",
            related_files=["a.py", "b.py"],
            related_symbols={"a.py": ["x"], "b.py": ["helper"]},
            dependency_summary=[
                DependencyEdge(from_path="a.py", to_path="b.py", import_text=None),
            ],
            total_symbols=2,
        )

        payload = build_repository_context_payload(pkg, selected_files=["a.py", "b.py"])
        encoded = json.dumps(payload)
        decoded = json.loads(encoded)

        self.assertIsNone(decoded["dependency_summary"][0]["import_text"])
        is_valid, reason = validate_repository_context_payload(decoded)
        self.assertTrue(is_valid, msg=reason)


if __name__ == "__main__":
    unittest.main()
