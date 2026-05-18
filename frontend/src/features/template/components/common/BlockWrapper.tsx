import { useState, useRef, type ReactNode, memo } from "react";
import type { CommonBlockProps } from "../../types";
import { useBlockPermissions } from "../../hooks/useBlockPermissions";
import { BlockMenu } from "./BlockMenu";
import { cx } from "../../utils/styles";

interface BlockWrapperProps extends CommonBlockProps {
  children: ReactNode;
}

export const BlockWrapper = memo(function BlockWrapper(
  props: BlockWrapperProps,
) {
  const {
    element,
    updateElement,
    removeElement,
    moveUp,
    moveDown,
    indent,
    outdent,
    children,
  } = props;

  const [menuOpen, setMenuOpen] = useState(false);
  const menuButtonRef = useRef<HTMLButtonElement>(null);

  const {
    canShowMenu,
    canMove,
    canEditPriority,
    canIndentOutdent,
    canDeleteBlock,
  } = useBlockPermissions(props);

  const contentRightPadding = canShowMenu ? "pr-14" : "";

  return (
    <div className="group relative rounded-2xl" data-element-id={element.id}>
      {canShowMenu && (
        <div className="absolute right-3 top-2 z-20">
          <div className="relative">
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
                "opacity-0 group-hover:opacity-100 group-focus-within:opacity-100 focus:opacity-100 transition-opacity",
              )}
              title="Действия блока"
            >
              ...
            </button>

            <BlockMenu
              open={menuOpen}
              onClose={() => setMenuOpen(false)}
              anchorRef={menuButtonRef}
              element={element}
              canMove={canMove}
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
      )}

      <div className={contentRightPadding}>{children}</div>
    </div>
  );
});
