type EmptyTemplatesStateProps = {
  canAdd: boolean;
  onAdd: () => void;
};

export const EmptyTemplatesState = ({
  canAdd,
  onAdd,
}: EmptyTemplatesStateProps) => {
  return (
    <div className="rounded-2xl border border-dashed border-zinc-300 bg-white/70 p-10 text-center dark:border-zinc-700 dark:bg-[#1E1E22]/60">
      <h2 className="text-xl font-semibold text-zinc-900 dark:text-zinc-50">
        Пока нет шаблонов
      </h2>

      <p className="mt-2 text-zinc-500 dark:text-zinc-400">
        Загрузите первый файл, чтобы начать работу.
      </p>

      {canAdd && (
        <button
          onClick={onAdd}
          className="mt-6 inline-flex items-center justify-center gap-2 rounded-xl bg-zinc-900 px-5 py-3 text-sm font-semibold text-white transition-all hover:bg-zinc-800 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-zinc-200"
        >
          Загрузить шаблон
        </button>
      )}
    </div>
  );
};
