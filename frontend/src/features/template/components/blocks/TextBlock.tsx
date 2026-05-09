import { memo } from "react";
import type { CommonBlockProps } from "../../types";
import { cx, modeBadgeClasses, modeLabel } from "../../utils/styles";
import {
  shouldHideMarkers,
  effectiveDisplayMode,
} from "../../utils/visibility";
import { AutoResizeTextarea } from "../common/AutoResizeTextarea";
import { ParamLegend } from "../common/ParamLegend";

export const TextBlock = memo(function TextBlock({
  element,
  updateElement,
  isReadOnly,
  isGradingMode,
  isReportMode,
  filterMode = "all",
  availableQuestions,
  parentType,
}: CommonBlockProps) {
  const hideMarkers = shouldHideMarkers(filterMode);
  const mode = effectiveDisplayMode(element);
  const priorityText =
    mode === "always" ? "Ключевое" : mode === "prefer" ? "Важное" : null;
  const showPriorityPill = filterMode === "all" && priorityText;

  const hasMarker = !!(element.marker && element.marker.trim());
  const isViewMode = isGradingMode || isReportMode || isReadOnly;
  const hideMarkerInput =
    hideMarkers ||
    ((isGradingMode || isReportMode) && !hasMarker) ||
    parentType === "cell";
  const canEditMarker = !isReadOnly && !isGradingMode && !isReportMode;

  const text = element.data || "";

  return (
    <div className="py-1">
      <div className="flex items-start gap-2 text-base text-zinc-800 dark:text-zinc-200 leading-relaxed">
        {showPriorityPill && (
          <span
            className={cx(
              "px-3 py-1.5 rounded-full border shadow-sm text-xs font-semibold shrink-0",
              modeBadgeClasses(mode),
            )}
            title={modeLabel(mode)}
          >
            {priorityText}
          </span>
        )}
        {!hideMarkerInput &&
          (canEditMarker ? (
            <input
              type="text"
              value={element.marker || ""}
              onChange={(e) =>
                updateElement(element.id, { marker: e.target.value })
              }
              aria-label="Маркер пункта"
              className={cx(
                "mt-[2px] w-12 shrink-0 text-right text-sm text-zinc-400 outline-none bg-transparent",
                "dark:text-zinc-500",
                "focus:ring-2 focus:ring-blue-500/20 focus:rounded",
              )}
              placeholder="*"
            />
          ) : (
            <span className="shrink-0 text-zinc-500 dark:text-zinc-400">
              {element.marker}
            </span>
          ))}
        <div className="flex-1 min-w-0">
          <AutoResizeTextarea
            value={text}
            onChange={(val) => updateElement(element.id, { data: val })}
            readOnly={isReadOnly}
            className="w-full leading-relaxed"
            placeholder="Введите текст..."
          />

          {!isViewMode &&
            availableQuestions &&
            availableQuestions.all.length > 0 && (
              <ParamLegend text={text} groups={availableQuestions} />
            )}
        </div>
      </div>
    </div>
  );
});
