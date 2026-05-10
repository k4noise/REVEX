import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate } from "@tanstack/react-router";
import { useQuery, useQueryClient, useMutation } from "@tanstack/react-query";
import { Helmet } from "react-helmet-async";
import { toast } from "sonner";

import { templateApi, queryKeys } from "../api/template";
import type {
  TemplateUpdateRequest,
  TemplateDetailResponse,
  ImageUploadResponse,
} from "../model/template";
import type { AnyPatch } from "../model/templateElement";
import { ApiError } from "../lib/api";

import { BlocksList } from "../features/template/components/BlocksList";
import { useGlobalScoring } from "../features/template/hooks/useGlobalScoring";
import { useQuestions } from "../features/template/hooks/useQuestions";
import { useEditorWithBaseline } from "../features/template/hooks/useEditorWithBaseline";
import { generatePatches } from "../features/template/utils/diff";
import { normalizeTotalPoints } from "../features/template/utils/validation";
import { cx } from "../features/template/utils/styles";
import { filterTreeByVisibility } from "../features/template/utils/visibility";
import type { FilterMode } from "../features/template/types";

type SaveMode = "save" | "publish";

interface TemplatePageProps {
  templateId: string;
  initialData: TemplateDetailResponse;
}

function useHotkeySave(enabled: boolean, onSave: () => void) {
  useEffect(() => {
    if (!enabled) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      const isSave = (e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "s";
      if (!isSave) return;
      e.preventDefault();
      onSave();
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [enabled, onSave]);
}

export function TemplatePage({ templateId, initialData }: TemplatePageProps) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const { data: template } = useQuery({
    queryKey: queryKeys.detail(templateId),
    queryFn: () => templateApi.getById(templateId),
    initialData,
    staleTime: 1000 * 60 * 5,
  });

  const serverTree = template._embedded?.elements || [];
  const editor = useEditorWithBaseline(serverTree);

  const [error, setError] = useState<string | null>(null);
  const [filterMode, setFilterMode] = useState<FilterMode>("all");

  const canEditContent = !!template._links.update;
  const canEditMeta = !!template._links.update && template.isDraft;
  const canPublish = !!template._links.publish && template.isDraft;
  const canDelete = !!template._links.delete;

  const [name, setName] = useState<string>(template.name);
  const [totalPoints, setTotalPoints] = useState<number>(
    normalizeTotalPoints(template.maxScore),
  );

  useEffect(() => {
    setName(template.name);
    setTotalPoints(normalizeTotalPoints(template.maxScore));
  }, [template.name, template.maxScore]);

  const metaDirty =
    canEditMeta &&
    (name !== template.name ||
      totalPoints !== normalizeTotalPoints(template.maxScore));

  const hasUnsaved = canEditContent && (editor.isDirty || metaDirty);

  const availableQuestions = useQuestions(editor.elements);
  const globalScoring = useGlobalScoring(editor.elements, totalPoints);

  const visibleElements = useMemo(
    () => filterTreeByVisibility(editor.elements, filterMode),
    [editor.elements, filterMode],
  );

  const saveMutation = useMutation({
    mutationFn: async ({ mode }: { mode: SaveMode }) => {
      setError(null);

      const updateHref = template._links.update?.href;
      if (!updateHref) throw new Error("Нет прав для сохранения");

      const publishHref = template._links.publish?.href;
      if (mode === "publish" && !publishHref)
        throw new Error("Нет прав для публикации");

      const patches: AnyPatch[] = generatePatches(
        editor.baselineRef.current,
        editor.elements,
      );

      const body: TemplateUpdateRequest = {};

      if (metaDirty) {
        body.name = name;
        body.maxScore = totalPoints;
      }

      if (patches.length > 0) {
        body.elements = { patches };
      }

      const shouldUpdate = Object.keys(body).length > 0;

      if (shouldUpdate) {
        await templateApi.update(updateHref, body);
      }

      if (mode === "publish") {
        await templateApi.publish(publishHref!);
      }
    },
    onSuccess: async (_data, variables) => {
      await queryClient.invalidateQueries({
        queryKey: queryKeys.detail(templateId),
      });

      if (variables.mode === "publish") {
        await queryClient.invalidateQueries({
          queryKey: queryKeys.collection(),
        });
        toast.success("Шаблон опубликован");
        navigate({ to: "/" });
      } else {
        toast.success("Сохранено");
      }
    },
    onError: (err) => {
      const message =
        err instanceof ApiError
          ? err.message
          : (err as Error)?.message || "Ошибка сохранения";
      setError(message);
      toast.error(message);
    },
  });

  const isSaving = saveMutation.isPending;

  const handleSave = useCallback(
    (mode: SaveMode) => {
      if (mode === "save" && !canEditContent) return;
      if (mode === "publish" && !canPublish) return;
      saveMutation.mutate({ mode });
    },
    [saveMutation, canEditContent, canPublish],
  );

  useHotkeySave(canEditContent && template.isDraft, () => handleSave("save"));

  useEffect(() => {
    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      if (!hasUnsaved) return;
      e.preventDefault();
      e.returnValue = "";
    };
    window.addEventListener("beforeunload", handleBeforeUnload);
    return () => window.removeEventListener("beforeunload", handleBeforeUnload);
  }, [hasUnsaved]);

  const deleteMutation = useMutation({
    mutationFn: async (href: string) => templateApi.remove(href),
    onSuccess: async () => {
      queryClient.removeQueries({ queryKey: queryKeys.detail(templateId) });
      await queryClient.invalidateQueries({ queryKey: queryKeys.collection() });
      navigate({ to: "/" });
    },
    onError: (err) => {
      const message = err instanceof ApiError ? err.message : "Ошибка удаления";
      setError(message);
      toast.error(message);
    },
  });

  const handleDelete = useCallback(() => {
    const href = template._links.delete?.href;
    if (!href) {
      setError("Нет прав для удаления");
      return;
    }
    const confirmed = window.confirm(
      `Удалить шаблон "${template.name}"? Это необратимо.`,
    );
    if (!confirmed) return;
    deleteMutation.mutate(href);
  }, [template, deleteMutation]);

  const uploadImageHref = template._links.upload_image?.href;

  const pickAndInsertImage = useCallback(
    (index: number) => {
      if (!uploadImageHref) {
        toast.error("Нет прав на загрузку изображений");
        return;
      }
      const input = document.createElement("input");
      input.type = "file";
      input.accept = "image/*";
      input.onchange = async () => {
        const file = input.files?.[0];
        if (!file) return;
        try {
          const res: ImageUploadResponse = await templateApi.uploadImage(
            uploadImageHref,
            file,
          );
          editor.insertImageAt(
            index,
            res.mediaKey,
            file.name,
            res.imageUrl ?? undefined,
          );
        } catch (e) {
          const msg =
            e instanceof Error ? e.message : "Не удалось загрузить картинку";
          toast.error(msg);
        }
      };
      input.click();
    },
    [uploadImageHref, editor],
  );

  const resetDisabled = !hasUnsaved || isSaving;

  return (
    <>
      <Helmet>
        <title>{name}</title>
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

          <div className="flex flex-1 min-w-0 items-center gap-3">
            {canEditMeta ? (
              <input
                className="min-w-0 flex-1 text-lg font-semibold bg-transparent outline-none placeholder:text-zinc-300 dark:placeholder:text-zinc-700"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Название шаблона..."
                required
              />
            ) : (
              <div className="truncate text-lg font-semibold text-zinc-900 dark:text-zinc-50">
                {template.name}
              </div>
            )}

            <span
              className={cx(
                "text-xs px-2 py-1 rounded-full border",
                template.isDraft
                  ? "border-amber-300 text-amber-700 bg-amber-50 dark:bg-amber-900/20 dark:text-amber-300 dark:border-amber-800"
                  : "border-emerald-300 text-emerald-700 bg-emerald-50 dark:bg-emerald-900/20 dark:text-emerald-300 dark:border-emerald-800",
              )}
            >
              {template.isDraft ? "Черновик" : "Опубликовано"}
            </span>
          </div>

          <div className="flex items-center gap-3">
            {canEditContent && (
              <button
                type="button"
                onClick={() => handleSave("save")}
                disabled={isSaving || !hasUnsaved}
                className={cx(
                  "px-4 py-2 text-sm font-medium rounded-xl border transition-colors",
                  hasUnsaved && !isSaving
                    ? "border-zinc-900 bg-zinc-900 text-white hover:bg-zinc-800"
                    : "border-zinc-300 bg-zinc-100 text-zinc-500 cursor-default",
                )}
                title="Ctrl/Cmd + S"
              >
                {isSaving
                  ? "Сохранение..."
                  : hasUnsaved
                    ? "Сохранить"
                    : "Нет изменений"}
              </button>
            )}

            {canPublish && (
              <button
                type="button"
                onClick={() => handleSave("publish")}
                disabled={isSaving}
                className="px-4 py-2 text-sm font-medium rounded-xl border border-blue-600 bg-blue-600 text-white disabled:opacity-40 hover:bg-blue-700 transition-colors"
              >
                Опубликовать
              </button>
            )}

            {canDelete && (
              <button
                type="button"
                disabled={isSaving}
                onClick={handleDelete}
                className="px-4 py-2 text-sm font-medium rounded-xl border border-red-600 text-red-700 dark:text-red-300 dark:border-red-900/60 hover:bg-red-50 dark:hover:bg-red-900/10 disabled:opacity-40 transition-colors"
              >
                Удалить
              </button>
            )}
          </div>
        </div>

        {canEditContent && (
          <div className="w-full px-6 pb-3 flex flex-wrap items-end gap-4">
            <div className="flex flex-col gap-1">
              <div className="text-xs text-zinc-500 font-medium">
                Режим просмотра
              </div>
              <div className="flex gap-2 bg-zinc-100 p-1.5 rounded-xl dark:bg-zinc-800/50">
                {(
                  [
                    ["all", "Все"],
                    ["important", "Важное"],
                    ["key", "Ключевое"],
                  ] as const
                ).map(([key, label]) => (
                  <button
                    key={key}
                    type="button"
                    onClick={() => setFilterMode(key)}
                    aria-pressed={filterMode === key}
                    className={cx(
                      "px-4 py-2 text-sm rounded-lg transition-colors font-semibold",
                      filterMode === key
                        ? "bg-white shadow-sm dark:bg-zinc-700 text-zinc-900 dark:text-white"
                        : "text-zinc-600 hover:text-zinc-900 dark:text-zinc-300 dark:hover:text-zinc-50",
                    )}
                  >
                    {label}
                  </button>
                ))}
              </div>
            </div>

            <div className="text-sm text-zinc-600 flex items-center gap-3">
              <span className="text-zinc-500">Баллов:</span>
              {canEditMeta ? (
                <input
                  type="number"
                  min={1}
                  max={1000}
                  step={1}
                  inputMode="numeric"
                  className="w-20 h-10 rounded-xl px-3 bg-transparent border border-zinc-300 outline-none font-semibold text-zinc-900 dark:border-zinc-700 dark:text-white"
                  value={totalPoints}
                  onChange={(e) =>
                    setTotalPoints(normalizeTotalPoints(e.target.value))
                  }
                />
              ) : (
                <span className="font-semibold text-zinc-900 dark:text-white">
                  {template.maxScore}
                </span>
              )}
            </div>

            {hasUnsaved && (
              <button
                type="button"
                disabled={resetDisabled}
                onClick={() => {
                  editor.resetToBaseline();
                  setName(template.name);
                  setTotalPoints(normalizeTotalPoints(template.maxScore));
                  setError(null);
                }}
                className="ml-auto px-5 py-2 text-sm rounded-xl border disabled:opacity-40 hover:bg-zinc-50 dark:hover:bg-zinc-900 dark:border-zinc-700 transition-colors font-medium"
              >
                Сбросить правки
              </button>
            )}
          </div>
        )}
      </div>

      <div className="max-w-7xl mx-auto mt-6 px-4 pb-32">
        <div className="bg-white dark:bg-[#1E1E22] rounded-2xl shadow-sm border border-zinc-200 dark:border-zinc-800 p-8 sm:p-14 min-h-[70vh]">
          {visibleElements.length === 0 && !canEditContent ? (
            <div className="text-center text-zinc-400 py-16">Шаблон пуст.</div>
          ) : (
            <BlocksList
              elements={visibleElements}
              updateElement={editor.updateElement}
              removeElement={editor.removeElement}
              moveUp={editor.moveElementUp}
              moveDown={editor.moveElementDown}
              indent={editor.indentElement}
              outdent={editor.outdentElement}
              isReadOnly={!canEditContent}
              isReportMode={false}
              availableQuestions={availableQuestions}
              inContainer={false}
              globalScoring={globalScoring}
              insideQuestion={false}
              convertCellToAnswer={
                canEditContent ? editor.convertCellToAnswer : undefined
              }
              clearCell={canEditContent ? editor.clearCell : undefined}
              insertTextAt={canEditContent ? editor.insertTextAt : undefined}
              insertQuestionAnswerAt={
                canEditContent ? editor.insertQuestionAnswerAt : undefined
              }
              insertImageAt={
                canEditContent && uploadImageHref
                  ? pickAndInsertImage
                  : undefined
              }
              insertGroupAt={canEditContent ? editor.insertGroupAt : undefined}
            />
          )}
        </div>

        {error && (
          <div className="mt-4 text-red-600 text-sm bg-red-50 dark:bg-red-900/20 p-3 rounded-lg border border-red-200 dark:border-red-900/50">
            Ошибка: {error}
          </div>
        )}
      </div>
    </>
  );
}
