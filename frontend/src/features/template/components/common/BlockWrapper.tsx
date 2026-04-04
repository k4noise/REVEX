import React, { useState, useRef } from "react";
import type { CommonBlockProps } from "../../types";
import { BlockMenu } from "./BlockMenu";
import {
  cx,
  modeBadgeClasses,
  groupBadgeClasses,
  isTableStructural,
  modeLabel,
} from "../../utils/styles";
import { effectiveDisplayMode } from "../../utils/visibility";

interface BlockWrapperProps extends CommonBlockProps {
  children: React.ReactNode;
}

export function BlockWrapper({
  element,
  updateElement,
  removeElement,
  moveUp,
  moveDown,
  indent,
  outdent,
  isReadOnly = false,
  filterMode = "all",
  parentType,
  inContainer = false,
  insideQuestion = false,
  parentChildrenCount,
  children,
}: BlockWrapperProps) {
  const [menuOpen, setMenuOpen] = useState(false);
  const menuButtonRef = useRef<HTMLButtonElement>(null);

  const inTableCell = parentType === "cell";
  const isStructural = isTableStructural(element.type);

  const mode = effectiveDisplayMode(element);
  const priorityText =
    mode === "always" ? "Ключевое" : mode === "prefer" ? "Важное" : null;

  const showPriorityPill =
    filterMode === "all" && priorityText && !inContainer && !insideQuestion;
  const showGroupPill = element.type === "container";
  const isOverlayType =
    element.type === "container" || element.type === "question";

  const canEditPriority =
    !isReadOnly &&
    !inTableCell &&
    !isStructural &&
    element.type !== "answer" &&
    element.type !== "container" &&
    element.type !== "question" &&
    !insideQuestion;

  const canIndentOutdent =
    !isReadOnly &&
    !inTableCell &&
    !isStructural &&
    element.type !== "answer" &&
    !insideQuestion;

  const canShowMenu =
    !isReadOnly &&
    !inTableCell &&
    !isStructural &&
    element.type !== "question" &&
    !insideQuestion;

  const deleteBlockedByGroupSingle =
    parentType === "container" && (parentChildrenCount ?? 0) === 1;
  const canDeleteBlock =
    !isReadOnly && canShowMenu && !deleteBlockedByGroupSingle;

  const contentRightPadding = canShowMenu ? "pr-14" : "";

  const renderPriority = () => {
    if (!showPriorityPill) return null;
    return (
      <span
        className={cx(
          "px-3 py-1.5 rounded-full border shadow-sm text-xs font-semibold",
          modeBadgeClasses(mode),
        )}
        title={modeLabel(mode)}
      >
        {priorityText}
      </span>
    );
  };

  const renderGroupPill = () => {
    if (!showGroupPill) return null;
    return (
      <span
        className={cx(
          "px-3 py-1.5 rounded-full border shadow-sm text-xs font-semibold",
          groupBadgeClasses,
        )}
      >
        Группа
      </span>
    );
  };

  const Controls = () => {
    if (!canShowMenu) return null;

    return (
      <div className="absolute right-3 top-2 z-50">
        <div className="relative isolate">
          <button
            ref={menuButtonRef}
            type="button"
            onClick={() => setMenuOpen((prev) => !prev)}
            aria-haspopup="menu"
            aria-expanded={menuOpen}
            className={cx(
              "h-9 w-9 rounded-xl border shadow-sm",
              "border-zinc-200 bg-white hover:bg-zinc-50 transition-colors",
              "dark:border-zinc-700 dark:bg-[#141416] dark:hover:bg-zinc-800",
              "opacity-0 group-hover:opacity-100 group-focus-within:opacity-100 transition-opacity",
              "pointer-events-none group-hover:pointer-events-auto group-focus-within:pointer-events-auto",
            )}
            title="Действия блока"
          >
            ⋯
          </button>

          <BlockMenu
            open={menuOpen}
            onClose={() => setMenuOpen(false)}
            anchorRef={menuButtonRef}
            element={element}
            canEditPriority={canEditPriority}
            canIndentOutdent={canIndentOutdent}
            canDeleteBlock={canDeleteBlock}
            onIndent={() => indent(element.id)}
            onOutdent={() => outdent(element.id)}
            onSetPriority={(value) =>
              updateElement(element.id, { displayMode: value })
            }
            onMoveUp={() => moveUp(element.id)}
            onMoveDown={() => moveDown(element.id)}
            onDelete={() => removeElement(element.id)}
          />
        </div>
      </div>
    );
  };

  return (
    <div
      className={cx(
        "group relative rounded-2xl isolate",
        "focus-within:ring-2 focus-within:ring-blue-500/20",
      )}
    >
      <Controls />
      {isOverlayType && (
        <div className="absolute left-3 top-2 z-40 flex gap-2">
          {renderPriority()}
          {renderGroupPill()}
        </div>
      )}
      <div className={contentRightPadding}>{children}</div>
    </div>
  );
}
