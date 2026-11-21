"""Purpose-specific checks for code questions, without solving or rewriting them."""

from __future__ import annotations

from io import StringIO
import re
import tokenize

from markdown_it import MarkdownIt

from .choice_format import _PROGRAM

CODE_TASKS = ("select_program", "predict_output", "debug_code")
_NON_SOURCE = {"text", "txt", "plaintext", "plain", "mermaid", "math", "latex", "csv", "tsv"}

# Match Rust lexical units, keeping literals and compound operators intact.
# Unknown or malformed literals use exact comparison instead of guessing.
_RUST_TOKEN = re.compile(
    r"\s+|//[^\n]*|/\*[\s\S]*?\*/"
    r'|(?:br|cr|r)(?P<hashes>#{0,255})"[\s\S]*?"(?P=hashes)'
    r'|(?:b|c)?"(?:\\[\s\S]|[^"\\])*"'
    r"|b?'(?:\\u\{[\da-fA-F_]+\}|\\x[\da-fA-F]{2}|\\[^\n]|[^'\\\n])'"
    r"|'[A-Za-z_]\w*"
    r"|(?:0[xX][\da-fA-F_]+|0[bB][01_]+|0[oO][0-7_]+|\d[\d_]*(?:\.(?!\.)[\d_]*)?"
    r"(?:[eE][+-]?[\d_]+)?)(?:[A-Za-z_]\w*)?"
    r"|[^\W\d]\w*"
    r"|>>=|<<=|\.\.=|\.\.\.|::|->|=>|&&|\|\||==|!=|<=|>=|\+=|-=|\*=|/=|%=|&=|\|=|\^=|<<|>>|\.\."
    r"|[{}()\[\],;:.?@#~+*/%&|^!=<>$-]"
)


def _signature(code: str, language: str) -> tuple | None:
    """Ignore layout only where token boundaries are understood safely."""
    if language in {"python", "py", "python3"}:
        result = []
        try:
            for token in tokenize.generate_tokens(StringIO(code).readline):
                if token.type == tokenize.ERRORTOKEN:
                    return None
                if token.type not in {tokenize.NL, tokenize.ENDMARKER}:
                    value = (
                        ""
                        if token.type in {tokenize.INDENT, tokenize.DEDENT, tokenize.NEWLINE}
                        else token.string
                    )
                    result.append((token.type, value))
        except (tokenize.TokenError, IndentationError, SyntaxError):
            return None
        return tuple(result)
    if language not in {"rust", "rs"}:
        return None
    result = []
    offset = 0
    while offset < len(code):
        match = _RUST_TOKEN.match(code, offset)
        if match is None:
            return None
        value = match.group()
        if not value.isspace():
            result.append(value)
        offset = match.end()
    return tuple(result)


def _code_blocks(markdown: str) -> list[tuple[str, str]]:
    blocks = []
    for token in MarkdownIt("commonmark", {"html": False}).parse(markdown):
        if token.type in {"fence", "code_block"}:
            language = token.info.strip().split(maxsplit=1)[0].lower() if token.info.strip() else ""
            language = {"rs": "rust", "py": "python", "python3": "python"}.get(language, language)
            blocks.append((language, token.content.strip("\r\n")))
        elif token.type == "inline":
            blocks.extend(
                ("", child.content.strip())
                for child in token.children or []
                if child.type == "code_inline" and _PROGRAM.search(child.content)
            )
    return blocks


def validate_code_question(
    question: str, options: list[dict[str, str]], code_task: str | None
) -> None:
    """Require an explicit purpose and reject copied whole candidate programs.

    The purpose is supplied by the model, not inferred from question wording.
    This catches duplication, not every semantic hint or an incorrect purpose.
    Unknown languages still receive exact-match protection. No code is executed.
    """
    purpose = code_task.strip() if isinstance(code_task, str) else code_task
    if purpose is not None and (not isinstance(purpose, str) or purpose not in CODE_TASKS):
        raise ValueError(
            "mastery_quiz.code_task must be select_program, predict_output or debug_code; "
            "omit it for a non-code question. Retry mastery_quiz with corrected arguments."
        )
    stem_blocks = _code_blocks(question)
    candidates = [(option["label"], _code_blocks(option["body"])) for option in options]
    if not purpose:
        if options and any(
            language not in _NON_SOURCE
            for language, _ in stem_blocks + [block for _, blocks in candidates for block in blocks]
        ):
            raise ValueError(
                "mastery_quiz.code_task is required for code choice questions. Use "
                "select_program to choose a candidate program, predict_output to evaluate "
                "a supplied program, or debug_code to inspect faulty code. "
                "Retry mastery_quiz with the matching purpose; keep the choices unchanged."
            )
        return
    if purpose != "select_program":
        return
    for label, blocks in candidates:
        for language, candidate in blocks:
            if not _PROGRAM.search(candidate):
                continue  # Shared identifiers and small snippets are not whole programs.
            signature = _signature(candidate, language)
            for stem_language, supplied in stem_blocks:
                compatible = stem_language == language or stem_language in _NON_SOURCE | {""}
                if candidate == supplied or (
                    compatible
                    and signature is not None
                    and signature == _signature(supplied, language)
                ):
                    raise ValueError(
                        f"mastery_quiz.question repeats an entire candidate program from "
                        f"options[{label}].body. For code_task=select_program, put candidate "
                        "programs only in options. Retry mastery_quiz with the task and "
                        "constraints in question, preserving the choices and answer key. "
                        "Do not relabel the task as predict_output or debug_code to bypass this check."
                    )
