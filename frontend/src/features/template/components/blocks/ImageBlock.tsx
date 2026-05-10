import { memo } from "react";
import type { CommonBlockProps } from "../../types";
import { cx } from "../../utils/styles";

export const ImageBlock = memo(function ImageBlock({
  element,
  updateElement,
  isReadOnly,
}: CommonBlockProps) {
  const imageUrl = element.imageUrl ?? null;
  const altText = element.altText || "";

  return (
    <div
      className={cx("my-6 rounded-xl bg-zinc-50 p-5", "dark:bg-zinc-900/30")}
    >
      <div
        className={cx(
          "overflow-hidden rounded-xl bg-white",
          "dark:bg-[#141416]",
          "flex items-center justify-center min-h-[180px]",
        )}
      >
        {imageUrl ? (
          <img
            src={imageUrl}
            alt={altText}
            className="block max-h-[420px] w-auto max-w-full object-contain"
            loading="lazy"
          />
        ) : (
          <div className="flex h-[180px] w-full flex-col items-center justify-center text-zinc-400">
            <div className="mb-2 flex h-14 w-14 items-center justify-center rounded-2xl bg-zinc-200 text-sm font-bold dark:bg-zinc-800">
              IMG
            </div>
            <div className="text-sm">Изображение недоступно</div>
          </div>
        )}
      </div>

      {!isReadOnly && (
        <input
          type="text"
          value={altText}
          onChange={(e) =>
            updateElement(element.id, { altText: e.target.value })
          }
          aria-label="Описание изображения"
          className={cx(
            "mt-4 w-full rounded-xl px-4 py-3 text-sm outline-none text-center",
            "bg-white border-b border-zinc-200 text-zinc-700",
            "dark:bg-[#141416] dark:border-zinc-700 dark:text-zinc-200",
            "focus:ring-2 focus:ring-blue-500/20",
          )}
          placeholder="Описание изображения (alt)..."
        />
      )}

      {isReadOnly && altText && (
        <div className="mt-4 text-center text-sm text-zinc-500 dark:text-zinc-400">
          {altText}
        </div>
      )}
    </div>
  );
});
