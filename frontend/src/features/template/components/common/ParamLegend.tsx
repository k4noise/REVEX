import { useMemo } from "react";
import type { QuestionGroups } from "../../hooks/useQuestions";
import { extractVarIds } from "../../utils/questions";

interface ParamLegendProps {
  text: string;
  groups: QuestionGroups;
}

export function ParamLegend({ text, groups }: ParamLegendProps) {
  const referencedParams = useMemo(() => {
    const varIds = extractVarIds(text);

    if (varIds.length === 0) return [];

    const allMap = new Map(groups.all.map((q) => [q.id, q]));

    const result = [];
    for (const id of varIds) {
      const found = allMap.get(id);
      result.push({
        id,
        text: found?.text ?? "Неизвестный параметр",
      });
    }

    return result;
  }, [text, groups]);

  if (referencedParams.length === 0) return null;

  return (
    <div className="mt-2 rounded-lg bg-zinc-100/60 px-3 py-2 dark:bg-zinc-800/40">
      <div className="text-xs text-zinc-400 dark:text-zinc-500 mb-1">
        Параметры:
      </div>
      <div className="space-y-2">
        {referencedParams.map((p) => (
          <div
            key={p.id}
            className="flex flex-wrap items-start gap-x-2 gap-y-1 text-sm"
          >
            <code className="text-blue-600 dark:text-blue-400 text-[12px] font-mono break-all min-w-0 max-w-full leading-relaxed bg-blue-50/50 dark:bg-blue-900/20 px-1 rounded">
              {p.id}
            </code>
            <span className="text-zinc-700 dark:text-zinc-300 flex-1 min-w-[80px] break-words">
              {p.text}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
