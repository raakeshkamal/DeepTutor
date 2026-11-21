import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { MasteryQuestionCard } from "@/components/chat/home/MasteryQuestionCard";
import { AppShellProvider } from "@/context/AppShellContext";
import { initI18n } from "@/i18n/init";
import type { MasteryQuestion } from "@/lib/mastery-question";

initI18n("en");

const question = (overrides: Partial<MasteryQuestion> = {}): MasteryQuestion => ({
  questionId: "q-free",
  prompt: "Explain the difference between precision and recall.",
  questionType: "short",
  objectiveName: "Evaluation metrics",
  difficulty: "medium",
  attempt: 1,
  options: [],
  allowFreeText: true,
  ...overrides,
});

describe("MasteryQuestionCard", () => {
  it("preserves compiler output in the stem and keeps choices inline", async () => {
    const diagnostic = "error[E0382]: use of moved value\n  --> src/main.rs:5:20\n   |\n5  | println!(\"{city}\");";
    const { container } = render(
      <MasteryQuestionCard
        question={question({
          prompt: `Read the compiler output.\n\n\`\`\`text\n${diagnostic}\n\`\`\`\n\nWhich fix works?`,
          questionType: "choice",
          options: [{ label: "A", body: "Borrow with `&city`" }],
          allowFreeText: false,
        })}
        grade={null}
        answered={false}
        submittedAnswer=""
        onSubmit={() => true}
      />,
      { wrapper: AppShellProvider },
    );

    await waitFor(() => expect(container.querySelector("pre")?.textContent?.trimEnd()).toBe(diagnostic));
    expect(screen.getByText("Which fix works?").closest("pre")).toBeNull();
    const option = await screen.findByRole("button", { name: /Borrow with &city/ });
    expect(option.querySelector("code")).toHaveTextContent("&city");
    expect(option.querySelector("p, pre")).toBeNull();
  });

  it("shows indented code in a choice that still works by keyboard", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn(() => true);
    const code = ["fn main() {", "    let pair = (5, 8);", "", "    println!(\"{pair}\");", "}"].join("\n");
    render(
      <MasteryQuestionCard
        question={question({
          prompt: "Which program fails to compile?",
          questionType: "choice",
          options: [
            { label: "A", body: `\`\`\`rust\n${code}\n\`\`\`` },
            { label: "B", body: "Neither program" },
          ],
          allowFreeText: false,
        })}
        grade={null}
        answered={false}
        submittedAnswer=""
        onSubmit={onSubmit}
      />,
    );

    const choice = await screen.findByRole("button", { name: /fn main/ });
    expect(choice.querySelector("code")?.textContent?.trimEnd()).toBe(code);
    expect(choice.querySelector("code")?.parentElement).toHaveClass("whitespace-pre", "overflow-x-auto");
    expect(choice.querySelector("p, pre")).toBeNull();
    expect(screen.getByRole("button", { name: /Neither program/ }).querySelector("code")).toBeNull();

    choice.focus();
    await user.keyboard("{Enter}");
    await user.click(screen.getByRole("button", { name: "Submit" }));
    expect(onSubmit).toHaveBeenCalledWith({ text: "A", answers: [{ questionId: "q-free", text: "A" }] });
  });

  it("shows original evidence and assisted meaning without exposing a reference key", () => {
    render(<MasteryQuestionCard question={question({ visual: { task: "identification", answerCues: "visible", keyStatus: "unverified", hintsUsed: 1, sources: [{ imageUrl: "/api/knowledge-bases/kb/visual-assets/known", url: "/api/knowledge-bases/kb/files/book.pdf#page=4", sourcePath: "book.pdf", page: 4 }] } })} grade={null} answered={false} submittedAnswer="" onSubmit={() => true} />);
    expect(screen.getByRole("img", { name: "Original source evidence" })).toHaveAttribute("src", "/api/knowledge-bases/kb/visual-assets/known");
    expect(screen.getByText("Guided visual practice — this does not demonstrate independent mastery.")).toBeInTheDocument();
    expect(screen.getByText("The reference key is uncertain. This practice will remain ungraded.")).toBeInTheDocument();
    fireEvent.error(screen.getByRole("img"));
    expect(screen.getByRole("alert")).toHaveTextContent("The source image is unavailable");
  });
  it("keeps uncertain grades neutral and sends a source-review challenge", async () => {
    const user = userEvent.setup();
    const onChallenge = vi.fn(() => true);
    render(<MasteryQuestionCard question={question()} grade={{ questionId: "q-free", isCorrect: false, result: "ungraded", learnerAnswer: "ambiguous", correctLabel: "", correctBody: "", explanation: "Source evidence needs clarification." }} answered submittedAnswer="" onSubmit={() => true} onChallenge={onChallenge} />);
    expect(screen.getByText("Ungraded — mastery unchanged")).toBeInTheDocument();
    expect(screen.queryByText("Not quite")).toBeNull();
    await user.click(screen.getByRole("button", { name: "Review or challenge this assessment" }));
    expect(onChallenge).toHaveBeenCalledWith("q-free");
  });
  it("enables submit from a free-text-only question", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn(() => true);
    render(
      <MasteryQuestionCard
        question={question()}
        grade={null}
        answered={false}
        submittedAnswer=""
        onSubmit={onSubmit}
      />,
    );

    const submit = screen.getByRole("button", { name: "Submit" });
    expect(submit).toBeDisabled();

    await user.type(screen.getByRole("textbox"), "Precision measures exactness");
    expect(submit).toBeEnabled();

    await user.click(submit);
    expect(onSubmit).toHaveBeenCalledWith({
      text: "Precision measures exactness",
      answers: [
        {
          questionId: "q-free",
          text: "Precision measures exactness",
        },
      ],
    });
  });

  it("keeps explicit free text working alongside choices", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn(() => true);
    render(
      <MasteryQuestionCard
        question={question({
          questionId: "q-choice",
          options: [{ label: "A", body: "Precision measures exactness" }],
        })}
        grade={null}
        answered={false}
        submittedAnswer=""
        onSubmit={onSubmit}
      />,
    );

    await user.click(screen.getByRole("button", { name: /Answer in my own words/ }));
    await user.type(screen.getByRole("textbox"), "They answer different errors");
    await user.click(screen.getByRole("button", { name: "Submit" }));

    expect(onSubmit).toHaveBeenCalledWith({
      text: "They answer different errors",
      answers: [
        {
          questionId: "q-choice",
          text: "They answer different errors",
        },
      ],
    });
  });
});
