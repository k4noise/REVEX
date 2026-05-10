import type { DisplayMode, ElementType } from "../../../model/templateElement";

export const cx = (...classes: Array<string | false | null | undefined>) =>
  classes.filter(Boolean).join(" ");

export const modeBadgeClasses = (mode: DisplayMode | null) => {
  if (mode === "always")
    return "border-amber-200 bg-amber-50 text-amber-700 dark:border-amber-800/60 dark:bg-amber-900/20 dark:text-amber-200";
  if (mode === "prefer")
    return "border-blue-200 bg-blue-50 text-blue-700 dark:border-blue-900/60 dark:bg-blue-900/20 dark:text-blue-200";
  return "border-zinc-200 bg-zinc-50 text-zinc-700 dark:border-zinc-800 dark:bg-zinc-900/30 dark:text-zinc-200";
};

export const groupBadgeClasses =
  "border-zinc-200 bg-zinc-50 text-zinc-600 dark:border-zinc-800 dark:bg-zinc-900/30 dark:text-zinc-300";

export const isTableStructural = (type: ElementType) =>
  type === "row" || type === "cell";

export const isFixedHigh = (type: ElementType) =>
  type === "container" || type === "question" || type === "answer";

export const modeLabel = (mode: DisplayMode | null) =>
  mode === "always" ? "Ключевое" : mode === "prefer" ? "Важное" : "Обычное";
