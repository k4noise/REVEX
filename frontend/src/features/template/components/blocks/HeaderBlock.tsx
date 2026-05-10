import { memo } from "react";
import type { CommonBlockProps } from "../../types";
import { cx, modeBadgeClasses, modeLabel } from "../../utils/styles";
import { AutoResizeTextarea } from "../common/AutoResizeTextarea";
import { effectiveDisplayMode } from "../../utils/visibility";

export const HeaderBlock = memo(function HeaderBlock({
  element,
  updateElement,
  isReadOnly,
  filterMode,
}: CommonBlockProps) {
  const level = element.level ?? 1;
  const size =
    level === 1
      ? "text-4xl font-bold"
      : level === 2
        ? "text-2xl font-semibold"
        : "text-xl font-semibold";

  const mode = effectiveDisplayMode(element);
  const priorityText =
    mode === "always" ? "Ключевое" : mode === "prefer" ? "Важное" : null;
  const showPriorityPill = filterMode === "all" && priorityText;

  return (
    <div className="py-2">
      <div className="flex items-center gap-2">
        {showPriorityPill && (
          <span
            className={cx(
              "px-3 py-1.5 rounded-full border shadow-sm text-xs font-semibold",
              modeBadgeClasses(mode),
            )}
            title={modeLabel(mode)}
          >
            {priorityText}
          </span>
        )}
        <AutoResizeTextarea
          value={element.data || ""}
          onChange={(val) => updateElement(element.id, { data: val })}
          readOnly={isReadOnly}
          className={cx(
            "w-full text-zinc-900 dark:text-zinc-50",
            "placeholder:text-zinc-300 dark:placeholder:text-zinc-700",
            size,
          )}
          placeholder={`Заголовок (уровень ${level})...`}
        />
      </div>
    </div>
  );
});
