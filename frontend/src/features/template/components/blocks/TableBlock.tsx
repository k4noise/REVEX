import { useMemo, memo, useRef, useState, useEffect } from "react";
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
  const walk = (node: TemplateElementResponse): boolean => {
    if (node.type === "answer") return true;
    return node.children?.some(walk) ?? false;
  };
  return cell.children?.some(walk) ?? false;
}

function computeCellPositions(rows: TemplateElementResponse[]) {
  const positions = new Map<string, number>();
  const occupiedCells: Map<number, Map<number, number>> = new Map();

  rows.forEach((row, rowIndex) => {
    if (row.type !== "row" || !row.children) return;

    let currentColumn = 0;
    const occupiedInThisRow = occupiedCells.get(rowIndex) || new Map();

    row.children.forEach((cell) => {
      if (cell.type !== "cell") return;

      while (occupiedInThisRow.has(currentColumn)) {
        currentColumn++;
      }

      positions.set(cell.id, currentColumn);

      const colspan =
        typeof cell.colspan === "number" && cell.colspan > 1 ? cell.colspan : 1;
      const rowspan =
        typeof cell.rowspan === "number" && cell.rowspan > 1 ? cell.rowspan : 1;

      for (let r = 0; r < rowspan; r++) {
        const targetRow = rowIndex + r;
        if (!occupiedCells.has(targetRow)) {
          occupiedCells.set(targetRow, new Map());
        }
        const rowMap = occupiedCells.get(targetRow)!;

        for (let c = 0; c < colspan; c++) {
          rowMap.set(currentColumn + c, 1);
        }
      }

      currentColumn += colspan;
    });
  });

  return positions;
}

function DoubleScrollbar({
  children,
  rowCount,
}: {
  children: React.ReactNode;
  rowCount: number;
}) {
  const topScrollRef = useRef<HTMLDivElement>(null);
  const bottomScrollRef = useRef<HTMLDivElement>(null);
  const contentRef = useRef<HTMLDivElement>(null);
  const [showScrollbar, setShowScrollbar] = useState(false);
  const [isExpanded, setIsExpanded] = useState(false);
  const [scrollState, setScrollState] = useState({
    canScrollLeft: false,
    canScrollRight: false,
  });

  const shouldLimitHeight = rowCount > 15;
  const maxHeight = isExpanded ? "none" : shouldLimitHeight ? "600px" : "none";

  useEffect(() => {
    const content = contentRef.current;
    if (!content) return;

    const checkScroll = () => {
      const hasOverflow = content.scrollWidth > content.clientWidth;
      setShowScrollbar(hasOverflow);

      setScrollState({
        canScrollLeft: content.scrollLeft > 0,
        canScrollRight:
          content.scrollLeft < content.scrollWidth - content.clientWidth - 1,
      });
    };

    checkScroll();
    const resizeObserver = new ResizeObserver(checkScroll);
    resizeObserver.observe(content);

    return () => resizeObserver.disconnect();
  }, []);

  const syncScroll =
    (source: "top" | "bottom" | "content") =>
    (e: React.UIEvent<HTMLDivElement>) => {
      const scrollLeft = e.currentTarget.scrollLeft;

      if (source !== "top" && topScrollRef.current) {
        topScrollRef.current.scrollLeft = scrollLeft;
      }
      if (source !== "bottom" && bottomScrollRef.current) {
        bottomScrollRef.current.scrollLeft = scrollLeft;
      }
      if (source !== "content" && contentRef.current) {
        contentRef.current.scrollLeft = scrollLeft;
      }

      if (contentRef.current) {
        setScrollState({
          canScrollLeft: contentRef.current.scrollLeft > 0,
          canScrollRight:
            contentRef.current.scrollLeft <
            contentRef.current.scrollWidth - contentRef.current.clientWidth - 1,
        });
      }
    };

  return (
    <div className="relative">
      {showScrollbar && (
        <div className="flex items-center gap-2 mb-2">
          <div
            ref={topScrollRef}
            onScroll={syncScroll("top")}
            className="overflow-x-auto overflow-y-hidden flex-1"
            style={{ height: "12px" }}
          >
            <div
              style={{
                width: contentRef.current?.scrollWidth || "100%",
                height: "1px",
              }}
            />
          </div>

          {shouldLimitHeight && (
            <button
              type="button"
              onClick={() => setIsExpanded(!isExpanded)}
              className="shrink-0 text-xs text-zinc-500 hover:text-zinc-700 dark:text-zinc-400 dark:hover:text-zinc-200 transition-colors"
              title={isExpanded ? "Свернуть таблицу" : "Развернуть таблицу"}
            >
              {isExpanded ? (
                <svg
                  className="w-4 h-4"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M6 18L18 6M6 6l12 12"
                  />
                </svg>
              ) : (
                <svg
                  className="w-4 h-4"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4"
                  />
                </svg>
              )}
            </button>
          )}
        </div>
      )}

      <div className="relative">
        {scrollState.canScrollLeft && (
          <div className="absolute left-0 top-0 bottom-0 w-8 bg-gradient-to-r from-white/80 to-transparent dark:from-zinc-900/80 pointer-events-none z-10" />
        )}

        {scrollState.canScrollRight && (
          <div className="absolute right-0 top-0 bottom-0 w-8 bg-gradient-to-l from-white/80 to-transparent dark:from-zinc-900/80 pointer-events-none z-10" />
        )}

        <div
          ref={contentRef}
          onScroll={syncScroll("content")}
          className="overflow-auto rounded-xl border border-zinc-200 dark:border-zinc-800"
          style={{ maxHeight }}
        >
          {children}
        </div>
      </div>

      {shouldLimitHeight && !isExpanded && (
        <div className="mt-2 text-center">
          <button
            type="button"
            onClick={() => setIsExpanded(true)}
            className="text-xs text-zinc-500 hover:text-blue-600 dark:text-zinc-400 dark:hover:text-blue-400 transition-colors inline-flex items-center gap-1"
          >
            <span>Показать все ({rowCount} строк)</span>
            <svg
              className="w-3 h-3"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M19 9l-7 7-7-7"
              />
            </svg>
          </button>
        </div>
      )}
    </div>
  );
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

  const cellPositions = useMemo(
    () => computeCellPositions(element.children ?? []),
    [element.children],
  );

  const hasGradableAnswers = isGradingMode && answerIds.length > 0;
  const rowCount = element.children?.length ?? 0;

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

      <DoubleScrollbar rowCount={rowCount}>
        <table className="w-full text-left text-sm text-zinc-700 dark:text-zinc-300">
          <tbody>
            {element.children.map((row, rowIndex) => (
              <TableRow
                key={row.id}
                {...restProps}
                element={row}
                rowIndex={rowIndex}
                cellPositions={cellPositions}
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
      </DoubleScrollbar>
    </div>
  );
});

interface TableRowProps extends CommonBlockProps {
  rowIndex: number;
  cellPositions: Map<string, number>;
}

const TableRow = memo(function TableRow(props: TableRowProps) {
  const { element, rowIndex, cellPositions, ...restProps } = props;
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
      {element.children?.map((cell) => (
        <TableCell
          key={cell.id}
          {...restProps}
          element={cell}
          isFirstColumn={cellPositions.get(cell.id) === 0}
          isFirstRow={rowIndex === 0}
        />
      ))}
    </tr>
  );
});

interface TableCellProps extends CommonBlockProps {
  isFirstColumn?: boolean;
  isFirstRow?: boolean;
}

const TableCell = memo(function TableCell(props: TableCellProps) {
  const {
    element,
    isFirstColumn,
    isFirstRow,
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
    canEdit &&
    !hasAnswer &&
    !isFirstColumn &&
    !isFirstRow &&
    !!convertCellToAnswer;
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
