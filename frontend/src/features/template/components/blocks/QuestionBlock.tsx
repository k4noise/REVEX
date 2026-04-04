import React from "react";
import type { CommonBlockProps } from "../../types";
import { cx } from "../../utils/styles";
import { shouldHideMarkers } from "../../utils/visibility";
import { AutoResizeTextarea } from "../common/AutoResizeTextarea";
import { BlocksList } from "../BlocksList";

export function QuestionBlock(props: CommonBlockProps) {
  const {
    element,
    updateElement,
    isReadOnly,
    filterMode = "all",
    forceShowAll,
    inContainer,
    ...restProps
  } = props;

  const hideMarkers = shouldHideMarkers(filterMode);

  return (
    <div
      className={cx(
        "my-6 rounded-2xl border border-blue-200 bg-blue-50/40 p-6",
        "dark:border-blue-900/50 dark:bg-blue-900/10",
      )}
    >
      <div className="flex items-start gap-3">
        {!hideMarkers && (
          <input
            type="text"
            value={element.marker || ""}
            onChange={(e) =>
              updateElement(element.id, { marker: e.target.value })
            }
            readOnly={isReadOnly}
            aria-label="Маркер вопроса"
            className={cx(
              "mt-1 w-20 shrink-0 rounded-xl px-3 py-2 text-right font-bold outline-none",
              "bg-white/70 border border-blue-200 text-blue-700",
              "dark:bg-[#141416] dark:border-blue-900/60 dark:text-blue-200",
              "focus:ring-2 focus:ring-blue-500/20",
            )}
            placeholder="1)"
          />
        )}
        <div className="flex-1">
          <AutoResizeTextarea
            value={element.data || ""}
            onChange={(val) => updateElement(element.id, { data: val })}
            readOnly={isReadOnly}
            className={cx(
              "w-full font-semibold text-zinc-900 outline-none text-lg",
              "placeholder:text-blue-300 dark:text-zinc-100 dark:placeholder:text-blue-700",
            )}
            placeholder="Текст вопроса…"
          />
        </div>
      </div>

      {element.children && element.children.length > 0 && (
        <div className="mt-4 space-y-3">
          <BlocksList
            {...restProps}
            updateElement={updateElement}
            isReadOnly={isReadOnly}
            filterMode={filterMode}
            elements={element.children}
            parentType="question"
            forceShowAll={forceShowAll || false}
            inContainer={inContainer}
            insideQuestion={true}
          />
        </div>
      )}
    </div>
  );
}
