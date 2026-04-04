import { useState } from "react";
import * as DropdownMenu from "@radix-ui/react-dropdown-menu";

import type { TemplateCourseSummary } from "@/model/template";

type RowMenuProps = {
  template: TemplateCourseSummary;
  onPublish: () => void;
  onDelete: () => void;
  isPublishing: boolean;
  isDeleting: boolean;
};

export const RowMenu = ({
  template,
  onPublish,
  onDelete,
  isPublishing,
  isDeleting,
}: RowMenuProps) => {
  const [open, setOpen] = useState(false);

  const canPublish = !!template._links.publish;
  const canDelete = !!template._links.delete;

  if (!canPublish && !canDelete) return null;

  const close = () => setOpen(false);

  return (
    <DropdownMenu.Root open={open} onOpenChange={setOpen}>
      <DropdownMenu.Trigger asChild>
        <button
          type="button"
          aria-label="Действия"
          className="inline-flex h-10 w-10 items-center justify-center rounded-xl border border-zinc-200 bg-white/60 transition-all active:scale-[0.98] dark:border-zinc-700 dark:bg-[#1E1E22]/60 dark:hover:bg-zinc-800 hover:bg-zinc-50"
        >
          <svg
            aria-hidden="true"
            className="h-5 w-5 text-zinc-600 dark:text-zinc-300"
            viewBox="0 0 24 24"
            fill="currentColor"
          >
            <path d="M12 7.5a1.5 1.5 0 1 1 0-3 1.5 1.5 0 0 1 0 3Zm0 6a1.5 1.5 0 1 1 0-3 1.5 1.5 0 0 1 0 3Zm0 6a1.5 1.5 0 1 1 0-3 1.5 1.5 0 0 1 0 3Z" />
          </svg>
        </button>
      </DropdownMenu.Trigger>

      <DropdownMenu.Portal>
        <DropdownMenu.Content
          align="end"
          sideOffset={8}
          className="z-[60] min-w-[220px] rounded-xl border border-zinc-200 bg-white p-1 shadow-xl dark:border-zinc-700 dark:bg-[#1E1E22]"
        >
          {canPublish && (
            <DropdownMenu.Item
              disabled={isPublishing}
              onSelect={() => {
                close();
                onPublish();
              }}
              className="cursor-pointer select-none rounded-lg px-3 py-2 text-sm text-zinc-800 outline-none data-[disabled]:cursor-not-allowed data-[disabled]:opacity-50 dark:text-zinc-200 dark:hover:bg-zinc-800 hover:bg-zinc-100"
            >
              <span className="inline-flex items-center gap-2">
                {isPublishing ? (
                  <span className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
                ) : (
                  <svg
                    aria-hidden="true"
                    className="h-4 w-4 text-zinc-700 dark:text-zinc-200"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M5 13l4 4L19 7"
                    />
                  </svg>
                )}
                Опубликовать
              </span>
            </DropdownMenu.Item>
          )}

          {canDelete && (
            <DropdownMenu.Item
              disabled={isDeleting}
              onSelect={() => {
                close();
                onDelete();
              }}
              className="cursor-pointer select-none rounded-lg px-3 py-2 text-sm text-red-700 outline-none data-[disabled]:cursor-not-allowed data-[disabled]:opacity-50 dark:text-red-400 dark:hover:bg-red-900/10 hover:bg-red-50"
            >
              <span className="inline-flex items-center gap-2">
                {isDeleting ? (
                  <span className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
                ) : (
                  <svg
                    aria-hidden="true"
                    className="h-4 w-4"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                    />
                  </svg>
                )}
                Удалить
              </span>
            </DropdownMenu.Item>
          )}
        </DropdownMenu.Content>
      </DropdownMenu.Portal>
    </DropdownMenu.Root>
  );
};
