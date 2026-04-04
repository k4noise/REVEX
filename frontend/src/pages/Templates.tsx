import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { Helmet } from "react-helmet-async";
import { useNavigate } from "@tanstack/react-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { templateApi, queryKeys } from "@/api/template";
import { ApiError } from "@/lib/api";
import type {
  TemplateCourseCollection,
  TemplateCourseSummary,
} from "@/model/template";
import { BulkActionsBar } from "@/features/templates/components/BulkActionsBar";
import { ConfirmModal } from "@/features/templates/components/ConfirmModal";
import { EmptyTemplatesState } from "@/features/templates/components/EmptyTemplatesState";
import { TemplateItem } from "@/features/templates/components/TemplateItem";
import { UploadModal } from "@/features/templates/components/UploadModal";
import { pluralizeTemplates } from "@/features/templates/pluralize";

type ConfirmState = {
  open: boolean;
  title: string;
  message: ReactNode;
  danger: boolean;
  confirmText: string;
  onConfirm: () => void;
};

export const TemplatesPage = ({
  initialData,
}: {
  initialData: TemplateCourseCollection;
}) => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const selectAllCheckboxRef = useRef<HTMLInputElement>(null);

  const { data: collection } = useQuery({
    queryKey: queryKeys.collection(),
    queryFn: templateApi.getCollection,
    initialData,
    staleTime: 1000 * 60 * 5,
  });

  const templates = collection._embedded.templates;

  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [isUploadOpen, setUploadOpen] = useState(false);

  const [confirm, setConfirm] = useState<ConfirmState>({
    open: false,
    title: "",
    message: null,
    danger: false,
    confirmText: "Подтвердить",
    onConfirm: () => {},
  });

  const [pendingDelete, setPendingDelete] = useState<string | null>(null);
  const [pendingPublish, setPendingPublish] = useState<string | null>(null);

  const canAdd = !!collection._links.add_template;
  const publishManyHref = collection._links.publish_many?.href;
  const deleteManyHref = collection._links.delete_many?.href;
  const hasPublishMany = !!publishManyHref;
  const hasDeleteMany = !!deleteManyHref;

  const selectionMode = selectedIds.size > 0;

  const selectedTemplates = useMemo(
    () => templates.filter((t) => selectedIds.has(t.id)),
    [templates, selectedIds],
  );

  const selectedDraftCount = useMemo(
    () => selectedTemplates.filter((t) => t.isDraft).length,
    [selectedTemplates],
  );

  const allSelected =
    templates.length > 0 && selectedIds.size === templates.length;

  useEffect(() => {
    if (selectAllCheckboxRef.current) {
      selectAllCheckboxRef.current.indeterminate =
        selectedIds.size > 0 && !allSelected;
    }
  }, [selectedIds.size, allSelected]);

  useEffect(() => {
    const existingIds = new Set(templates.map((t) => t.id));
    setSelectedIds((prev) => {
      const next = new Set([...prev].filter((id) => existingIds.has(id)));
      return next.size === prev.size ? prev : next;
    });
  }, [templates]);

  const toggle = (id: string) =>
    setSelectedIds((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });

  const toggleAll = () =>
    setSelectedIds(
      allSelected ? new Set() : new Set(templates.map((t) => t.id)),
    );

  const uploadMutation = useMutation({
    mutationFn: ({ file, separator }: { file: File; separator: string }) =>
      templateApi.upload(file, separator),
    onSuccess: async (res) => {
      await queryClient.invalidateQueries({ queryKey: queryKeys.collection() });
      setUploadOpen(false);
      toast.success("Шаблон загружен");
      navigate({ to: "/template/$templateId", params: { templateId: res.id } });
    },
    onError: (e) =>
      toast.error(e instanceof ApiError ? e.message : "Ошибка загрузки"),
  });

  const deleteMutation = useMutation({
    mutationFn: (template: TemplateCourseSummary) =>
      templateApi.remove(template._links.delete!.href),
    onMutate: (template) => setPendingDelete(template.id),
    onSettled: () => setPendingDelete(null),
    onSuccess: async (_, deletedTemplate) => {
      queryClient.setQueryData<TemplateCourseCollection>(
        queryKeys.collection(),
        (oldData) => {
          if (!oldData) return oldData;
          return {
            ...oldData,
            _embedded: {
              ...oldData._embedded,
              templates: oldData._embedded.templates.filter(
                (t) => t.id !== deletedTemplate.id,
              ),
            },
          };
        },
      );
      setConfirm((prev) => ({ ...prev, open: false }));
      toast.success("Шаблон удален");
    },
    onError: (e) =>
      toast.error(e instanceof ApiError ? e.message : "Ошибка удаления"),
  });

  const publishMutation = useMutation({
    mutationFn: (template: TemplateCourseSummary) =>
      templateApi.publish(template._links.publish!.href),
    onMutate: (template) => setPendingPublish(template.id),
    onSettled: () => setPendingPublish(null),
    onSuccess: async (_, publishedTemplate) => {
      queryClient.setQueryData<TemplateCourseCollection>(
        queryKeys.collection(),
        (oldData) => {
          if (!oldData) return oldData;
          return {
            ...oldData,
            _embedded: {
              ...oldData._embedded,
              templates: oldData._embedded.templates.map((t) =>
                t.id === publishedTemplate.id ? { ...t, isDraft: false } : t,
              ),
            },
          };
        },
      );
      toast.success("Шаблон опубликован");
    },
    onError: (e) =>
      toast.error(e instanceof ApiError ? e.message : "Ошибка публикации"),
  });

  const bulkDeleteMutation = useMutation({
    mutationFn: () => {
      if (!deleteManyHref) throw new Error("No delete many endpoint");
      return templateApi.deleteMany(deleteManyHref, [...selectedIds]);
    },
    onSuccess: async () => {
      const count = selectedIds.size;
      const targetIds = new Set(selectedIds);

      queryClient.setQueryData<TemplateCourseCollection>(
        queryKeys.collection(),
        (oldData) => {
          if (!oldData) return oldData;
          return {
            ...oldData,
            _embedded: {
              ...oldData._embedded,
              templates: oldData._embedded.templates.filter(
                (t) => !targetIds.has(t.id),
              ),
            },
          };
        },
      );

      setSelectedIds(new Set());
      setConfirm((prev) => ({ ...prev, open: false }));
      toast.success(`Удалено ${count} ${pluralizeTemplates(count)}`);
    },
    onError: () => toast.error("Ошибка удаления"),
  });

  const bulkPublishMutation = useMutation({
    mutationFn: () => {
      if (!publishManyHref) throw new Error("No publish many endpoint");
      const ids = selectedTemplates.filter((t) => t.isDraft).map((t) => t.id);
      return templateApi.publishMany(publishManyHref, ids);
    },
    onSuccess: async () => {
      const published = selectedDraftCount;
      const targetIds = new Set(
        selectedTemplates.filter((t) => t.isDraft).map((t) => t.id),
      );

      queryClient.setQueryData<TemplateCourseCollection>(
        queryKeys.collection(),
        (oldData) => {
          if (!oldData) return oldData;
          return {
            ...oldData,
            _embedded: {
              ...oldData._embedded,
              templates: oldData._embedded.templates.map((t) =>
                targetIds.has(t.id) ? { ...t, isDraft: false } : t,
              ),
            },
          };
        },
      );

      setSelectedIds(new Set());
      setConfirm((prev) => ({ ...prev, open: false }));
      toast.success(
        `Опубликовано ${published} ${pluralizeTemplates(published)}`,
      );
    },
    onError: () => toast.error("Ошибка публикации"),
  });

  const isUploadPending = uploadMutation.isPending;
  const isConfirmPending =
    deleteMutation.isPending ||
    publishMutation.isPending ||
    bulkDeleteMutation.isPending ||
    bulkPublishMutation.isPending;

  const canBulkPublish =
    hasPublishMany && selectedDraftCount > 0 && !bulkPublishMutation.isPending;
  const canBulkDelete =
    hasDeleteMany && selectedIds.size > 0 && !bulkDeleteMutation.isPending;

  const openDeleteConfirm = (template: TemplateCourseSummary) => {
    setConfirm({
      open: true,
      title: "Удалить шаблон?",
      message: (
        <>
          Вы действительно хотите удалить{" "}
          <span className="font-bold">«{template.name}»</span>?
        </>
      ),
      danger: true,
      confirmText: "Удалить",
      onConfirm: () => deleteMutation.mutate(template),
    });
  };

  const openBulkPublishConfirm = () => {
    setConfirm({
      open: true,
      title: "Опубликовать выбранные?",
      message: (
        <>
          Опубликовать черновики:{" "}
          <span className="font-bold">{selectedDraftCount}</span>
          {selectedIds.size !== selectedDraftCount ? (
            <>
              {" "}
              (ещё{" "}
              <span className="font-bold">
                {selectedIds.size - selectedDraftCount}
              </span>{" "}
              уже опубликованы)
            </>
          ) : null}
          ?
        </>
      ),
      danger: false,
      confirmText: "Опубликовать",
      onConfirm: () => bulkPublishMutation.mutate(),
    });
  };

  const openBulkDeleteConfirm = () => {
    setConfirm({
      open: true,
      title: "Удалить выбранные?",
      message: (
        <>
          Вы действительно хотите удалить{" "}
          <span className="font-bold">
            {selectedIds.size} {pluralizeTemplates(selectedIds.size)}
          </span>
          ?
        </>
      ),
      danger: true,
      confirmText: "Удалить",
      onConfirm: () => bulkDeleteMutation.mutate(),
    });
  };

  return (
    <>
      <Helmet>
        <title>{collection.courseName} — Шаблоны</title>
      </Helmet>
      <div className=" bg-[#F8FAFC] px-4 py-10 transition-colors duration-300 dark:bg-[#141416] sm:px-6">
        <div className="mx-auto max-w-5xl space-y-8">
          <div className="flex flex-col justify-between gap-4 border-b border-zinc-200 pb-6 dark:border-zinc-800/50 sm:flex-row sm:items-center">
            <div>
              <h1 className="text-3xl font-bold tracking-tight text-zinc-900 dark:text-zinc-50">
                {collection.courseName}
              </h1>
              <p className="mt-1 text-lg text-zinc-500 dark:text-zinc-400">
                Список шаблонов курса
              </p>
            </div>

            {canAdd && (
              <button
                onClick={() => setUploadOpen(true)}
                className="inline-flex items-center justify-center gap-3 rounded-xl bg-zinc-900 px-6 py-3.5 text-base font-semibold text-white transition-all active:scale-[0.98] dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-zinc-200 hover:bg-zinc-800"
              >
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
                    d="M12 4v16m8-8H4"
                  />
                </svg>
                Добавить шаблон
              </button>
            )}
          </div>

          {templates.length === 0 ? (
            <EmptyTemplatesState
              canAdd={canAdd}
              onAdd={() => setUploadOpen(true)}
            />
          ) : (
            <>
              <div className="mb-3 flex flex-wrap items-center gap-3">
                <button
                  type="button"
                  onClick={toggleAll}
                  className="inline-flex items-center justify-center rounded-xl border border-zinc-200 bg-white px-4 py-2 text-sm font-semibold text-zinc-900 hover:bg-zinc-50 dark:border-zinc-800 dark:bg-[#1E1E22] dark:text-zinc-50 dark:hover:bg-zinc-800/40"
                >
                  {allSelected ? "Снять выделение" : "Выбрать все"}
                </button>

                {selectedIds.size > 0 && (
                  <button
                    type="button"
                    onClick={() => setSelectedIds(new Set())}
                    className="text-sm text-zinc-500 underline underline-offset-4 hover:text-zinc-700 dark:hover:text-zinc-300"
                  >
                    Очистить выбор
                  </button>
                )}
              </div>

              <ul className={`grid gap-3 ${selectionMode ? "pb-28" : ""}`}>
                {templates.map((template) => (
                  <TemplateItem
                    key={template.id}
                    template={template}
                    selected={selectedIds.has(template.id)}
                    onToggle={() => toggle(template.id)}
                    onDelete={() => openDeleteConfirm(template)}
                    onPublish={() => publishMutation.mutate(template)}
                    isDeleting={pendingDelete === template.id}
                    isPublishing={pendingPublish === template.id}
                  />
                ))}
              </ul>
            </>
          )}
        </div>

        {selectionMode && (
          <BulkActionsBar
            selectedCount={selectedIds.size}
            selectedDraftCount={selectedDraftCount}
            allSelected={allSelected}
            selectAllCheckboxRef={selectAllCheckboxRef}
            onToggleAll={toggleAll}
            onClearSelection={() => setSelectedIds(new Set())}
            hasPublishMany={hasPublishMany}
            hasDeleteMany={hasDeleteMany}
            canBulkPublish={canBulkPublish}
            canBulkDelete={canBulkDelete}
            onBulkPublish={openBulkPublishConfirm}
            onBulkDelete={openBulkDeleteConfirm}
          />
        )}

        <UploadModal
          isOpen={isUploadOpen}
          onClose={() => setUploadOpen(false)}
          handleUpload={(file, separator) =>
            uploadMutation.mutate({ file, separator })
          }
          isPending={isUploadPending}
        />

        <ConfirmModal
          isOpen={confirm.open}
          onClose={() => setConfirm((prev) => ({ ...prev, open: false }))}
          onConfirm={confirm.onConfirm}
          title={confirm.title}
          message={confirm.message}
          danger={confirm.danger}
          confirmText={confirm.confirmText}
          isPending={isConfirmPending}
        />
      </div>
    </>
  );
};
