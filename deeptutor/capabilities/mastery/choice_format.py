"""Validate model-written code choices; never infer or rewrite source formatting."""

from __future__ import annotations

import re

from markdown_it import MarkdownIt

# These are source markers, not a compiler. Incorrect distractors must pass once
# they are readable. Short expressions, output values, prose and maths stay valid.
_PROGRAM = re.compile(
    r"^\s*(?:(?:pub(?:\([^)]*\))?|async|unsafe|export|public|private|static)\s+)*"
    r"(?:(?:fn|def|function|func|fun)\s+\w+\s*(?:<[^>\n]*>)?\s*\("
    r"|(?:struct|enum|class|interface)\s+\w+[^{}\n]*\{)",
    re.MULTILINE,
)
_SOURCE = re.compile(
    r"^\s*(?:let|const|var)\s+[^\n;]*="
    r"|^\s*(?:println|print|printf)!?\s*\([^\n]*\)\s*;"
    r"|^\s*(?:return|import|from|use)\s+[^\n]*(?:;|\bimport\b)"
    r"|^\s*#\s*include\s*[<\"]",
    re.MULTILINE,
)


def validate_choice_format(options: list[dict[str, str]]) -> None:
    """Reject unreadable code before registering a question or ending its turn.

    Markdown parsing distinguishes real fences from inline code, and the error
    tells the model which option to repair. No code is compiled, autoformatted,
    repaired or substituted, including syntax errors used as distractors.
    """
    parser = MarkdownIt("commonmark", {"html": False})
    for option in options:
        body = option["body"]
        source_lines = body.splitlines()

        def reject(reason: str) -> None:
            raise ValueError(
                f"mastery_quiz.options[{option['label']}].body: {reason} "
                "Retry mastery_quiz with the same question and choices, formatting "
                "each code choice in a closed fenced Markdown block with a language "
                "tag, real line breaks and indentation. Do not change code tokens "
                "or repair deliberately incorrect code. Keep prose choices as prose."
            )

        for token in parser.parse(body):
            if token.type == "fence":
                closing = source_lines[token.map[1] - 1] if token.map else ""
                if not re.fullmatch(
                    rf" {{0,3}}{re.escape(token.markup[0])}{{{len(token.markup)},}}[ \t]*",
                    closing,
                ):
                    reject("the code fence is not closed on its own line.")
                if not re.fullmatch(r"[\w+#.-]+", token.info.strip()):
                    reject("the opening code fence needs a language tag, such as rust.")
                code_lines = token.content.splitlines()
                if not any(line.strip() for line in code_lines):
                    reject("the fenced code block is empty.")
                if any(len(line.expandtabs(4)) > 120 for line in code_lines):
                    reject(
                        "a code line exceeds 120 columns; lay out the code across readable lines."
                    )
                if _PROGRAM.search(token.content) and (
                    len([line for line in code_lines if line.strip()]) < 2
                    or not any(line[:1].isspace() for line in code_lines if line.strip())
                ):
                    reject(
                        "a program or declaration is flattened; use multiple indented code lines."
                    )
            elif token.type == "code_block":
                reject("indented code needs an explicit fenced Markdown block.")
            elif token.type == "inline":
                # Inspect both raw text and inline-code spans. Wrapping an entire
                # one-line program in single backticks does not make it readable.
                for child in token.children or []:
                    if child.type == "code_inline" and len(child.markup) >= 3:
                        reject(
                            "code fences need real line breaks and delimiters on their own lines."
                        )
                    if child.type in {"text", "code_inline"} and (
                        _PROGRAM.search(child.content) or _SOURCE.search(child.content)
                    ):
                        reject("source code is outside a fenced Markdown block.")
