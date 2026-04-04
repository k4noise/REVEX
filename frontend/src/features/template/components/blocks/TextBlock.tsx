import React from "react";
import type { CommonBlockProps } from "../../types";
import { cx, modeBadgeClasses, modeLabel } from "../../utils/styles";
import {
  shouldHideMarkers,
  effectiveDisplayMode,
} from "../../utils/visibility";
import { AutoResizeTextarea } from "../common/AutoResizeTextarea";

export function TextBlock({
  element,
  updateElement,
  isReadOnly,
  filterMode = "all",
  inContainer,
  insideQuestion,
}: CommonBlockProps) {
  const hideMarkers = shouldHideMarkers(filterMode);
  const mode = effectiveDisplayMode(element);
  const priorityText =
    mode === "always" ? "Ключевое" : mode === "prefer" ? "Важное" : null;
  const showPriorityPill =
    filterMode === "all" && priorityText && !inContainer && !insideQuestion;

  return (
    <div className="py-1">
      <div className="flex items-start gap-3 text-base text-zinc-800 dark:text-zinc-200 leading-relaxed">
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
        {!hideMarkers && (
          <input
            type="text"
            value={element.marker || ""}
            onChange={(e) =>
              updateElement(element.id, { marker: e.target.value })
            }
            readOnly={isReadOnly}
            aria-label="Маркер пункта"
            className={cx(
              "mt-[2px] w-14 shrink-0 rounded-lg px-2 py-1 text-right font-semibold outline-none",
              "bg-zinc-100 text-right font-semibold text-zinc-500",
              "dark:bg-zinc-800 dark:text-zinc-400",
              "focus:ring-2 focus:ring-blue-500/20",
            )}
            placeholder="•"
          />
        )}
        <AutoResizeTextarea
          value={element.data || ""}
          onChange={(val) => updateElement(element.id, { data: val })}
          readOnly={isReadOnly}
          className="w-full flex-1 leading-relaxed"
          placeholder="Введите текст…"
        />
      </div>
    </div>
  );
}
