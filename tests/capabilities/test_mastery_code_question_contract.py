"""Code purpose controls where programs belong; a rejected leak never posts a card."""

from unittest.mock import Mock

import pytest

from deeptutor.capabilities.mastery import tools
from deeptutor.capabilities.mastery.code_question import CODE_TASKS, validate_code_question
from deeptutor.learning.models import PendingQuestion

pytest_plugins = ["tests.capabilities.test_mastery_question_groups"]

# Same code as session message 190, with only layout changed between the copies.
STRUCT = """struct User { name: String, age: u8 }
fn main() {
    let u1 = User { name: String::from("Ana"), age: 30 };
    let u2 = User { age: 31, ..u1 };
    println!("{} {}", u2.name, u2.age);
}"""
STRUCT_LAYOUT = """struct User {
    name: String,
    age: u8
}
fn main() {
    let u1 = User { name: String::from("Ana"), age: 30 };
    let u2 = User { age: 31, ..u1 };
    println!("{} {}", u2.name, u2.age);
}"""
TUPLE = """fn get_pair() -> (i32, i32) { (5, 8) }
fn main() {
    let (first, second) = get_pair();
    println!("{first} {second}");
}"""


def fenced(code, language="rust"):
    return f"```{language}\n{code}\n```"


def options(code=STRUCT_LAYOUT, language="rust"):
    return [
        {"label": "A", "body": fenced(code, language)},
        {"label": "B", "body": "Neither program"},
    ]


@pytest.mark.parametrize("code", [STRUCT, TUPLE])
def test_actual_leaked_struct_and_tuple_programs_are_rejected(code):
    with pytest.raises(ValueError, match="repeats an entire candidate program"):
        validate_code_question(
            "Which program is correct?\n\n" + fenced(code), options(code), "select_program"
        )


@pytest.mark.parametrize("stem", [fenced(STRUCT), "`" + STRUCT.replace("\n", " ") + "`"])
def test_layout_differences_and_inline_code_do_not_hide_a_complete_copy(stem):
    with pytest.raises(ValueError, match=r"options\[A\].body"):
        validate_code_question("Choose a program.\n\n" + stem, options(), "select_program")


@pytest.mark.parametrize(
    ("candidate", "different"),
    [
        ('println!("a b");', 'println!("ab");'),
        ('println!(r#"a b"#);', 'println!(r#"a  b"#);'),
        ('println!(br###"a b"###);', 'println!(br###"ab"###);'),
        ("let c = 'a';", "let c = 'b';"),
        ("let n = 1.0;", "let n = 1 .0;"),
        ("let n = a && b;", "let n = a & & b;"),
        ("let n = a == b;", "let n = a != b;"),
        ("let city = 1;", "let cities = 1;"),
    ],
)
def test_strings_numbers_identifiers_and_operators_remain_distinct(candidate, different):
    original = "fn main() {\n    " + candidate + "\n}"
    supplied = "fn main() {\n    " + different + "\n}"
    validate_code_question(fenced(supplied), options(original), "select_program")


def test_language_aliases_do_not_hide_layout_only_copies():
    with pytest.raises(ValueError, match="repeats an entire candidate program"):
        validate_code_question(fenced(STRUCT, "rs"), options(), "select_program")


def test_rust_lifetimes_and_characters_preserve_meaning_while_layout_is_ignored():
    candidate = "fn choose<'a>(s: &'a str) -> &'a str {\n    s\n}"
    supplied = "fn choose < 'a > (s : & 'a str) -> & 'a str { s }"
    with pytest.raises(ValueError, match="repeats an entire candidate program"):
        validate_code_question(fenced(supplied), options(candidate), "select_program")


def test_python_indent_width_is_layout_but_block_structure_and_strings_are_not():
    code = 'def f():\n    if ready:\n        print("a b")\n    print("done")'
    restyled = 'def f():\n  if ready:\n    print("a b")\n  print("done")'
    with pytest.raises(ValueError, match="repeats an entire candidate program"):
        validate_code_question(
            fenced(restyled, "python"), options(code, "python"), "select_program"
        )
    validate_code_question(
        fenced(code.replace('"a b"', '"ab"'), "python"), options(code, "python"), "select_program"
    )
    changed_scope = 'def f():\n    if ready:\n        print("a b")\n        print("done")'
    validate_code_question(
        fenced(changed_scope, "python"), options(code, "python"), "select_program"
    )
    # A top-level indentation error must not be erased by stripping the block.
    validate_code_question(
        fenced("    " + code, "python"), options(code, "python"), "select_program"
    )


def test_unknown_languages_and_invalid_literals_use_conservative_exact_matching():
    code = "function main() {\n    return /a b/;\n}"
    with pytest.raises(ValueError, match="repeats an entire candidate program"):
        validate_code_question(
            fenced(code, "javascript"), options(code, "javascript"), "select_program"
        )
    validate_code_question(
        fenced(code.replace("a b", "a  b"), "javascript"),
        options(code, "javascript"),
        "select_program",
    )
    invalid = 'fn main() {\n    println!("unclosed);\n}'
    with pytest.raises(ValueError, match="repeats an entire candidate program"):
        validate_code_question(fenced(invalid), options(invalid), "select_program")


@pytest.mark.parametrize("purpose", ["predict_output", "debug_code"])
def test_input_programs_are_allowed_for_prediction_and_debugging(purpose):
    validate_code_question("Inspect this input.\n\n" + fenced(STRUCT), options(), purpose)


@pytest.mark.parametrize(
    "snippet",
    ["`User`", "`..u1`", fenced("let age = 31;"), fenced("struct User { name: String, age: u8 }")],
)
def test_shared_identifiers_and_partial_programs_are_not_answer_leaks(snippet):
    validate_code_question("Use this context.\n\n" + snippet, options(), "select_program")


@pytest.mark.parametrize("purpose", ["", "guess", 1, [], {}])
def test_an_invalid_purpose_is_an_actionable_error(purpose):
    with pytest.raises(ValueError, match="code_task must be"):
        validate_code_question("Choose.", options(), purpose)


def test_code_questions_require_a_purpose_but_prose_math_and_diagrams_do_not():
    with pytest.raises(ValueError, match="code_task is required"):
        validate_code_question("Choose a program.", options(), None)
    with pytest.raises(ValueError, match="code_task is required"):
        validate_code_question(fenced(STRUCT), [{"label": "A", "body": "Ana 31"}], None)
    validate_code_question("What is $x^2$?", [{"label": "A", "body": "$4$"}], None)
    validate_code_question(
        fenced("graph LR; A-->B", "mermaid"), [{"label": "A", "body": "A to B"}], None
    )


def test_purpose_is_advertised_for_single_and_group_questions_but_not_required_for_prose():
    schema = tools.MasteryQuizTool().get_definition().to_openai_schema()["function"]["parameters"]
    for contract in [schema, schema["properties"]["questions"]["items"]]:
        assert contract["properties"]["code_task"]["enum"] == list(CODE_TASKS)
        assert "code_task" not in contract["required"]
        assert "actual task" in contract["properties"]["code_task"]["description"]
        assert "corrected solution code" in contract["properties"]["question"]["description"]


def question(prompt="Which program is correct?"):
    return {
        "knowledge_point_id": "kp1",
        "question": prompt,
        "code_task": "select_program",
        "options": options(),
        "expected_answer": fenced(STRUCT_LAYOUT),
    }


@pytest.mark.asyncio
@pytest.mark.parametrize("location", ["single", "group_child", "group_intro"])
async def test_rejected_copy_preserves_state_then_corrected_retry_posts_one_card(
    service, monkeypatch, location
):
    monkeypatch.setattr(tools, "_new_service", lambda: service)
    end_turn = Mock()
    call = {"_mastery_path_id": "p", "_end_turn_on_card": end_turn}
    leak = "Which program is correct?\n\n" + fenced(STRUCT)
    if location == "single":
        malformed = {**call, **question(leak)}
        corrected = {**call, **question()}
    else:
        sibling = {
            "knowledge_point_id": "kp2",
            "question": "Name a value.",
            "expected_answer": "beta",
        }
        malformed = {
            **call,
            "questions": [sibling, question(leak if location == "group_child" else "Choose.")],
        }
        if location == "group_intro":
            malformed["question"] = leak
        corrected = {**call, "questions": [sibling, question()]}
    before = service.store.load("p").model_dump()
    result = await tools.MasteryQuizTool().execute(**malformed)
    assert not result.success
    assert "repeats an entire candidate program" in result.content
    assert "mastery_question" not in result.metadata
    assert service.store.load("p").model_dump() == before
    assert service.store.get_active_interaction("p") is None
    end_turn.assert_not_called()
    fixed = await tools.MasteryQuizTool().execute(**corrected)
    assert fixed.success, fixed.content
    end_turn.assert_called_once()
    pending = service.store.load("p").pending_question
    leaf = pending if location == "single" else pending.questions[1]
    assert leaf.choice_map[leaf.expected_answer] == fenced(STRUCT_LAYOUT)


@pytest.mark.asyncio
async def test_old_pending_replay_and_failed_replacement_do_not_rewrite_or_grade_it(
    service, monkeypatch
):
    monkeypatch.setattr(tools, "_new_service", lambda: service)
    original = PendingQuestion(
        question_id="old",
        knowledge_point_id="kp1",
        module_id="m",
        question_type="choice",
        prompt="Old saved question.\n\n" + fenced(STRUCT),
        options=options(),
        expected_answer="A",
    )
    service.register_question("p", original)
    replayed = await tools.MasteryQuizTool().execute(
        _mastery_path_id="p", pending_action="resume", resume_question_id="old"
    )
    assert replayed.success
    assert replayed.metadata["mastery_question"]["prompt"] == original.prompt
    before = service.store.load("p").model_dump()
    replacement = await tools.MasteryQuizTool().execute(
        _mastery_path_id="p",
        pending_action="replace",
        replace_question_id="old",
        replacement_request="Replace this question.",
        _learner_message="Replace this question.",
        **question("Choose.\n\n" + fenced(STRUCT)),
    )
    assert not replacement.success
    assert service.store.load("p").model_dump() == before
    assert service.store.get_active_interaction("p").interaction_id == "old"


@pytest.mark.asyncio
async def test_parent_purpose_is_not_silently_applied_to_all_group_children(service, monkeypatch):
    monkeypatch.setattr(tools, "_new_service", lambda: service)
    result = await tools.MasteryQuizTool().execute(
        _mastery_path_id="p", code_task="select_program", questions=[question(), question()]
    )
    assert not result.success and "not the parent" in result.content
    assert service.store.get_active_interaction("p") is None
