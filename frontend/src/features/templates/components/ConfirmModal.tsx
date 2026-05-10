import type { ReactNode } from "react";
import * as Dialog from "@radix-ui/react-dialog";

type ConfirmModalProps = {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  isPending?: boolean;
  title: string;
  message: ReactNode;
  confirmText?: string;
  danger?: boolean;
};

export const ConfirmModal = ({
  isOpen,
  onClose,
  onConfirm,
  isPending,
  title,
  message,
  confirmText = "Подтвердить",
  danger = false,
}: ConfirmModalProps) => {
  return (
    <Dialog.Root
      open={isOpen}
      onOpenChange={(open) => {
        if (!open && !isPending) onClose();
      }}
    >
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-black/50 backdrop-blur-[2px] data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0" />

        <Dialog.Content
          className="fixed inset-0 z-50 flex items-center justify-center p-4 data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95 duration-200"
          onEscapeKeyDown={(e) => {
            if (isPending) e.preventDefault();
          }}
          onPointerDownOutside={(e) => {
            if (isPending) e.preventDefault();
          }}
        >
          <div className="relative w-full max-w-lg rounded-2xl border border-zinc-200 bg-white p-8 shadow-2xl dark:border-zinc-700 dark:bg-[#1E1E22]">
            <div
              className={[
                "mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full",
                danger
                  ? "bg-red-100 dark:bg-red-900/20"
                  : "bg-zinc-100 dark:bg-zinc-800",
              ].join(" ")}
            >
              {danger ? (
                <svg
                  aria-hidden="true"
                  className="h-8 w-8 text-red-600 dark:text-red-400"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                  />
                </svg>
              ) : (
                <svg
                  aria-hidden="true"
                  className="h-8 w-8 text-zinc-700 dark:text-zinc-200"
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
            </div>

            <Dialog.Title className="mb-3 text-center text-2xl font-bold text-zinc-900 dark:text-zinc-50">
              {title}
            </Dialog.Title>

            <Dialog.Description className="mb-6 text-center text-lg leading-relaxed text-zinc-600 dark:text-zinc-400">
              {message}
            </Dialog.Description>

            {danger && (
              <div className="mb-6 rounded-xl border border-red-200 bg-red-50 p-4 dark:border-red-900/30 dark:bg-red-950/20">
                <p className="text-sm text-red-800 dark:text-red-300">
                  Это действие нельзя отменить
                </p>
              </div>
            )}

            <div className="flex justify-center gap-4">
              <Dialog.Close asChild>
                <button
                  type="button"
                  disabled={isPending}
                  className="inline-flex min-w-[140px] items-center justify-center rounded-xl border border-zinc-300 px-6 py-3 text-base font-semibold text-zinc-700 transition-all active:scale-[0.98] disabled:opacity-50 dark:border-zinc-600 dark:text-zinc-300 dark:hover:bg-zinc-800 hover:bg-zinc-100"
                >
                  Отмена
                </button>
              </Dialog.Close>

              <button
                type="button"
                onClick={onConfirm}
                disabled={isPending}
                className={[
                  "inline-flex min-w-[140px] items-center justify-center gap-2 rounded-xl px-6 py-3 text-base font-semibold transition-all active:scale-[0.98] disabled:opacity-50",
                  danger
                    ? "bg-red-700 text-white hover:bg-red-600 dark:bg-red-800 dark:hover:bg-red-700"
                    : "bg-zinc-900 text-white hover:bg-zinc-800 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-zinc-200",
                ].join(" ")}
              >
                {isPending ? (
                  <>
                    <span className="h-5 w-5 animate-spin rounded-full border-2 border-current border-t-transparent" />
                    Выполняю...
                  </>
                ) : (
                  confirmText
                )}
              </button>
            </div>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
};
