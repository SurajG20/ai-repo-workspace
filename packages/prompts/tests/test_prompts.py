from __future__ import annotations

from prompts.render import (
    build_architecture_prompt,
    build_dead_code_prompt,
    build_onboarding_prompt,
    build_pr_analysis_prompt,
    build_qa_messages,
    format_context_blocks,
)


def test_format_context_blocks():
    hits = [
        {
            "kind": "function",
            "name": "login",
            "file_path": "auth.py",
            "start_line": 10,
            "signature": "def login(): pass",
            "parent_name": None,
        },
        {
            "kind": "class",
            "name": "AuthService",
            "file_path": "service.py",
            "start_line": 20,
            "signature": "class AuthService",
            "parent_name": None,
        },
    ]
    formatted = format_context_blocks(hits)
    assert "[1] function login — auth.py:10" in formatted
    assert "def login(): pass" in formatted
    assert "[2] class AuthService — service.py:20" in formatted


def test_build_qa_messages():
    hits = [
        {
            "kind": "function",
            "name": "create_user",
            "file_path": "users.py",
            "start_line": 5,
            "signature": "def create_user(): pass",
        }
    ]
    messages = build_qa_messages("How does user creation work?", hits, "my-org/my-repo")
    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert "create_user" in messages[0]["content"]
    assert messages[1]["role"] == "user"
    assert "my-org/my-repo" in messages[1]["content"]
    assert "How does user creation work?" in messages[1]["content"]


def test_build_dead_code_prompt():
    candidates = [{"name": "unused_fn", "file_path": "old.py", "outbound_links": 0}]
    prompt = build_dead_code_prompt(candidates)
    assert "unused_fn" in prompt
    assert "old.py" in prompt


def test_build_pr_analysis_prompt():
    files = [{"path": "api/auth.py"}]
    affected = [{"name": "login_handler", "file_path": "api/auth.py"}]
    prompt = build_pr_analysis_prompt("Update Auth", "Improves login security", files, affected)
    assert "Update Auth" in prompt
    assert "api/auth.py" in prompt
    assert "login_handler" in prompt


def test_build_architecture_prompt():
    hits = [{"name": "AppEngine", "file_path": "main.py", "start_line": 1}]
    prompt = build_architecture_prompt("Authentication Architecture", hits)
    assert "Authentication Architecture" in prompt
    assert "AppEngine" in prompt


def test_build_onboarding_prompt():
    inventory = [{"file": "README.md", "type": "docs"}]
    prompt = build_onboarding_prompt(inventory)
    assert "README.md" in prompt
