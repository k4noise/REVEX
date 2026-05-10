import { useState, useRef, useEffect } from "react";
import { cx } from "../../utils/styles";

interface InsertDividerProps {
  onInsertText?: () => void;
  onInsertQA?: () => void;
  onInsertImage?: () => void;
  onInsertGroup?: () => void;
}

export function InsertDivider({
  onInsertText,
  onInsertQA,
  onInsertImage,
  onInsertGroup,
}: InsertDividerProps) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;

    const handleClick = (e: MouseEvent) => {
      if (!ref.current?.contains(e.target as Node)) {
        setOpen(false);
      }
    };

    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setOpen(false);
      }
    };

    document.addEventListener("mousedown", handleClick);
    document.addEventListener("keydown", handleKey);

    return () => {
      document.removeEventListener("mousedown", handleClick);
      document.removeEventListener("keydown", handleKey);
    };
  }, [open]);

  const pick = (fn: () => void) => () => {
    fn();
    setOpen(false);
  };

  const hasAnyActions =
    !!onInsertText || !!onInsertQA || !!onInsertImage || !!onInsertGroup;

  if (!hasAnyActions) {
    return null;
  }

  return (
    <div
      ref={ref}
      className="group/divider relative flex items-center justify-center h-3 -my-0.5"
    >
      <div className="absolute inset-x-0 top-1/2 h-px bg-zinc-200/0 group-hover/divider:bg-zinc-200 dark:group-hover/divider:bg-zinc-800 transition-colors" />

      <button
        type="button"
        onClick={() => setOpen((prev) => !prev)}
        className={cx(
          "relative z-10 flex h-5 w-5 items-center justify-center rounded-full text-xs font-bold transition-all",
          "opacity-0 group-hover/divider:opacity-100",
          "bg-zinc-200 text-zinc-500 hover:bg-blue-500 hover:text-white",
          "dark:bg-zinc-700 dark:text-zinc-400 dark:hover:bg-blue-600 dark:hover:text-white",
        )}
        title="Вставить блок"
      >
        +
      </button>

      {open && (
        <div
          className={cx(
            "absolute top-full mt-1 z-[200] w-56",
            "rounded-xl border border-zinc-200 bg-white shadow-lg",
            "dark:border-zinc-700 dark:bg-[#141416]",
          )}
        >
          <div className="p-1">
            {onInsertText && (
              <button
                type="button"
                onClick={pick(onInsertText)}
                className="w-full text-left px-3 py-2 text-sm rounded-lg hover:bg-zinc-50 dark:hover:bg-zinc-800 transition-colors text-zinc-700 dark:text-zinc-300"
              >
                Текст
              </button>
            )}

            {onInsertQA && (
              <button
                type="button"
                onClick={pick(onInsertQA)}
                className="w-full text-left px-3 py-2 text-sm rounded-lg hover:bg-zinc-50 dark:hover:bg-zinc-800 transition-colors text-zinc-700 dark:text-zinc-300"
              >
                Вопрос + Ответ
              </button>
            )}

            {onInsertImage && (
              <button
                type="button"
                onClick={pick(onInsertImage)}
                className="w-full text-left px-3 py-2 text-sm rounded-lg hover:bg-zinc-50 dark:hover:bg-zinc-800 transition-colors text-zinc-700 dark:text-zinc-300"
              >
                Картинка
              </button>
            )}

            {onInsertGroup && (
              <button
                type="button"
                onClick={pick(onInsertGroup)}
                className="w-full text-left px-3 py-2 text-sm rounded-lg hover:bg-zinc-50 dark:hover:bg-zinc-800 transition-colors text-zinc-700 dark:text-zinc-300"
              >
                Группа
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
