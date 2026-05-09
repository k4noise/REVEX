import {
  useEffect,
  useRef,
  useState,
  type ChangeEvent,
  type FormEvent,
} from "react";
import * as Dialog from "@radix-ui/react-dialog";

type UploadModalProps = {
  isOpen: boolean;
  onClose: () => void;
  handleUpload: (file: File, separator: string) => void;
  isPending: boolean;
};

export const UploadModal = ({
  isOpen,
  onClose,
  handleUpload,
  isPending,
}: UploadModalProps) => {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [separator, setSeparator] = useState("_____");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen) {
      setSelectedFile(null);
      setError(null);
      setSeparator("_____");

      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  }, [isOpen]);

  const onFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0] ?? null;
    setError(null);

    if (!file) {
      setSelectedFile(null);
      return;
    }

    const name = file.name.toLowerCase();
    const isSupported = name.endsWith(".docx") || name.endsWith(".pdf");

    if (!isSupported) {
      setError("Можно загружать только файлы .docx и .pdf");
      setSelectedFile(null);
      if (e.currentTarget) {
        e.currentTarget.value = "";
      }
      return;
    }

    setSelectedFile(file);
  };

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (!selectedFile || isPending) return;

    const sep = separator.trim() || "_____";
    handleUpload(selectedFile, sep);
  };

  return (
    <Dialog.Root
      open={isOpen}
      onOpenChange={(open) => {
        if (!open && !isPending) onClose();
      }}
    >
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-black/50 backdrop-blur-[2px]" />

        <Dialog.Content
          className="fixed inset-0 z-50 flex items-center justify-center p-4"
          onOpenAutoFocus={(e) => {
            e.preventDefault();
            fileInputRef.current?.focus();
          }}
          onEscapeKeyDown={(e) => {
            if (isPending) e.preventDefault();
          }}
          onPointerDownOutside={(e) => {
            if (isPending) e.preventDefault();
          }}
        >
          <form
            onSubmit={onSubmit}
            className="relative w-full max-w-md rounded-2xl border border-zinc-200 bg-white p-8 shadow-2xl dark:border-zinc-700 dark:bg-[#1E1E22]"
          >
            <Dialog.Title className="mb-2 text-center text-2xl font-bold text-zinc-900 dark:text-zinc-50">
              Загрузить новый шаблон
            </Dialog.Title>

            <Dialog.Description className="mb-6 text-center text-sm text-zinc-500 dark:text-zinc-400">
              Поддерживаются только файлы формата .docx и .pdf
            </Dialog.Description>

            <label className="mb-2 block text-base font-medium text-zinc-700 dark:text-zinc-300">
              Выберите файл:
            </label>

            <input
              ref={fileInputRef}
              type="file"
              accept=".docx,.pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,application/pdf"
              onChange={onFileChange}
              disabled={isPending}
              className="mb-6 block w-full cursor-pointer text-lg text-zinc-700 transition-all file:mr-6 file:rounded-xl file:border-0 file:bg-zinc-100 file:px-6 file:py-3 file:text-base file:font-semibold file:text-zinc-900 hover:file:bg-zinc-200 disabled:cursor-not-allowed disabled:opacity-60 dark:text-zinc-300 dark:file:bg-zinc-800 dark:file:text-zinc-50 dark:hover:file:bg-zinc-700"
            />

            <div className="mb-6">
              <label className="mb-2 block text-base font-medium text-zinc-700 dark:text-zinc-300">
                Маркер поля ответа
              </label>

              <input
                type="text"
                value={separator}
                onChange={(e) => setSeparator(e.target.value)}
                placeholder="_____"
                disabled={isPending}
                className="w-full rounded-xl border border-zinc-200 bg-slate-50 px-4 py-3 text-lg text-zinc-900 placeholder-zinc-400 transition-all focus:outline-none focus:ring-2 focus:ring-zinc-500/20 disabled:opacity-60 dark:border-zinc-700 dark:bg-slate-800/50 dark:text-zinc-50 dark:focus:ring-zinc-400/20"
              />

              <p className="mt-2 text-sm text-zinc-500 dark:text-zinc-400">
                Пример: <span className="font-mono">_____</span>. Места в
                документе с таким маркером будут считаться полями для
                заполнения.
              </p>
            </div>

            {error && (
              <div className="mb-6 rounded-xl border border-red-200 bg-red-50 p-4 text-red-700 dark:border-red-900/30 dark:bg-red-900/10 dark:text-red-400">
                <strong>Ошибка:</strong> {error}
              </div>
            )}

            <div className="flex justify-end gap-4">
              <Dialog.Close asChild>
                <button
                  type="button"
                  disabled={isPending}
                  className="rounded-xl border border-zinc-300 px-6 py-3 text-base font-semibold text-zinc-700 transition-all active:scale-[0.98] disabled:opacity-50 dark:border-zinc-600 dark:text-zinc-300 dark:hover:bg-zinc-800 hover:bg-zinc-100"
                >
                  Отмена
                </button>
              </Dialog.Close>

              <button
                type="submit"
                disabled={!selectedFile || isPending}
                className="inline-flex items-center justify-center gap-3 rounded-xl bg-zinc-900 px-6 py-3 text-base font-semibold text-white transition-all active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-50 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-zinc-200 hover:bg-zinc-800"
              >
                {isPending ? (
                  <>
                    <span className="h-5 w-5 animate-spin rounded-full border-2 border-current border-t-transparent" />
                    Загрузка...
                  </>
                ) : (
                  <>
                    <svg
                      aria-hidden="true"
                      className="h-5 w-5"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12"
                      />
                    </svg>
                    Загрузить файл
                  </>
                )}
              </button>
            </div>
          </form>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
};
