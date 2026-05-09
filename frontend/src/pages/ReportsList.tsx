import { useMemo, useState } from "react";
import { Helmet } from "react-helmet-async";
import { Link, useNavigate } from "@tanstack/react-router";
import {
  createColumnHelper,
  flexRender,
  getCoreRowModel,
  getSortedRowModel,
  useReactTable,
  type SortingState,
  type ColumnDef,
} from "@tanstack/react-table";
import type { MinimalReport, AllReportsResponse } from "../model/report";
import { cx } from "../features/template/utils/styles";
import { startGradingQueue } from "../features/grading/useGradingQueue";

const columnHelper = createColumnHelper<MinimalReport>();

const statusLabel = (s: string) => {
  if (s === "graded") return "Оценено";
  if (s === "submitted") return "На проверке";
  if (s === "saved") return "В работе";
  if (s === "created") return "Создано";
  return "—";
};

const statusColor = (s: string) => {
  if (s === "graded") return "text-emerald-600 dark:text-emerald-400";
  if (s === "submitted") return "text-amber-600 dark:text-amber-400";
  return "text-zinc-500 dark:text-zinc-400";
};

const formatDate = (iso: string) =>
  new Date(iso).toLocaleString("ru-RU", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });

function SortIcon({ dir }: { dir: false | "asc" | "desc" }) {
  return (
    <span className="ml-1 text-xs text-zinc-400 dark:text-zinc-500">
      {dir === "asc" ? "▲" : dir === "desc" ? "▼" : ""}
    </span>
  );
}

interface ReportsTableProps {
  reports: MinimalReport[];
  maxScore: number;
  showAuthor: boolean;
  emptyText: string;
}

function ReportsTable({
  reports,
  maxScore,
  showAuthor,
  emptyText,
}: ReportsTableProps) {
  const navigate = useNavigate();
  const [sorting, setSorting] = useState<SortingState>([
    { id: "createdAt", desc: true },
  ]);

  const columns = useMemo(() => {
    const cols: ColumnDef<MinimalReport, any>[] = [];

    if (showAuthor) {
      cols.push(
        columnHelper.accessor("authorName", {
          header: "Студент",
          cell: (info) => (
            <span className="text-base font-semibold text-zinc-900 dark:text-zinc-50">
              {info.getValue() || "—"}
            </span>
          ),
        }),
      );
    }

    cols.push(
      columnHelper.accessor("createdAt", {
        header: "Дата",
        cell: (info) => (
          <span className="text-sm text-zinc-600 dark:text-zinc-300">
            {formatDate(info.getValue())}
          </span>
        ),
      }),
      columnHelper.accessor("status", {
        header: "Статус",
        cell: (info) => (
          <span
            className={cx(
              "text-sm font-semibold",
              statusColor(info.getValue()),
            )}
          >
            {statusLabel(info.getValue())}
          </span>
        ),
      }),
      columnHelper.accessor("score", {
        header: "Балл",
        cell: (info) => {
          const value = info.getValue();
          return (
            <span className="font-mono text-base font-semibold text-zinc-900 dark:text-zinc-50">
              {value ?? "—"}
              <span className="ml-1 font-mono text-sm font-normal text-zinc-400 dark:text-zinc-500">
                / {maxScore}
              </span>
            </span>
          );
        },
      }),
      columnHelper.display({
        id: "actions",
        header: "",
        cell: (info) => {
          const reportId = info.row.original.reportId;
          if (!reportId) return null;
          return (
            <div className="text-right">
              <Link
                to="/report/$reportId"
                params={{ reportId }}
                onClick={(e) => e.stopPropagation()}
                className={cx(
                  "inline-flex items-center justify-center rounded-xl border px-4 py-2 text-sm font-medium transition-colors",
                  "border-zinc-300 bg-white text-zinc-900 hover:bg-zinc-50",
                  "dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-100 dark:hover:bg-zinc-700",
                )}
              >
                Открыть
              </Link>
            </div>
          );
        },
      }),
    );

    return cols;
  }, [maxScore, showAuthor]);

  const table = useReactTable({
    data: reports,
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  });

  if (reports.length === 0) {
    return (
      <div className="py-12 text-center text-zinc-400 dark:text-zinc-500">
        {emptyText}
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-left">
        <thead>
          {table.getHeaderGroups().map((headerGroup) => (
            <tr
              key={headerGroup.id}
              className="border-b border-zinc-200 bg-zinc-50/60 dark:border-zinc-800 dark:bg-zinc-900/40"
            >
              {headerGroup.headers.map((header) => {
                const canSort = header.column.getCanSort();
                const sorted = header.column.getIsSorted();

                return (
                  <th
                    key={header.id}
                    className={cx(
                      "px-5 py-3 text-xs font-semibold text-zinc-500 dark:text-zinc-400",
                      canSort
                        ? "cursor-pointer select-none hover:text-zinc-900 dark:hover:text-zinc-100"
                        : "cursor-default",
                    )}
                    onClick={header.column.getToggleSortingHandler()}
                    aria-sort={
                      sorted === "asc"
                        ? "ascending"
                        : sorted === "desc"
                          ? "descending"
                          : "none"
                    }
                  >
                    <span className="inline-flex items-center">
                      {flexRender(
                        header.column.columnDef.header,
                        header.getContext(),
                      )}
                      {canSort && <SortIcon dir={sorted} />}
                    </span>
                  </th>
                );
              })}
            </tr>
          ))}
        </thead>

        <tbody className="divide-y divide-zinc-100 dark:divide-zinc-800">
          {table.getRowModel().rows.map((row) => {
            const reportId = row.original.reportId;
            if (!reportId) return null;
            return (
              <tr
                key={row.id}
                onClick={() =>
                  navigate({
                    to: "/report/$reportId",
                    params: { reportId },
                  })
                }
                className="cursor-pointer transition-colors hover:bg-zinc-50/80 dark:hover:bg-zinc-900/40"
              >
                {row.getVisibleCells().map((cell) => (
                  <td key={cell.id} className="px-5 py-4 align-middle">
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </td>
                ))}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

interface ReportsListPageProps {
  data: AllReportsResponse;
}

export function ReportsListPage({ data }: ReportsListPageProps) {
  const navigate = useNavigate();
  const { templateId } = data;

  const [searchQuery, setSearchQuery] = useState("");
  const [hideGraded, setHideGraded] = useState(false);

  const ownedReports = data.reports?.owned ?? [];
  const toGradeReports = data.reports?.toGrade ?? [];

  const hasOwned = ownedReports.length > 0;
  const hasToGrade = toGradeReports.length > 0;
  const isEmpty = !hasOwned && !hasToGrade;

  const filteredToGrade = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    return toGradeReports.filter((r) => {
      if (hideGraded && r.status === "graded") return false;
      if (q && !(r.authorName ?? "").toLowerCase().includes(q)) return false;
      return true;
    });
  }, [toGradeReports, searchQuery, hideGraded]);

  const toGradeStats = useMemo(() => {
    const total = toGradeReports.length;
    const graded = toGradeReports.filter((r) => r.status === "graded").length;
    const submitted = toGradeReports.filter(
      (r) => r.status === "submitted",
    ).length;
    return { total, graded, submitted };
  }, [toGradeReports]);

  const isFiltering = searchQuery.trim().length > 0 || hideGraded;

  const gradableReportIds = useMemo(() => {
    return toGradeReports
      .filter((r) => r.status === "submitted")
      .map((r) => r.reportId);
  }, [toGradeReports]);

  const canStartBatchGrading = gradableReportIds.length > 0;

  const handleStartBatchGrading = () => {
    if (!canStartBatchGrading) return;
    startGradingQueue(templateId, gradableReportIds);
    navigate({
      to: "/report/$reportId",
      params: { reportId: gradableReportIds[0] },
    });
  };
  const pageTitle = `Отчеты — ${data.templateName}`;
  return (
    <>
      <Helmet>
        <title>{pageTitle}</title>
      </Helmet>

      <div className="sticky top-0 z-[80] isolate border-b border-zinc-200/80 bg-white/80 backdrop-blur dark:border-zinc-800/80 dark:bg-[#0F0F12]/80">
        <div className="flex h-16 w-full items-center gap-4 px-6">
          <button
            type="button"
            onClick={() => navigate({ to: "/" })}
            className="text-sm opacity-70 hover:opacity-100"
          >
            ← Список
          </button>

          <div className="flex min-w-0 flex-1 items-center gap-3">
            <h1 className="truncate text-lg font-semibold text-zinc-900 dark:text-zinc-50">
              Отчеты
            </h1>
            <span className="truncate text-sm text-zinc-500 dark:text-zinc-400">
              {data.templateName}
            </span>
          </div>

          {hasToGrade && (
            <div className="flex items-center gap-3">
              <span className="text-sm text-zinc-500 dark:text-zinc-400">
                Всего:{" "}
                <span className="font-semibold text-zinc-900 dark:text-zinc-50">
                  {toGradeStats.total}
                </span>
              </span>
              <span className="text-sm text-amber-600 dark:text-amber-400">
                На проверке:{" "}
                <span className="font-semibold">{toGradeStats.submitted}</span>
              </span>
              <span className="text-sm text-emerald-600 dark:text-emerald-400">
                Оценено:{" "}
                <span className="font-semibold">{toGradeStats.graded}</span>
              </span>

              {canStartBatchGrading && (
                <button
                  type="button"
                  onClick={handleStartBatchGrading}
                  className={cx(
                    "rounded-xl border px-4 py-2 text-sm font-semibold transition-colors",
                    "border-emerald-600 bg-emerald-600 text-white hover:bg-emerald-700",
                  )}
                >
                  Начать проверку ({gradableReportIds.length})
                </button>
              )}
            </div>
          )}
        </div>
      </div>

      <div className="mx-auto mt-6 max-w-5xl px-4 pb-16 space-y-6">
        {isEmpty && (
          <div className="py-16 text-center text-zinc-400 dark:text-zinc-500">
            Отчетов пока нет.
          </div>
        )}

        {hasOwned && (
          <div className="space-y-3">
            <h2 className="text-xl font-semibold text-zinc-900 dark:text-zinc-50">
              Мои отчеты
            </h2>
            <div className="overflow-hidden rounded-2xl border border-zinc-200 bg-white shadow-sm dark:border-zinc-800 dark:bg-[#1E1E22]">
              <ReportsTable
                reports={ownedReports}
                maxScore={data.maxScore}
                showAuthor={false}
                emptyText="У вас пока нет отчетов."
              />
            </div>
          </div>
        )}

        {hasToGrade && (
          <div className="space-y-3">
            <h2 className="text-xl font-semibold text-zinc-900 dark:text-zinc-50">
              На проверку
            </h2>

            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div className="relative flex-1 sm:max-w-md">
                <svg
                  aria-hidden="true"
                  className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-400 dark:text-zinc-500"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M21 21l-4.35-4.35M11 19a8 8 0 100-16 8 8 0 000 16z"
                  />
                </svg>
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Поиск по ФИО студента..."
                  className="w-full rounded-xl border border-zinc-200 bg-white py-2.5 pl-10 pr-9 text-sm text-zinc-900 outline-none placeholder:text-zinc-400 focus:border-zinc-400 dark:border-zinc-800 dark:bg-[#1E1E22] dark:text-zinc-100 dark:placeholder:text-zinc-600 dark:focus:border-zinc-600"
                />
                {searchQuery && (
                  <button
                    type="button"
                    onClick={() => setSearchQuery("")}
                    aria-label="Очистить поиск"
                    className="absolute right-2 top-1/2 -translate-y-1/2 rounded-md p-1 text-zinc-400 hover:bg-zinc-100 hover:text-zinc-600 dark:hover:bg-zinc-800 dark:hover:text-zinc-300"
                  >
                    <svg
                      className="h-4 w-4"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        d="M6 18L18 6M6 6l12 12"
                      />
                    </svg>
                  </button>
                )}
              </div>

              <div className="flex items-center gap-3">
                <label
                  className={cx(
                    "inline-flex cursor-pointer select-none items-center gap-2 rounded-xl border px-3 py-2 text-sm font-medium transition-colors",
                    hideGraded
                      ? "border-zinc-900 bg-zinc-900 text-white dark:border-zinc-100 dark:bg-zinc-100 dark:text-zinc-900"
                      : "border-zinc-200 bg-white text-zinc-700 hover:bg-zinc-50 dark:border-zinc-800 dark:bg-[#1E1E22] dark:text-zinc-200 dark:hover:bg-zinc-800/40",
                  )}
                >
                  <input
                    type="checkbox"
                    className="sr-only"
                    checked={hideGraded}
                    onChange={(e) => setHideGraded(e.target.checked)}
                  />
                  <span
                    className={cx(
                      "flex h-4 w-4 items-center justify-center rounded border transition-colors",
                      hideGraded
                        ? "border-white bg-white text-zinc-900 dark:border-zinc-900 dark:bg-zinc-900 dark:text-zinc-100"
                        : "border-zinc-300 bg-white dark:border-zinc-600 dark:bg-transparent",
                    )}
                  >
                    {hideGraded && (
                      <svg
                        className="h-3 w-3"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="3"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          d="M5 13l4 4L19 7"
                        />
                      </svg>
                    )}
                  </span>
                  Скрыть проверенные
                </label>

                <span className="hidden whitespace-nowrap text-sm text-zinc-500 dark:text-zinc-400 sm:inline">
                  Показано: {filteredToGrade.length} из {toGradeStats.total}
                </span>
              </div>
            </div>

            <div className="overflow-hidden rounded-2xl border border-zinc-200 bg-white shadow-sm dark:border-zinc-800 dark:bg-[#1E1E22]">
              {filteredToGrade.length === 0 ? (
                <div className="py-12 text-center">
                  <p className="text-zinc-500 dark:text-zinc-400">
                    Ничего не найдено по заданным фильтрам.
                  </p>
                  {isFiltering && (
                    <button
                      type="button"
                      onClick={() => {
                        setSearchQuery("");
                        setHideGraded(false);
                      }}
                      className="mt-3 text-sm font-medium text-blue-600 hover:underline dark:text-blue-400"
                    >
                      Сбросить фильтры
                    </button>
                  )}
                </div>
              ) : (
                <ReportsTable
                  reports={filteredToGrade}
                  maxScore={data.maxScore}
                  showAuthor={true}
                  emptyText="Нет работ на проверку."
                />
              )}
            </div>
          </div>
        )}
      </div>
    </>
  );
}
