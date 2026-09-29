// The theme toggle flips data-theme on <html>, relabels itself, and remembers the choice.
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, it } from "vitest";
import ThemeToggle from "../src/components/ThemeToggle";

beforeEach(() => {
  localStorage.clear();
  document.documentElement.dataset.theme = "light";
});

it("switches light to dark and back, persisting each choice", async () => {
  render(<ThemeToggle />);
  const button = screen.getByRole("button", { name: "Switch to dark mode" });
  expect(button).toHaveAttribute("aria-pressed", "false");

  await userEvent.click(button);
  expect(document.documentElement.dataset.theme).toBe("dark");
  expect(localStorage.getItem("theme")).toBe("dark");
  expect(screen.getByRole("button", { name: "Switch to light mode" })).toHaveAttribute(
    "aria-pressed",
    "true",
  );

  await userEvent.click(screen.getByRole("button", { name: "Switch to light mode" }));
  expect(document.documentElement.dataset.theme).toBe("light");
  expect(localStorage.getItem("theme")).toBe("light");
});

it("starts from the theme index.html already applied", () => {
  document.documentElement.dataset.theme = "dark";
  render(<ThemeToggle />);
  expect(screen.getByRole("button", { name: "Switch to light mode" })).toBeInTheDocument();
});
