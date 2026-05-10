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
      <div className="space-y-1">
        {referencedParams.map((p) => (
          <div key={p.id} className="flex items-start gap-2 text-sm">
            <code className="text-blue-600 dark:text-blue-400 shrink-0 text-xs font-mono break-all leading-relaxed">
              {p.id}
            </code>
            <span className="text-zinc-700 dark:text-zinc-300">{p.text}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
