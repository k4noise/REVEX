import { useMemo, memo } from "react";
import type { CommonBlockProps } from "../../types";
import type { TemplateElementResponse } from "../../../../model/templateElement";
import { cx } from "../../utils/styles";
import { BlocksList } from "../BlocksList";

function collectAnswerIds(nodes: TemplateElementResponse[]): string[] {
  const ids: string[] = [];
  const walk = (list: TemplateElementResponse[]) => {
    for (const node of list) {
      if (node.type === "answer") ids.push(node.id);
      if (node.children?.length) walk(node.children);
    }
  };
  walk(nodes);
  return ids;
}

function hasAnswerChild(cell: TemplateElementResponse): boolean {
  return cell.children?.some((c) => c.type === "answer") ?? false;
}

export const TableBlock = memo(function TableBlock(props: CommonBlockProps) {
  const {
    element,
    isGradingMode,
    isReadOnly,
    isReportMode,
    answerGrading,
    onAnswerGradeChange,
    convertCellToAnswer,
    clearCell,
    ...restProps
  } = props;

  const answerIds = useMemo(
    () => collectAnswerIds(element.children ?? []),
    [element.children],
  );

  const hasGradableAnswers = isGradingMode && answerIds.length > 0;

  const handleAllCorrect = () => {
    for (const id of answerIds) onAnswerGradeChange?.(id, 1);
  };

  const handleAllIncorrect = () => {
    for (const id of answerIds) onAnswerGradeChange?.(id, 0);
  };

  if (!element.children?.length) {
    return (
      <div className="my-6 w-full overflow-x-auto rounded-xl bg-zinc-50 dark:bg-zinc-900/30">
        <table className="w-full text-left text-sm text-zinc-700 dark:text-zinc-300">
          <tbody>
            <tr>
              <td className="p-5 text-zinc-400">Таблица пуста.</td>
            </tr>
          </tbody>
        </table>
      </div>
    );
  }

  return (
    <div className="my-6 space-y-2">
      {hasGradableAnswers && (
        <div className="flex items-center gap-3">
          <span className="text-sm text-zinc-500 dark:text-zinc-400">
            Таблица ({answerIds.length} ответов):
          </span>
          <button
            type="button"
            onClick={handleAllCorrect}
            className={cx(
              "rounded-lg border px-3 py-1.5 text-sm font-medium transition-colors",
              "border-emerald-200 bg-emerald-50 text-emerald-700 hover:bg-emerald-100",
              "dark:border-emerald-900/50 dark:bg-emerald-900/20 dark:text-emerald-300 dark:hover:bg-emerald-900/40",
            )}
          >
            Все верно
          </button>
          <button
            type="button"
            onClick={handleAllIncorrect}
            className={cx(
              "rounded-lg border px-3 py-1.5 text-sm font-medium transition-colors",
              "border-red-200 bg-red-50 text-red-700 hover:bg-red-100",
              "dark:border-red-900/50 dark:bg-red-900/20 dark:text-red-300 dark:hover:bg-red-900/40",
            )}
          >
            Все неверно
          </button>
        </div>
      )}

      <div className="w-full overflow-auto rounded-xl border border-zinc-200 dark:border-zinc-800">
        <table className="w-full text-left text-sm text-zinc-700 dark:text-zinc-300">
          <tbody>
            {element.children.map((row) => (
              <TableRow
                key={row.id}
                {...restProps}
                element={row}
                isGradingMode={isGradingMode}
                isReadOnly={isReadOnly}
                isReportMode={isReportMode}
                answerGrading={answerGrading}
                onAnswerGradeChange={onAnswerGradeChange}
                convertCellToAnswer={convertCellToAnswer}
                clearCell={clearCell}
              />
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
});

const TableRow = memo(function TableRow(props: CommonBlockProps) {
  const { element, ...restProps } = props;
  if (element.type !== "row") return null;

  return (
    <tr
      className={cx(
        "bg-white even:bg-zinc-50/80",
        "dark:bg-[#1A1A1D] dark:even:bg-[#141416]",
        "hover:bg-zinc-100/60 dark:hover:bg-zinc-800/40 transition-colors",
        "group/row",
      )}
    >
      {element.children?.map((cell, cellIndex) => (
        <TableCell
          key={cell.id}
          {...restProps}
          element={cell}
          isFirstColumn={cellIndex === 0}
        />
      ))}
    </tr>
  );
});

interface TableCellProps extends CommonBlockProps {
  isFirstColumn?: boolean;
}

const TableCell = memo(function TableCell(props: TableCellProps) {
  const {
    element,
    isFirstColumn,
    convertCellToAnswer,
    clearCell,
    isReadOnly,
    isReportMode,
    isGradingMode,
    ...restProps
  } = props;

  if (element.type !== "cell") return null;

  const canEdit = !isReadOnly && !isReportMode && !isGradingMode;
  const hasAnswer = hasAnswerChild(element);
  const hasContent = (element.children?.length ?? 0) > 0;
  const showAddAnswer =
    canEdit && !hasAnswer && !isFirstColumn && !!convertCellToAnswer;
  const showClear = canEdit && hasAnswer && !!clearCell;

  const rowSpan =
    typeof element.rowspan === "number" && element.rowspan > 1
      ? element.rowspan
      : undefined;
  const colSpan =
    typeof element.colspan === "number" && element.colspan > 1
      ? element.colspan
      : undefined;

  return (
    <td
      rowSpan={rowSpan}
      colSpan={colSpan}
      className={cx(
        "px-4 py-3 align-middle leading-relaxed min-w-[140px]",
        "border-b border-zinc-100 dark:border-zinc-800/60",
        isFirstColumn && "sticky left-0 z-10 font-medium bg-inherit",
      )}
    >
      {hasContent && (
        <BlocksList
          {...restProps}
          isReadOnly={isReadOnly}
          isReportMode={isReportMode}
          isGradingMode={isGradingMode}
          convertCellToAnswer={convertCellToAnswer}
          clearCell={clearCell}
          elements={element.children ?? []}
          parentType="cell"
        />
      )}

      {showAddAnswer && (
        <button
          type="button"
          onClick={() => {
            convertCellToAnswer!(element.id);
          }}
          className={cx(
            "rounded border border-dashed px-2 py-0.5 text-xs font-medium transition-colors",
            hasContent && "mt-1",
            "border-zinc-300 text-zinc-400 hover:border-blue-400 hover:text-blue-600",
            "dark:border-zinc-700 dark:text-zinc-500 dark:hover:border-blue-600 dark:hover:text-blue-400",
          )}
        >
          + Ответ
        </button>
      )}

      {showClear && (
        <button
          type="button"
          onClick={() => clearCell!(element.id)}
          className="mt-1 rounded px-2 py-0.5 text-xs font-medium text-zinc-400 hover:text-red-600 dark:text-zinc-500 dark:hover:text-red-400 transition-colors"
        >
          Убрать ответ
        </button>
      )}
    </td>
  );
});
