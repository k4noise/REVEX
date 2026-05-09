import { useRef, useState, useCallback, memo } from "react";
import type { CommonBlockProps } from "../../types";
import {
  getQuestionGradingStatus,
  gradingBorderColor,
  gradingBgTint,
} from "../../types";
import { cx } from "../../utils/styles";
import { shouldHideMarkers } from "../../utils/visibility";
import { AutoResizeTextarea } from "../common/AutoResizeTextarea";
import { QuestionPicker } from "../common/QuestionPicker";
import { BlocksList } from "../BlocksList";
import { insertVar } from "../../utils/questions";

export const QuestionBlock = memo(function QuestionBlock(
  props: CommonBlockProps,
) {
  const {
    element,
    updateElement,
    isReadOnly,
    isReportMode,
    isGradingMode,
    filterMode = "all",
    inContainer,
    answerGrading,
    availableQuestions,
    ...restProps
  } = props;

  const [pickerOpen, setPickerOpen] = useState(false);
  const pickerWrapRef = useRef<HTMLDivElement>(null);
  const lastFocusedRef = useRef<{
    elementId: string;
    textarea: HTMLTextAreaElement;
  } | null>(null);

  const hideMarkers = shouldHideMarkers(filterMode);
  const readOnly = isReadOnly || isReportMode || isGradingMode;

  const hasMarker = !!(element.marker && element.marker.trim());
  const isViewMode = isGradingMode || isReportMode || isReadOnly;
  const hideMarkerInput = hideMarkers || (isViewMode && !hasMarker);
  const canEditMarker = !isReadOnly && !isGradingMode && !isReportMode;
  const canInsertParams =
    !isReadOnly &&
    !isGradingMode &&
    !isReportMode &&
    !!availableQuestions &&
    availableQuestions.all.length > 0;

  const isGradedView = !isGradingMode && answerGrading !== undefined;

  const qStatus =
    isGradingMode || isGradedView
      ? getQuestionGradingStatus(element, answerGrading)
      : null;

  const borderClass = qStatus
    ? gradingBorderColor[qStatus]
    : "border-zinc-200 dark:border-zinc-800";

  const bgClass = qStatus
    ? gradingBgTint[qStatus]
    : "bg-zinc-50/60 dark:bg-zinc-900/30";

  const handleFocusCapture = useCallback((e: React.FocusEvent) => {
    const target = e.target;
    if (!(target instanceof HTMLTextAreaElement)) return;

    const block = target.closest("[data-element-id]");
    if (!block) return;

    const elementId = block.getAttribute("data-element-id");
    if (elementId) {
      lastFocusedRef.current = { elementId, textarea: target };
    }
  }, []);

  const handlePickParam = useCallback(
    (q: { id: string }) => {
      const active = lastFocusedRef.current;
      if (!active) return;

      const ta = active.textarea;
      const currentText = ta.value;
      const start = ta.selectionStart ?? currentText.length;
      const end = ta.selectionEnd ?? start;

      const { next, cursor } = insertVar(currentText, q.id, start, end);
      updateElement(active.elementId, { data: next });

      requestAnimationFrame(() => {
        ta.focus();
        ta.setSelectionRange(cursor, cursor);
      });

      setPickerOpen(false);
    },
    [updateElement],
  );

  return (
    <div
      className={cx(
        "my-8 rounded-2xl border p-6 transition-colors",
        borderClass,
        bgClass,
      )}
      onFocusCapture={canInsertParams ? handleFocusCapture : undefined}
    >
      <div className="flex items-start gap-2">
        {!hideMarkerInput &&
          (canEditMarker ? (
            <input
              type="text"
              value={element.marker || ""}
              onChange={(e) =>
                updateElement(element.id, { marker: e.target.value })
              }
              aria-label="Маркер вопроса"
              className={cx(
                "mt-1 w-14 shrink-0 text-right text-sm font-semibold text-zinc-400 outline-none bg-transparent",
                "dark:text-zinc-500",
                "focus:ring-2 focus:ring-blue-500/20 focus:rounded",
              )}
              placeholder="1)"
            />
          ) : (
            <span className="mt-1 shrink-0 font-semibold text-zinc-500 dark:text-zinc-400">
              {element.marker}
            </span>
          ))}

        <div className="flex-1">
          <AutoResizeTextarea
            value={element.data || ""}
            onChange={(val) => {
              if (readOnly) return;
              updateElement(element.id, { data: val });
            }}
            readOnly={readOnly}
            className={cx(
              "w-full font-semibold text-zinc-900 outline-none text-lg px-1 py-0.5",
              "placeholder:text-zinc-400 dark:text-zinc-100 dark:placeholder:text-zinc-600",
            )}
            placeholder="Текст вопроса..."
          />
        </div>

        {canInsertParams && (
          <div ref={pickerWrapRef} className="relative shrink-0">
            <button
              type="button"
              onClick={() => setPickerOpen((prev) => !prev)}
              className={cx(
                "mt-1 px-3 py-1.5 text-sm font-medium rounded-lg border transition-colors",
                pickerOpen
                  ? "border-blue-500 bg-blue-50 text-blue-700 dark:border-blue-600 dark:bg-blue-900/20 dark:text-blue-300"
                  : "border-zinc-200 bg-zinc-50 text-zinc-600 hover:bg-zinc-100 hover:text-blue-600 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-400 dark:hover:bg-zinc-700 dark:hover:text-blue-400",
              )}
            >
              + Параметр
            </button>

            <QuestionPicker
              open={pickerOpen}
              onClose={() => setPickerOpen(false)}
              groups={availableQuestions!}
              onPick={handlePickParam}
              triggerRef={pickerWrapRef}
            />
          </div>
        )}
      </div>

      {element.children && element.children.length > 0 && (
        <div className="mt-4 space-y-3">
          <BlocksList
            {...restProps}
            updateElement={updateElement}
            isReadOnly={isReadOnly}
            isReportMode={isReportMode}
            isGradingMode={isGradingMode}
            filterMode={filterMode}
            elements={element.children}
            parentType="question"
            forceShowAll={true}
            inContainer={inContainer}
            insideQuestion={true}
            answerGrading={answerGrading}
            availableQuestions={availableQuestions}
          />
        </div>
      )}
    </div>
  );
});
