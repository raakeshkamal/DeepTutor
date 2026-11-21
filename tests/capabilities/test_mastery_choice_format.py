"""Models own code layout; unreadable choices never become durable quiz cards."""

from unittest.mock import Mock

import pytest
import yaml

from deeptutor.capabilities.mastery import tools
from deeptutor.capabilities.mastery.choice_format import validate_choice_format

pytest_plugins = ["tests.capabilities.test_mastery_question_groups"]

# Regression from session message 190: fencing the stem did not format its options.
FLAT_PROGRAM = (
    "struct User { name: String, age: u8 } fn main() { "
    'let u1 = User { name: String::from("Ana"), age: 30 }; '
    'let u2 = User { age: 31, ..u1 }; println!("{} {}", u2.name, u2.age); }'
)
FORMATTED_PROGRAM = """```rust
struct User {
    name: String,
    age: u8,
}
fn main() {
    let u1 = User { name: String::from("Ana"), age: 30 };
    let u2 = User { age: 31, ..u1 };
    println!("{} {}", u2.name, u2.age);
}
```"""


@pytest.mark.parametrize(
    "body",
    [
        FLAT_PROGRAM,
        f"`{FLAT_PROGRAM}`",
        f"```rust\n{FLAT_PROGRAM}\n```",
        "```rust\nfn main() {}\n```",
        '```rust\nfn main() {\nprintln!("hi");\n}\n```',
        "```rust\nlet n = 1;",
        "```\nlet n = 1;\n```",
        "```rust\n```",
        r"```rust\nlet n = 1;\n```",
        "    let n = 1;",
        "let u2 = User { age: 31, ..u1 };",
        "def pair(): return (5, 8)",
        "function pair() { return [5, 8]; }",
        "```text\n" + "x" * 121 + "\n```",
    ],
)
def test_unreadable_code_is_rejected_with_actionable_retry(body):
    with pytest.raises(ValueError) as exc:
        validate_choice_format([{"label": "C", "body": body}])
    assert "options[C].body" in str(exc.value)
    assert "Retry mastery_quiz" in str(exc.value)
    assert "Do not change code tokens" in str(exc.value)
    assert body not in str(exc.value)


@pytest.mark.parametrize(
    "body",
    [
        "It fails to compile because the function returns the wrong type.",
        "Struct update syntax fills the remaining fields.",
        "Use `..u1` to fill the remaining fields.",
        "Use function split() to return the values.",
        "A call to fn pair() returns a tuple.",
        "Z-9",
        "9-Z",
        "$x^2 + y^2$",
        "`&city`",
        "```rust\nlet u2 = User { age: 31, ..u1 };\n```",
        FORMATTED_PROGRAM,
        FORMATTED_PROGRAM.replace("..u1", "u1"),  # Intentionally invalid distractor.
        FORMATTED_PROGRAM.replace("..u1", "..u1.name"),
        FORMATTED_PROGRAM.replace("```", "~~~"),
        "```python\ndef pair():\n    return (5, 8)\n```",
        "```javascript\nfunction pair() {\n    return [5, 8];\n}\n```",
    ],
)
def test_formatted_code_invalid_distractors_prose_and_math_are_unchanged(body):
    options = [{"label": "A", "body": body}]
    validate_choice_format(options)
    assert options == [{"label": "A", "body": body}]


def test_single_and_group_schemas_advertise_the_enforced_format():
    definition = tools.MasteryQuizTool().get_definition()
    schema = definition.to_openai_schema()["function"]["parameters"]["properties"]
    for properties in [schema, schema["questions"]["items"]["properties"]]:
        options = properties["options"]
        assert "120" in options["description"]
        description = options["items"]["properties"]["body"]["description"]
        assert "```rust\nfn main() {\n" in description
        assert "incorrect syntax" in description
    assert "rejected" in definition.description


@pytest.mark.parametrize("language", ["en", "zh"])
def test_tutor_prompt_includes_an_actual_multiline_option_example(language):
    from pathlib import Path

    root = Path(tools.__file__).parent
    pack = yaml.safe_load((root / "prompts" / language / "mastery_loop.yaml").read_text())
    assert "mastery_quiz.options[].body" in pack["playbook"]
    assert '```rust\nfn main() {\n    println!("hi");\n}\n```' in pack["playbook"]
    assert "120" in pack["playbook"]


def _question(body):
    return {
        "knowledge_point_id": "kp1",
        "question": "Which program uses struct update syntax?",
        "code_task": "select_program",
        "expected_answer": body,
        "options": [
            {"label": "A", "body": body},
            {"label": "B", "body": "Neither program"},
        ],
    }


@pytest.mark.asyncio
@pytest.mark.parametrize("grouped", [False, True])
async def test_failed_format_publishes_nothing_then_model_retry_posts_one_card(
    service, monkeypatch, grouped
):
    monkeypatch.setattr(tools, "_new_service", lambda: service)
    end_turn = Mock()
    call = {"_mastery_path_id": "p", "_end_turn_on_card": end_turn}
    if grouped:
        valid_leaf = {
            "knowledge_point_id": "kp2",
            "question": "Name a value.",
            "expected_answer": "beta",
        }
        malformed = {**call, "questions": [valid_leaf, _question(FLAT_PROGRAM)]}
        corrected = {**call, "questions": [valid_leaf, _question(FORMATTED_PROGRAM)]}
    else:
        malformed = {**call, **_question(FLAT_PROGRAM)}
        corrected = {**call, **_question(FORMATTED_PROGRAM)}

    before = service.store.load("p").model_dump()
    failed = await tools.MasteryQuizTool().execute(**malformed)
    assert not failed.success
    assert "Retry mastery_quiz" in failed.content
    assert "mastery_question" not in failed.metadata
    assert service.store.get_active_interaction("p") is None
    assert service.store.load("p").model_dump() == before
    end_turn.assert_not_called()

    succeeded = await tools.MasteryQuizTool().execute(**corrected)
    assert succeeded.success, succeeded.content
    card = succeeded.metadata["mastery_question"]
    pending = service.store.load("p").pending_question
    if grouped:
        card = card["questions"][1]
        pending = pending.questions[1]
    assert pending.choice_map[pending.expected_answer] == FORMATTED_PROGRAM
    assert {option["label"]: option["body"] for option in card["options"]} == pending.choice_map
    end_turn.assert_called_once()
