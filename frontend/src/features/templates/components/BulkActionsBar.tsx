import type { RefObject } from "react";
import { pluralizeDrafts } from "../../../features/templates/pluralize";
import { cx } from "../../../features/template/utils/styles";

type BulkActionsBarProps = {
  selectedCount: number;
  selectedDraftCount: number;
  allSelected: boolean;
  selectAllCheckboxRef: RefObject<HTMLInputElement | null>;
  onToggleAll: () => void;
  onClearSelection: () => void;
  hasPublishMany: boolean;
  hasDeleteMany: boolean;
  canBulkPublish: boolean;
  canBulkDelete: boolean;
  onBulkPublish: () => void;
  onBulkDelete: () => void;
};

export const BulkActionsBar = ({
  selectedCount,
  selectedDraftCount,
  allSelected,
  selectAllCheckboxRef,
  onToggleAll,
  onClearSelection,
  hasPublishMany,
  hasDeleteMany,
  canBulkPublish,
  canBulkDelete,
  onBulkPublish,
  onBulkDelete,
}: BulkActionsBarProps) => {
  return (
    <div className="fixed bottom-0 left-0 right-0 z-20 border-t border-zinc-200 bg-white/92 p-4 shadow-xl backdrop-blur-md dark:border-zinc-800 dark:bg-[#1E1E22]/92">
      <div className="mx-auto flex max-w-5xl flex-col justify-between gap-4 sm:flex-row sm:items-center">
        <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              ref={selectAllCheckboxRef}
              type="checkbox"
              checked={allSelected}
              onChange={onToggleAll}
              className="h-5 w-5 accent-slate-700"
              aria-label="Выбрать все"
            />
            <span className="text-base font-semibold text-zinc-900 dark:text-zinc-50">
              Выбрано: {selectedCount}
            </span>
          </label>

          <button
            onClick={onClearSelection}
            className="text-sm text-zinc-500 underline underline-offset-4 hover:text-zinc-700 dark:hover:text-zinc-300"
          >
            Очистить
          </button>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          {hasPublishMany && (
            <button
              onClick={onBulkPublish}
              disabled={!canBulkPublish}
              title={
                !canBulkPublish ? "Выберите хотя бы один черновик" : undefined
              }
              className={cx(
                "inline-flex items-center justify-center rounded-xl px-4 py-2.5 text-sm font-semibold transition-all active:scale-[0.98] disabled:cursor-not-allowed",
                canBulkPublish
                  ? "bg-zinc-900 text-white hover:bg-zinc-800 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-zinc-200"
                  : "bg-zinc-300 text-zinc-600 dark:bg-zinc-700 dark:text-zinc-400",
              )}
            >
              Опубликовать{" "}
              {selectedDraftCount + " " + pluralizeDrafts(selectedDraftCount)}
            </button>
          )}

          {hasDeleteMany && (
            <button
              onClick={onBulkDelete}
              disabled={!canBulkDelete}
              className={cx(
                "inline-flex items-center justify-center rounded-xl border px-4 py-2.5 text-sm font-semibold transition-all active:scale-[0.98] disabled:cursor-not-allowed",
                canBulkDelete
                  ? "border-transparent bg-red-600 text-white hover:bg-red-700 dark:bg-red-500 dark:hover:bg-red-600"
                  : "border-red-200 bg-red-100 text-red-700 opacity-70 dark:border-red-900/30 dark:bg-red-900/20 dark:text-red-300/70",
              )}
            >
              Удалить
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
