import { useState, memo } from "react";
import { Link, useNavigate } from "@tanstack/react-router";
import { useMutation } from "@tanstack/react-query";

import type { TemplateCourseSummary } from "../../../model/template";
import type {
  MinimalReport,
  ReportCreationResponse,
} from "../../../model/report";
import { templateApi } from "../../../api/template";
import { RowMenu } from "./RowMenu";
import { cx } from "../../../features/template/utils/styles";

type TemplateItemProps = {
  template: TemplateCourseSummary;
  selected: boolean;
  onToggle: () => void;
  onDelete: () => void;
  onPublish: () => void;
  isDeleting: boolean;
  isPublishing: boolean;
};

function ReportStatusText({ report }: { report: MinimalReport }) {
  const status = report.status?.toLowerCase();

  if (status === "graded") {
    return (
      <span className="flex items-center gap-2">
        <span className="text-sm font-semibold text-emerald-600 dark:text-emerald-400">
          Оценено{report.score != null ? `: ${report.score} б.` : ""}
        </span>
        {report.authorName && (
          <span className="text-xs text-zinc-400 dark:text-zinc-500">
            ({report.authorName})
          </span>
        )}
      </span>
    );
  }

  if (status === "submitted") {
    return (
      <span className="text-sm font-semibold text-amber-600 dark:text-amber-400">
        На проверке
      </span>
    );
  }

  return (
    <span className="text-sm font-semibold text-zinc-500 dark:text-zinc-400">
      В процессе
    </span>
  );
}

const formatReportDate = (iso: string) =>
  new Date(iso).toLocaleString("ru-RU", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });

export const TemplateItem = memo(function TemplateItem({
  template,
  selected,
  onToggle,
  onDelete,
  onPublish,
  isDeleting,
  isPublishing,
}: TemplateItemProps) {
  const [expanded, setExpanded] = useState(false);
  const navigate = useNavigate();

  const canEdit = !!template._links?.get_template;
  const canGradeReports = !!template._links?.get_reports;
  const createReportHref = template._links?.create_report?.href;
  const canCreateReport = !!createReportHref;

  const reports = [...(template._embedded?.reports ?? [])].sort(
    (a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime(),
  );
  const latestReport = reports[0];
  const hasMultipleReports = reports.length > 1;

  const createReportMutation = useMutation({
    mutationFn: () => {
      if (!createReportHref) {
        throw new Error("Нет прав для создания отчета");
      }
      return templateApi.createReport(createReportHref);
    },
    onSuccess: (data: ReportCreationResponse) => {
      navigate({ to: "/report/$reportId", params: { reportId: data.id } });
    },
  });

  // --- Teacher view ---
  if (canEdit) {
    return (
      <li
        className={cx(
          "group flex items-center gap-4 rounded-2xl border px-5 py-4 transition-all duration-150 dark:bg-[#1E1E22]",
          selected
            ? "border-blue-400 bg-blue-50 shadow-sm shadow-blue-100 dark:border-blue-500 dark:bg-blue-950/40 dark:shadow-blue-900/20"
            : "border-zinc-200 bg-white hover:shadow-sm dark:border-zinc-800",
        )}
      >
        <input
          type="checkbox"
          checked={selected}
          onChange={onToggle}
          aria-label={`Выбрать шаблон ${template.name}`}
          className="h-5 w-5 shrink-0 accent-slate-700"
        />
        <Link
          to="/template/$templateId"
          params={{ templateId: template.id }}
          className="flex min-w-0 flex-1 items-center gap-4 cursor-pointer"
        >
          <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl border border-slate-200 bg-gradient-to-br from-slate-100 to-slate-50 dark:border-slate-700 dark:from-slate-800 dark:to-slate-900">
            <svg
              aria-hidden="true"
              className="h-6 w-6 text-slate-500 dark:text-slate-400"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
              />
            </svg>
          </div>

          <div className="flex min-w-0 flex-1 items-center justify-between gap-4">
            <div className="flex min-w-0 items-center gap-3">
              <h3 className="truncate text-lg font-semibold leading-tight text-zinc-900 dark:text-zinc-50">
                {template.name}
              </h3>
              <span
                className={cx(
                  "inline-flex shrink-0 items-center rounded-full px-2.5 py-1 text-xs font-medium",
                  template.isDraft
                    ? "bg-amber-100 text-amber-800 dark:bg-amber-900/20 dark:text-amber-300"
                    : "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/20 dark:text-emerald-300",
                )}
              >
                {template.isDraft ? "Черновик" : "Публичный"}
              </span>
            </div>

            <svg
              className="h-5 w-5 shrink-0 text-zinc-400 dark:text-zinc-500"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M9 5l7 7-7 7"
              />
            </svg>
          </div>
        </Link>

        {canGradeReports && !template.isDraft && (
          <Link
            to="/template/$templateId/reports"
            params={{ templateId: template.id }}
            onClick={(e: React.MouseEvent) => e.stopPropagation()}
            className="shrink-0 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-1.5 text-sm font-semibold text-emerald-700 transition-colors hover:bg-emerald-100 dark:border-emerald-900/50 dark:bg-emerald-900/20 dark:text-emerald-300 dark:hover:bg-emerald-900/40"
          >
            Отчеты
          </Link>
        )}

        <div className="shrink-0" onClick={(e) => e.stopPropagation()}>
          <RowMenu
            template={template}
            onPublish={onPublish}
            onDelete={onDelete}
            isPublishing={isPublishing}
            isDeleting={isDeleting}
          />
        </div>
      </li>
    );
  }

  // --- Student view ---
  return (
    <li
      className={cx(
        "flex flex-col rounded-2xl border transition-all duration-150",
        "border-zinc-200 bg-white dark:border-zinc-800 dark:bg-[#1E1E22]",
        "hover:shadow-sm",
      )}
    >
      <div className="flex items-center gap-4 px-5 py-4">
        <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl border border-slate-200 bg-gradient-to-br from-slate-100 to-slate-50 dark:border-slate-700 dark:from-slate-800 dark:to-slate-900">
          <svg
            aria-hidden="true"
            className="h-6 w-6 text-slate-500 dark:text-slate-400"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
            />
          </svg>
        </div>

        <div className="flex min-w-0 flex-1 flex-col gap-1.5">
          <h3 className="truncate text-lg font-semibold leading-tight text-zinc-900 dark:text-zinc-50">
            {template.name}
          </h3>
          {latestReport && (
            <div className="flex items-center gap-3">
              <span className="text-sm text-zinc-400 dark:text-zinc-500">
                Отчет от {formatReportDate(latestReport.createdAt)}
              </span>
              <ReportStatusText report={latestReport} />
            </div>
          )}
        </div>

        <div className="flex items-center gap-3 shrink-0">
          {latestReport && (
            <Link
              to="/report/$reportId"
              params={{ reportId: latestReport.reportId }}
              className={cx(
                "rounded-xl border px-4 py-2 text-sm font-medium transition-colors",
                "border-zinc-300 bg-white text-zinc-900 hover:bg-zinc-50",
                "dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-100 dark:hover:bg-zinc-700",
              )}
            >
              Открыть
            </Link>
          )}

          {hasMultipleReports && (
            <button
              type="button"
              onClick={() => setExpanded((prev) => !prev)}
              className={cx(
                "rounded-xl border px-4 py-2 text-sm font-medium transition-colors",
                expanded
                  ? "border-zinc-300 bg-zinc-100 text-zinc-700 dark:border-zinc-600 dark:bg-zinc-700 dark:text-zinc-200"
                  : "border-zinc-200 text-zinc-600 hover:bg-zinc-50 dark:border-zinc-700 dark:text-zinc-400 dark:hover:bg-zinc-800",
              )}
            >
              {expanded ? "Скрыть" : `Все (${reports.length})`}
            </button>
          )}

          {canCreateReport && (
            <button
              onClick={() => createReportMutation.mutate()}
              disabled={createReportMutation.isPending}
              className={cx(
                "rounded-xl border px-4 py-2 text-sm font-medium transition-colors",
                "border-zinc-900 bg-zinc-900 text-white hover:bg-zinc-800",
                "dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-zinc-200",
                "disabled:opacity-50",
              )}
            >
              {createReportMutation.isPending ? "Создание..." : "Новый отчет"}
            </button>
          )}
        </div>
      </div>

      {expanded && hasMultipleReports && (
        <div className="border-t border-zinc-100 bg-zinc-50/50 px-5 py-3 rounded-b-2xl dark:border-zinc-800/80 dark:bg-zinc-900/20">
          <ul className="space-y-2">
            {reports.map((report) => (
              <li
                key={report.reportId}
                className="flex items-center justify-between rounded-xl border border-zinc-200 bg-white p-3 dark:border-zinc-700/50 dark:bg-[#141416]"
              >
                <div className="flex items-center gap-3 min-w-0">
                  <span className="text-sm text-zinc-600 dark:text-zinc-300">
                    {formatReportDate(report.createdAt)}
                  </span>
                  <ReportStatusText report={report} />
                </div>
                <Link
                  to="/report/$reportId"
                  params={{ reportId: report.reportId }}
                  className="shrink-0 text-sm font-semibold text-blue-600 hover:text-blue-700 hover:underline dark:text-blue-400"
                >
                  Открыть
                </Link>
              </li>
            ))}
          </ul>
        </div>
      )}
    </li>
  );
});
