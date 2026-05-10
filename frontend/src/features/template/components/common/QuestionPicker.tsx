import { useState, useRef, useEffect, useMemo, type RefObject } from "react";
import type { QuestionReference } from "../../types";
import type { QuestionGroups } from "../../hooks/useQuestions";
import { cx } from "../../utils/styles";

const MAX_VISIBLE = 140;

interface QuestionPickerProps {
  open: boolean;
  onClose: () => void;
  groups: QuestionGroups;
  onPick: (question: QuestionReference) => void;
  triggerRef: RefObject<HTMLElement | null>;
}

export function QuestionPicker({
  open,
  onClose,
  groups,
  onPick,
  triggerRef,
}: QuestionPickerProps) {
  const popupRef = useRef<HTMLDivElement>(null);
  const [query, setQuery] = useState("");

  useEffect(() => {
    if (!open) {
      setQuery("");
      return;
    }
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    const handleClickOutside = (e: MouseEvent) => {
      const target = e.target as Node;
      if (popupRef.current?.contains(target)) return;
      if (triggerRef.current?.contains(target)) return;
      onClose();
    };
    document.addEventListener("keydown", handleKeyDown);
    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [open, onClose, triggerRef]);

  const filterList = (list: QuestionReference[], q: string) => {
    if (!q) return list;
    return list.filter((item) => {
      const searchable =
        `${item.marker ?? ""} ${item.text ?? ""} ${item.id}`.toLowerCase();
      return searchable.includes(q);
    });
  };

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return {
      questions: filterList(groups.questions, q),
      tableCells: filterList(groups.tableCells, q),
    };
  }, [query, groups.questions, groups.tableCells]);

  const totalCount = filtered.questions.length + filtered.tableCells.length;

  if (!open) return null;

  const renderItem = (item: QuestionReference) => (
    <button
      key={item.id}
      type="button"
      onClick={() => onPick(item)}
      className={cx(
        "w-full text-left px-3 py-2.5 rounded-lg text-sm transition-colors",
        "hover:bg-zinc-50 dark:hover:bg-zinc-800",
      )}
    >
      <div className="text-zinc-900 dark:text-zinc-100 font-medium leading-snug">
        {item.text || "Пустой вопрос"}
      </div>
      <div className="text-xs text-zinc-400 dark:text-zinc-500 mt-0.5 font-mono">
        {item.id}
      </div>
    </button>
  );

  return (
    <div
      ref={popupRef}
      className={cx(
        "absolute right-0 top-full mt-2 z-[200] w-[480px] max-w-[92vw] flex flex-col",
        "rounded-xl border border-zinc-200 bg-white shadow-xl",
        "dark:border-zinc-700 dark:bg-[#141416]",
        "max-h-[400px]",
      )}
      role="dialog"
    >
      <div className="px-3 pt-3">
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Поиск: номер / текст / id..."
          autoFocus
          className={cx(
            "w-full h-10 rounded-lg px-3 text-sm outline-none",
            "bg-zinc-50 border border-zinc-200 text-zinc-800",
            "dark:bg-[#0f0f12] dark:border-zinc-700 dark:text-zinc-200",
            "focus:ring-2 focus:ring-blue-500/20",
          )}
        />
      </div>

      <div className="flex-1 overflow-auto p-3">
        {totalCount === 0 ? (
          <div className="px-2 py-3 text-sm text-zinc-500">
            Ничего не найдено
          </div>
        ) : (
          <div className="space-y-1">
            {filtered.questions.length > 0 && (
              <>
                <div className="px-3 pt-2 pb-1 text-xs font-semibold uppercase tracking-wider text-zinc-400 dark:text-zinc-500">
                  Вопросы
                </div>
                {filtered.questions.slice(0, MAX_VISIBLE).map(renderItem)}
              </>
            )}

            {filtered.tableCells.length > 0 && (
              <>
                {filtered.questions.length > 0 && (
                  <div className="my-2 h-px bg-zinc-200 dark:bg-zinc-700" />
                )}
                <div className="px-3 pt-2 pb-1 text-xs font-semibold uppercase tracking-wider text-zinc-400 dark:text-zinc-500">
                  Ячейки таблиц
                </div>
                {filtered.tableCells.slice(0, MAX_VISIBLE).map(renderItem)}
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
