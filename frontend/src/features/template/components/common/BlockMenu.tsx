import {
  useRef,
  useEffect,
  useState,
  useLayoutEffect,
  type ReactNode,
  type RefObject,
  memo,
} from "react";
import { createPortal } from "react-dom";
import type {
  TemplateElementResponse,
  DisplayMode,
} from "../../../../model/templateElement";
import { cx } from "../../utils/styles";
import { effectiveDisplayMode } from "../../utils/visibility";

interface MenuItemProps {
  children: ReactNode;
  onClick: () => void;
  danger?: boolean;
}

const MenuItem = memo(function MenuItem({
  children,
  onClick,
  danger = false,
}: MenuItemProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cx(
        "w-full text-left px-3 py-2 text-sm rounded-lg transition-colors",
        danger
          ? "text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 dark:text-red-300"
          : "text-zinc-700 hover:bg-zinc-50 dark:text-zinc-200 dark:hover:bg-zinc-800",
      )}
      role="menuitem"
    >
      {children}
    </button>
  );
});

interface RadioOptionProps {
  label: string;
  value: DisplayMode | null;
  color: string;
  isActive: boolean;
  onClick: () => void;
}

const RadioOption = memo(function RadioOption({
  label,
  color,
  isActive,
  onClick,
}: RadioOptionProps) {
  return (
    <button
      type="button"
      className={cx(
        "w-full flex items-center justify-between gap-3 px-3 py-2 text-sm rounded-lg transition-colors",
        "hover:bg-zinc-50 dark:hover:bg-zinc-800",
        isActive && "bg-zinc-100 dark:bg-zinc-800/80",
      )}
      onClick={onClick}
      role="menuitemradio"
      aria-checked={isActive}
    >
      <span className="flex items-center gap-2">
        <span className={cx("h-2.5 w-2.5 rounded-full", color)} />
        <span className="text-zinc-800 dark:text-zinc-100">{label}</span>
      </span>
      {isActive && <span className="text-xs text-zinc-500">✓</span>}
    </button>
  );
});

const MenuDivider = memo(function MenuDivider() {
  return <div className="my-2 h-px bg-zinc-100 dark:bg-zinc-800" />;
});

interface BlockMenuProps {
  open: boolean;
  onClose: () => void;
  anchorRef: RefObject<HTMLElement | null>;
  element: TemplateElementResponse;
  canMove: boolean;
  canEditPriority: boolean;
  canIndentOutdent: boolean;
  canDeleteBlock: boolean;
  onIndent: () => void;
  onOutdent: () => void;
  onSetPriority: (value: DisplayMode | null) => void;
  onMoveUp: () => void;
  onMoveDown: () => void;
  onDelete: () => void;
}

export function BlockMenu({
  open,
  onClose,
  anchorRef,
  element,
  canMove,
  canEditPriority,
  canIndentOutdent,
  canDeleteBlock,
  onIndent,
  onOutdent,
  onSetPriority,
  onMoveUp,
  onMoveDown,
  onDelete,
}: BlockMenuProps) {
  const menuRef = useRef<HTMLDivElement>(null);
  const [position, setPosition] = useState({ top: -9999, left: -9999 });

  useLayoutEffect(() => {
    if (!open || !anchorRef.current || !menuRef.current) return;

    const anchorRect = anchorRef.current.getBoundingClientRect();
    const menuRect = menuRef.current.getBoundingClientRect();
    const viewportHeight = window.innerHeight;
    const viewportWidth = window.innerWidth;

    const spaceBelow = viewportHeight - anchorRect.bottom;
    const spaceAbove = anchorRect.top;

    const placement =
      spaceBelow < menuRect.height && spaceAbove > spaceBelow
        ? "top"
        : "bottom";

    let top =
      placement === "bottom"
        ? anchorRect.bottom + 4
        : anchorRect.top - menuRect.height - 4;

    let left = anchorRect.right - menuRect.width;

    top = Math.max(8, Math.min(top, viewportHeight - menuRect.height - 8));
    left = Math.max(8, Math.min(left, viewportWidth - menuRect.width - 8));

    setPosition({ top, left });
  }, [open, anchorRef]);

  useEffect(() => {
    if (!open) return;

    const firstItem =
      menuRef.current?.querySelector<HTMLElement>('[role^="menuitem"]');
    firstItem?.focus();

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
        anchorRef.current?.focus();
      }
    };

    const handleClickOutside = (e: MouseEvent | TouchEvent) => {
      const target = e.target as Node | null;
      if (!target) return;
      if (menuRef.current?.contains(target)) return;
      if (anchorRef.current?.contains(target)) return;
      onClose();
    };

    document.addEventListener("keydown", handleKeyDown);
    document.addEventListener("mousedown", handleClickOutside);
    document.addEventListener("touchstart", handleClickOutside);

    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      document.removeEventListener("mousedown", handleClickOutside);
      document.removeEventListener("touchstart", handleClickOutside);
    };
  }, [open, onClose, anchorRef]);

  if (!open) return null;

  const currentMode = effectiveDisplayMode(element);

  const closeAnd = (fn: () => void) => () => {
    fn();
    onClose();
  };

  return createPortal(
    <div
      ref={menuRef}
      role="menu"
      style={{ top: position.top, left: position.left, position: "fixed" }}
      className={cx(
        "z-[9999] w-72",
        "rounded-xl border border-zinc-200 bg-white shadow-xl",
        "dark:border-zinc-700 dark:bg-[#141416]",
        position.top < 0 && "opacity-0",
      )}
    >
      <div className="p-2">
        {canIndentOutdent && (
          <>
            <div className="px-2 py-1 text-[11px] font-bold uppercase tracking-wider text-zinc-500">
              Вложенность
            </div>
            <MenuItem onClick={closeAnd(onIndent)}>
              → Внутрь группы (в предыдущую)
            </MenuItem>
            <MenuItem onClick={closeAnd(onOutdent)}>
              ← Из группы (на уровень выше)
            </MenuItem>
            <MenuDivider />
          </>
        )}

        {canEditPriority && (
          <>
            <div className="px-2 py-1 text-[11px] font-bold uppercase tracking-wider text-zinc-500">
              Приоритет
            </div>
            <div className="mt-1 space-y-1">
              <RadioOption
                label="Обычный"
                value={null}
                color="bg-zinc-400"
                isActive={currentMode === null}
                onClick={closeAnd(() => onSetPriority(null))}
              />
              <RadioOption
                label="Важное"
                value="prefer"
                color="bg-blue-500"
                isActive={currentMode === "prefer"}
                onClick={closeAnd(() => onSetPriority("prefer"))}
              />
              <RadioOption
                label="Ключевое"
                value="always"
                color="bg-red-500"
                isActive={currentMode === "always"}
                onClick={closeAnd(() => onSetPriority("always"))}
              />
            </div>
            <MenuDivider />
          </>
        )}

        {canMove && (
          <>
            <MenuItem onClick={closeAnd(onMoveUp)}>↑ Переместить выше</MenuItem>
            <MenuItem onClick={closeAnd(onMoveDown)}>
              ↓ Переместить ниже
            </MenuItem>
            <MenuDivider />
          </>
        )}

        {canDeleteBlock && (
          <MenuItem danger onClick={closeAnd(onDelete)}>
            ✕ Удалить блок
          </MenuItem>
        )}
      </div>
    </div>,
    document.body,
  );
}
