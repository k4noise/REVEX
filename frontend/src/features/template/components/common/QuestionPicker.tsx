import React, { useState, useRef, useEffect, useMemo } from "react";
import { createPortal } from "react-dom";
import type { QuestionReference } from "../../types";
import { cx } from "../../utils/styles";

interface QuestionPickerProps {
  disabled?: boolean;
  questions: QuestionReference[];
  onPick: (question: QuestionReference) => void;
}

export function QuestionPicker({
  disabled,
  questions,
  onPick,
}: QuestionPickerProps) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const buttonRef = useRef<HTMLButtonElement>(null);
  const popupRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };

    const handleClickOutside = (e: MouseEvent | TouchEvent) => {
      const target = e.target as Node | null;
      if (!target) return;
      if (buttonRef.current?.contains(target)) return;
      if (popupRef.current?.contains(target)) return;
      setOpen(false);
    };

    document.addEventListener("keydown", handleKeyDown);
    document.addEventListener("mousedown", handleClickOutside);
    document.addEventListener("touchstart", handleClickOutside);

    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      document.removeEventListener("mousedown", handleClickOutside);
      document.removeEventListener("touchstart", handleClickOutside);
    };
  }, [open]);

  const filteredQuestions = useMemo(() => {
    const searchQuery = query.trim().toLowerCase();
    if (!searchQuery) return questions;

    return questions.filter((question) => {
      const searchableText =
        `${question.marker ?? ""} ${question.text ?? ""} ${question.id}`.toLowerCase();
      return searchableText.includes(searchQuery);
    });
  }, [query, questions]);

  return (
    <div className="relative shrink-0 isolate">
      <button
        ref={buttonRef}
        type="button"
        disabled={disabled}
        onClick={() => setOpen((prev) => !prev)}
        className={cx(
          "h-10 px-4 rounded-lg text-sm font-semibold border transition-colors",
          "border-blue-600 bg-blue-600 text-white hover:bg-blue-700",
          "disabled:opacity-40",
          "focus:outline-none focus:ring-2 focus:ring-blue-500/30",
        )}
        aria-haspopup="dialog"
        aria-expanded={open}
        title="Вставить параметр"
      >
        + Добавить параметр
      </button>

      {open &&
        createPortal(
          <div
            ref={popupRef}
            className={cx(
              "fixed z-[9999] w-[560px] max-w-[92vw]",
              "rounded-xl border border-zinc-200 bg-white shadow-xl",
              "dark:border-zinc-700 dark:bg-[#141416]",
            )}
            style={{
              top: buttonRef.current
                ? buttonRef.current.getBoundingClientRect().bottom + 8
                : 0,
              left: buttonRef.current
                ? buttonRef.current.getBoundingClientRect().right - 560
                : 0,
            }}
            role="dialog"
            aria-modal="false"
          >
            <div className="p-3">
              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Поиск: номер / текст / id…"
                className={cx(
                  "w-full h-10 rounded-lg px-3 text-sm outline-none",
                  "bg-zinc-50 border border-zinc-200 text-zinc-800",
                  "dark:bg-[#0f0f12] dark:border-zinc-700 dark:text-zinc-200",
                  "focus:ring-2 focus:ring-blue-500/20",
                )}
              />
            </div>

            <div className="max-h-80 overflow-auto p-3 pt-0">
              {filteredQuestions.length === 0 ? (
                <div className="px-2 py-3 text-sm text-zinc-500">
                  Ничего не найдено
                </div>
              ) : (
                <div className="space-y-2">
                  {filteredQuestions.slice(0, 140).map((question) => (
                    <button
                      key={question.id}
                      type="button"
                      onClick={() => {
                        onPick(question);
                        setOpen(false);
                        setQuery("");
                      }}
                      className={cx(
                        "w-full text-left px-3 py-2 rounded-lg text-sm transition-colors",
                        "hover:bg-zinc-50 dark:hover:bg-zinc-800",
                      )}
                    >
                      <div className="text-zinc-900 dark:text-zinc-100 font-semibold whitespace-normal leading-snug">
                        {question.marker ? `${question.marker} ` : ""}
                        {question.text || "Пустой вопрос"}
                      </div>
                      <div className="text-[11px] text-zinc-500 break-all">
                        {question.id}
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>,
          document.body,
        )}
    </div>
  );
}
