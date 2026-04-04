import React, { useRef, useEffect, useState, useLayoutEffect } from "react";
import { createPortal } from "react-dom";
import type {
  TemplateElementResponse,
  DisplayMode,
} from "@/model/templateElement";
import { cx } from "../../utils/styles";
import { effectiveDisplayMode } from "../../utils/visibility";

interface BlockMenuProps {
  open: boolean;
  onClose: () => void;
  anchorRef: React.RefObject<HTMLElement>;
  element: TemplateElementResponse;
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
  const [position, setPosition] = useState({ top: 0, left: 0 });

  useLayoutEffect(() => {
    if (!open || !anchorRef.current) return;
    const rect = anchorRef.current.getBoundingClientRect();
    setPosition({
      top: rect.bottom + 4,
      left: rect.right - 288,
    });
  }, [open, anchorRef]);

  useEffect(() => {
    if (!open) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
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

  const MenuItem = ({
    children,
    onClick,
    danger = false,
  }: {
    children: React.ReactNode;
    onClick: () => void;
    danger?: boolean;
  }) => (
    <button
      type="button"
      onClick={() => {
        onClick();
        onClose();
      }}
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

  const RadioOption = ({
    label,
    value,
    color,
  }: {
    label: string;
    value: DisplayMode | null;
    color: string;
  }) => {
    const isActive = currentMode === value;
    return (
      <button
        type="button"
        className={cx(
          "w-full flex items-center justify-between gap-3 px-3 py-2 text-sm rounded-lg transition-colors",
          "hover:bg-zinc-50 dark:hover:bg-zinc-800",
          isActive && "bg-zinc-100 dark:bg-zinc-800/80",
        )}
        onClick={() => {
          onSetPriority(value);
          onClose();
        }}
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
  };

  return createPortal(
    <div
      ref={menuRef}
      role="menu"
      style={{ top: position.top, left: position.left }}
      className={cx(
        "fixed z-[9999] w-72",
        "rounded-xl border border-zinc-200 bg-white shadow-xl",
        "dark:border-zinc-700 dark:bg-[#141416]",
      )}
    >
      <div className="p-2">
        {canIndentOutdent && (
          <>
            <div className="px-2 py-1 text-[11px] font-bold uppercase tracking-wider text-zinc-500">
              Вложенность
            </div>
            <MenuItem onClick={onIndent}>
              → Внутрь группы (в предыдущую)
            </MenuItem>
            <MenuItem onClick={onOutdent}>
              ← Из группы (на уровень выше)
            </MenuItem>
            <div className="my-2 h-px bg-zinc-100 dark:bg-zinc-800" />
          </>
        )}

        {canEditPriority && (
          <>
            <div className="px-2 py-1 text-[11px] font-bold uppercase tracking-wider text-zinc-500">
              Приоритет
            </div>
            <div className="mt-1 space-y-1">
              <RadioOption label="Обычный" value={null} color="bg-zinc-400" />
              <RadioOption label="Важное" value="prefer" color="bg-blue-500" />
              <RadioOption label="Ключевое" value="always" color="bg-red-500" />
            </div>
            <div className="my-2 h-px bg-zinc-100 dark:bg-zinc-800" />
          </>
        )}

        {!element.type.startsWith("question") && element.type !== "answer" && (
          <>
            <MenuItem onClick={onMoveUp}>↑ Переместить выше</MenuItem>
            <MenuItem onClick={onMoveDown}>↓ Переместить ниже</MenuItem>
            <div className="my-2 h-px bg-zinc-100 dark:bg-zinc-800" />
          </>
        )}

        {canDeleteBlock && (
          <MenuItem danger onClick={onDelete}>
            ✕ Удалить блок
          </MenuItem>
        )}
      </div>
    </div>,
    document.body,
  );
}
