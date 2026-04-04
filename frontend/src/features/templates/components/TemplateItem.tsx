import { Link } from "@tanstack/react-router";

import type { TemplateCourseSummary } from "@/model/template";
import { RowMenu } from "./RowMenu";

type TemplateItemProps = {
  template: TemplateCourseSummary;
  selected: boolean;
  onToggle: () => void;
  onDelete: () => void;
  onPublish: () => void;
  isDeleting: boolean;
  isPublishing: boolean;
};

export const TemplateItem = ({
  template,
  selected,
  onToggle,
  onDelete,
  onPublish,
  isDeleting,
  isPublishing,
}: TemplateItemProps) => {
  return (
    <li>
      <div
        className={[
          "group relative flex items-center gap-4 rounded-2xl border px-5 py-4 transition-all duration-150 dark:bg-[#1E1E22]",
          selected
            ? "border-blue-400 bg-blue-50 shadow-sm shadow-blue-100 dark:border-blue-500 dark:bg-blue-950/40 dark:shadow-blue-900/20"
            : "border-zinc-200 bg-white hover:shadow-sm dark:border-zinc-800",
        ].join(" ")}
      >
        <div className="flex shrink-0 items-center gap-4">
          <input
            type="checkbox"
            checked={selected}
            onChange={onToggle}
            aria-label={`Выбрать шаблон ${template.name}`}
            className="h-5 w-5 accent-slate-700"
          />

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
        </div>

        <Link
          to="/template/$templateId"
          params={{ templateId: template.id }}
          className="min-w-0 flex-1 rounded-xl px-2 py-2 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-zinc-400/40 dark:focus-visible:ring-zinc-500/40 dark:hover:bg-zinc-800/60 hover:bg-zinc-50 -mx-2 -my-2"
          aria-label={`Открыть шаблон ${template.name}`}
        >
          <div className="flex min-w-0 items-center justify-between gap-4">
            <div className="min-w-0">
              <div className="flex min-w-0 items-center gap-3">
                <h3 className="truncate text-lg font-semibold leading-tight text-zinc-900 dark:text-zinc-50">
                  {template.name}
                </h3>

                <span
                  className={[
                    "inline-flex shrink-0 items-center rounded-full px-2.5 py-1 text-xs font-medium",
                    template.isDraft
                      ? "bg-amber-100 text-amber-800 dark:bg-amber-900/20 dark:text-amber-300"
                      : "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/20 dark:text-emerald-300",
                  ].join(" ")}
                >
                  {template.isDraft ? "Черновик" : "Публичный"}
                </span>
              </div>
            </div>

            <svg
              aria-hidden="true"
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

        <div className="shrink-0">
          <RowMenu
            template={template}
            onPublish={onPublish}
            onDelete={onDelete}
            isPublishing={isPublishing}
            isDeleting={isDeleting}
          />
        </div>
      </div>
    </li>
  );
};
