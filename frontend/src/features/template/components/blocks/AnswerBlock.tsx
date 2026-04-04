import React, { useRef, useMemo, useEffect, useState } from "react";
import type { CommonBlockProps } from "../../types";
import { cx } from "../../utils/styles";
import { normalizeWeight } from "../../utils/validation";
import { formatPoints2 } from "../../utils/scoring";
import {
  buildQuestionsMap,
  normalizeVarsToIdOnly,
  extractVarIds,
  insertWithSpaces,
} from "../../utils/questions";
import { AutoResizeTextarea } from "../common/AutoResizeTextarea";
import { QuestionPicker } from "../common/QuestionPicker";

export function AnswerBlock({
  element,
  updateElement,
  isReadOnly,
  availableQuestions = [],
  globalScoring,
}: CommonBlockProps) {
  const answerRef = useRef<HTMLTextAreaElement>(null);
  const [paramsExpanded, setParamsExpanded] = useState(false);

  const questionsMap = useMemo(
    () => buildQuestionsMap(availableQuestions),
    [availableQuestions],
  );

  const raw = String(element.data ?? element.hint ?? "");
  const value = normalizeVarsToIdOnly(raw);

  useEffect(() => {
    if (isReadOnly) return;
    if (value !== raw) {
      updateElement(element.id, { data: value, hint: value });
    }
  }, [isReadOnly, element.id, raw, value, updateElement]);

  const score = globalScoring?.byAnswerId?.[element.id];
  const options = availableQuestions.filter(
    (q) => q.id !== element.parentElementId,
  );

  const insertVariable = (picked: (typeof availableQuestions)[0]) => {
    const variable = `{${picked.id}}`;
    const input = answerRef.current;

    if (!input) {
      const next = value ? value + " " + variable + " " : variable + " ";
      updateElement(element.id, { data: next, hint: next });
      return;
    }

    const start = input.selectionStart ?? value.length;
    const end = input.selectionEnd ?? value.length;
    const { next, cursor } = insertWithSpaces(value, variable, start, end);

    updateElement(element.id, { data: next, hint: next });

    setTimeout(() => {
      input.focus();
      input.setSelectionRange(cursor, cursor);
    }, 0);
  };

  const currentWeight = normalizeWeight(element.maxScore);

  const renderParamsPreview = () => {
    const ids = extractVarIds(value);
    if (ids.length === 0) return null;

    const uniqueIds = Array.from(new Set(ids));
    const shown = paramsExpanded ? uniqueIds : uniqueIds.slice(0, 2);
    const remaining = uniqueIds.length - shown.length;

    return (
      <div className="mt-4 rounded-xl border border-zinc-200 bg-zinc-50 p-4 dark:border-zinc-800 dark:bg-zinc-900/30">
        <div className="flex items-center justify-between gap-3 mb-2">
          <div className="font-bold text-zinc-700 dark:text-zinc-200">
            Параметры
          </div>
          {remaining > 0 && (
            <button
              type="button"
              onClick={() => setParamsExpanded((v) => !v)}
              className={cx(
                "text-sm font-semibold rounded-lg px-3 py-1",
                "border border-zinc-200 bg-white hover:bg-zinc-50",
                "dark:border-zinc-700 dark:bg-[#141416] dark:hover:bg-zinc-800",
              )}
            >
              {paramsExpanded ? "Свернуть" : `Ещё ${remaining}`}
            </button>
          )}
        </div>

        <div className="space-y-2">
          {shown.map((id) => {
            const question = questionsMap.get(id);
            const fullText = question
              ? `${question.marker ? question.marker + " " : ""}${question.text || ""}`.trim()
              : "";

            return (
              <div key={id} className="whitespace-normal leading-snug">
                <div className="text-zinc-700 dark:text-zinc-200 font-mono text-xs break-all">
                  {`{${id}}`}
                </div>
                <div className="text-zinc-900 dark:text-zinc-100 text-sm">
                  {question ? (
                    fullText || "Пустой вопрос"
                  ) : (
                    <span className="text-red-700 dark:text-red-300">
                      Параметр не найден
                    </span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    );
  };

  return (
    <div
      className={cx(
        "rounded-xl border border-zinc-200 bg-white p-5 shadow-sm",
        "dark:border-zinc-800 dark:bg-[#1A1A1D]",
      )}
    >
      <div className="flex flex-col gap-3">
        <div className="flex items-center justify-between gap-4">
          <div className="text-sm font-semibold text-zinc-700 dark:text-zinc-300">
            Эталонный ответ
          </div>
          {!isReadOnly && options.length > 0 && (
            <QuestionPicker
              disabled={isReadOnly}
              questions={options}
              onPick={insertVariable}
            />
          )}
        </div>

        <div className="flex flex-wrap items-center gap-4 text-sm text-zinc-600 dark:text-zinc-300">
          {score && (
            <span>
              Баллы:{" "}
              <span className="font-semibold text-zinc-900 dark:text-zinc-100">
                {formatPoints2(score.points)}
              </span>
            </span>
          )}

          <span className="flex items-center gap-2">
            Вес:
            <input
              type="number"
              min={0}
              max={20}
              step={1}
              inputMode="numeric"
              value={currentWeight}
              onChange={(e) => {
                const next = normalizeWeight(e.target.value);
                updateElement(element.id, { maxScore: next });
              }}
              readOnly={isReadOnly}
              className={cx(
                "w-24 rounded-xl px-3 py-2 text-sm font-semibold outline-none",
                "bg-zinc-50 border border-zinc-200 text-zinc-800",
                "dark:bg-[#141416] dark:border-zinc-700 dark:text-zinc-200",
                "focus:ring-2 focus:ring-blue-500/20",
              )}
            />
          </span>
        </div>

        <AutoResizeTextarea
          inputRef={answerRef}
          value={value}
          onChange={(val) => {
            const normalized = normalizeVarsToIdOnly(val);
            updateElement(element.id, { data: normalized, hint: normalized });
          }}
          readOnly={isReadOnly}
          placeholder="Оставьте пустым для ручной проверки…"
          className={cx(
            "w-full rounded-xl px-3 py-3 text-sm outline-none",
            "bg-zinc-50 border border-zinc-200 text-zinc-800",
            "dark:bg-[#141416] dark:border-zinc-700 dark:text-zinc-200",
            "focus:ring-2 focus:ring-blue-500/20",
          )}
        />

        {renderParamsPreview()}
      </div>
    </div>
  );
}
