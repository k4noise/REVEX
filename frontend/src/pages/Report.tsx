import { useCallback, useEffect, useMemo, useState } from "react";
import { Helmet } from "react-helmet-async";
import { useNavigate } from "@tanstack/react-router";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { reportApi, reportQueryKeys } from "../api/report";
import { queryKeys as templateQueryKeys } from "../api/template";
import { ApiError } from "../lib/api";
import { useHints } from "../features/template/hooks/useHints";
import type {
  FullWorkResponse,
  UpdateAnswerDataPayload,
  UpdateAnswerScorePayload,
  ReportStatus,
  AnswerData,
  PreGradedAnswerData,
} from "../model/report";
import type { TemplateElementResponse } from "../model/templateElement";
import type { AnswerGradingInfo, FilterMode } from "../features/template/types";
import { getGradingStatus } from "../features/template/types";
import { useEditorWithBaseline } from "../features/template/hooks/useEditorWithBaseline";
import { useGlobalScoring } from "../features/template/hooks/useGlobalScoring";
import { BlocksList } from "../features/template/components/BlocksList";
import { cx } from "../features/template/utils/styles";
import { floorTo2 } from "../features/template/utils/scoring";
import { filterTreeByVisibility } from "../features/template/utils/visibility";
import {
  useGradingQueue,
  clearGradingQueue,
} from "../features/grading/useGradingQueue";

const statusLabel: Record<ReportStatus, string> = {
  created: "В работе",
  saved: "В работе",
  submitted: "На проверке",
  graded: "Оценено",
};

const statusClassName: Record<ReportStatus, string> = {
  graded:
    "border-emerald-300 bg-emerald-50 text-emerald-700 dark:bg-emerald-900/20 dark:text-emerald-300",
  submitted:
    "border-amber-300 bg-amber-50 text-amber-700 dark:bg-amber-900/20 dark:text-amber-300",
  saved:
    "border-zinc-300 bg-zinc-100 text-zinc-600 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-300",
  created:
    "border-zinc-300 bg-zinc-100 text-zinc-600 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-300",
};

type ReportPageProps = {
  reportId: string;
  initialData: FullWorkResponse;
};

function extractAnswerText(data: Record<string, unknown> | null): string {
  if (!data || typeof data !== "object") return "";
  const nested = data.data;
  if (nested && typeof nested === "object" && "text" in nested) {
    const text = (nested as Record<string, unknown>).text;
    if (typeof text === "string") return text;
  }
  if ("text" in data && typeof data.text === "string") {
    return data.text;
  }
  return "";
}

function isPreGraded(
  a: AnswerData | PreGradedAnswerData,
): a is PreGradedAnswerData {
  return "preGrade" in a;
}

function countFilledAnswers(nodes: TemplateElementResponse[]): {
  total: number;
  filled: number;
} {
  let total = 0;
  let filled = 0;
  const walk = (list: TemplateElementResponse[]) => {
    for (const node of list) {
      if (node.type === "answer") {
        total++;
        if (typeof node.data === "string" && node.data.trim()) {
          filled++;
        }
      }
      if (node.children?.length) walk(node.children);
    }
  };
  walk(nodes);
  return { total, filled };
}

export const ReportPage = ({ reportId, initialData }: ReportPageProps) => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const gradingQueue = useGradingQueue(reportId);

  const { data: report } = useQuery({
    queryKey: reportQueryKeys.detail(reportId),
    queryFn: () => reportApi.getById(reportId),
    initialData,
    staleTime: 1000 * 60 * 5,
  });

  const isEditableStatus =
    report.status === "created" || report.status === "saved";
  const isGraded = report.status === "graded";

  const canSave = isEditableStatus && !!report._links?.save;
  const canSubmit = isEditableStatus && !!report._links?.submit;
  const canUnsubmit =
    report.status === "submitted" && !!report._links?.unsubmit;
  const canGrade =
    (report.status === "submitted" || isGraded) && !!report._links?.grade;

  const maxScore = report.template?.maxScore ?? 0;
  const isGradingMode = canGrade && maxScore > 0;
  const isReadOnly = !canSave;

  const [filterMode, setFilterMode] = useState<FilterMode>(
    isGradingMode ? "important" : "all",
  );

  const reportAnswers: (AnswerData | PreGradedAnswerData)[] =
    report._embedded?.answers ?? [];

  const answerByElementId = useMemo(
    () => new Map(reportAnswers.map((a) => [a.elementId, a])),
    [reportAnswers],
  );

  const hasAnyGrades = useMemo(
    () => reportAnswers.some((a) => a.score != null),
    [reportAnswers],
  );

  const isGradedView =
    (isGraded && !canGrade) ||
    (!isEditableStatus && !isGradingMode && hasAnyGrades);

  const showAnswerGrades = isGradingMode || isGradedView || hasAnyGrades;

  const mergedTree = useMemo(() => {
    const mergeNode = (
      nodes: TemplateElementResponse[],
    ): TemplateElementResponse[] => {
      return nodes.map((node) => {
        const ans = answerByElementId.get(node.id);
        const newNode: TemplateElementResponse = {
          ...node,
          data:
            node.type === "answer" && ans?.data
              ? extractAnswerText(ans.data)
              : node.data,
          children: node.children ? mergeNode(node.children) : [],
        };
        return newNode;
      });
    };

    return mergeNode(report.template?.elements || []);
  }, [report.template?.elements, answerByElementId]);

  const editor = useEditorWithBaseline(mergedTree);

  const visibleElements = useMemo(
    () => filterTreeByVisibility(editor.elements, filterMode),
    [editor.elements, filterMode],
  );

  const globalScoring = useGlobalScoring(editor.elements, maxScore);

  const fillProgress = useMemo(
    () => countFilledAnswers(editor.elements),
    [editor.elements],
  );

  const [answerGrades, setAnswerGrades] = useState<Map<string, number>>(
    new Map(),
  );
  const [answerComments, setAnswerComments] = useState<Map<string, string>>(
    new Map(),
  );

  useEffect(() => {
    const initialGrades = new Map<string, number>();
    const initialComments = new Map<string, string>();

    for (const ans of reportAnswers) {
      if (ans.score != null && Number.isFinite(ans.score)) {
        initialGrades.set(ans.elementId, ans.score);
      }
      if (ans.comment) {
        initialComments.set(ans.elementId, ans.comment);
      }
    }

    setAnswerGrades(initialGrades);
    setAnswerComments(initialComments);
  }, [reportId, reportAnswers]);

  const handleAnswerGradeChange = useCallback(
    (elementId: string, grade: number) => {
      setAnswerGrades((prev) => {
        const next = new Map(prev);
        next.set(elementId, grade);
        return next;
      });
    },
    [],
  );

  const handleAnswerCommentChange = useCallback(
    (elementId: string, comment: string) => {
      setAnswerComments((prev) => {
        const next = new Map(prev);
        next.set(elementId, comment);
        return next;
      });
    },
    [],
  );

  const currentAnswerTexts = useMemo(() => {
    const map = new Map<string, string>();
    const walk = (nodes: TemplateElementResponse[]) => {
      for (const node of nodes) {
        if (node.type === "answer") {
          map.set(node.id, node.data || "");
        }
        if (node.children?.length) walk(node.children);
      }
    };
    walk(editor.elements);
    return map;
  }, [editor.elements]);

  const getCurrentText = useCallback(
    (elementId: string) => currentAnswerTexts.get(elementId) ?? "",
    [currentAnswerTexts],
  );

  const hintHref = report._links?.get_hint?.href;

  const {
    hints: studentHintsMap,
    scheduleHint,
    requestHintNow,
  } = useHints({
    enabled: isEditableStatus && canSave && !!hintHref,
    hintHref,
    elements: report.template?.elements || [],
    answerByElementId,
    getCurrentText,
  });

  const handleAnswerBlur = useCallback(
    (elementId: string) => {
      requestHintNow(elementId);
    },
    [requestHintNow],
  );

  const handleAnswerInput = useCallback(
    (elementId: string) => {
      scheduleHint(elementId);
    },
    [scheduleHint],
  );

  const answerGrading = useMemo(() => {
    if (!showAnswerGrades) return undefined;

    const map = new Map<string, AnswerGradingInfo>();

    for (const [elementId, ans] of answerByElementId) {
      const scoring = globalScoring?.byAnswerId?.[elementId];

      const originalText = ans.data ? extractAnswerText(ans.data) : "";
      const currentText = currentAnswerTexts.get(elementId) ?? "";
      const textModified = isEditableStatus && currentText !== originalText;

      const rawPreviousGrade =
        ans.score != null && Number.isFinite(ans.score)
          ? ans.score
          : isPreGraded(ans) &&
              ans.preGrade?.score != null &&
              Number.isFinite(ans.preGrade.score)
            ? ans.preGrade.score
            : null;

      const previousGrade =
        rawPreviousGrade != null
          ? Math.min(1, Math.max(0, rawPreviousGrade))
          : null;

      const previousStatus = getGradingStatus(previousGrade);

      if (!scoring) {
        map.set(elementId, {
          grade: textModified ? null : previousGrade,
          maxPoints: 0,
          earnedPoints: 0,
          previousGrade,
          previousEarnedPoints: 0,
          previousComment: ans.comment ?? "",
          previousStatus,
          preGrade: isPreGraded(ans) ? ans.preGrade : undefined,
          comment: answerComments.get(elementId) ?? ans.comment ?? "",
          status: getGradingStatus(textModified ? null : previousGrade),
          originalText,
        });
        continue;
      }

      const safeMax = scoring.points;
      const preGrade = isPreGraded(ans) ? ans.preGrade : undefined;

      const currentGrade =
        isGradingMode && answerGrades.has(elementId)
          ? answerGrades.get(elementId)!
          : previousGrade;

      const effectiveGrade = textModified ? null : currentGrade;

      const earnedPoints =
        effectiveGrade !== null ? floorTo2(effectiveGrade * safeMax) : 0;

      const previousEarnedPoints =
        previousGrade !== null ? floorTo2(previousGrade * safeMax) : 0;

      map.set(elementId, {
        grade: effectiveGrade,
        maxPoints: safeMax,
        earnedPoints,
        previousGrade,
        previousEarnedPoints,
        previousComment: ans.comment ?? "",
        previousStatus,
        preGrade,
        comment: answerComments.get(elementId) ?? ans.comment ?? "",
        status: getGradingStatus(effectiveGrade),
        originalText,
      });
    }

    return map;
  }, [
    answerByElementId,
    answerGrades,
    answerComments,
    globalScoring,
    showAnswerGrades,
    currentAnswerTexts,
    isEditableStatus,
    isGradingMode,
  ]);

  const totalScore = useMemo(() => {
    if (!answerGrading) return 0;
    let sum = 0;
    for (const [, info] of answerGrading) {
      sum += info.earnedPoints;
    }
    return floorTo2(sum);
  }, [answerGrading]);

  const gradingProgress = useMemo(() => {
    if (!answerGrading) return { total: 0, graded: 0 };
    let total = 0;
    let graded = 0;
    for (const [, info] of answerGrading) {
      total++;
      if (info.grade !== null) graded++;
    }
    return { total, graded };
  }, [answerGrading]);

  const allAnswersScored =
    gradingProgress.graded === gradingProgress.total &&
    gradingProgress.total > 0;

  const hasUnsavedGrades = useMemo(() => {
    if (!isGradingMode) return false;
    for (const [elementId, grade] of answerGrades.entries()) {
      const originalGrade = answerByElementId.get(elementId)?.score;
      if (grade !== originalGrade) return true;
    }
    for (const [elementId, comment] of answerComments.entries()) {
      const originalComment = answerByElementId.get(elementId)?.comment;
      if (comment !== originalComment) return true;
    }
    return false;
  }, [isGradingMode, answerGrades, answerComments, answerByElementId]);

  const extractAnswers = (
    nodes: TemplateElementResponse[],
  ): UpdateAnswerDataPayload[] => {
    const result: UpdateAnswerDataPayload[] = [];

    const visit = (node: TemplateElementResponse) => {
      if (node.type === "answer") {
        const ans = answerByElementId.get(node.id);
        if (ans) {
          const text = typeof node.data === "string" ? node.data : "";
          result.push({ id: ans.id, data: { text } });
        }
      }
      node.children?.forEach(visit);
    };

    nodes.forEach(visit);
    return result;
  };

  const saveMutation = useMutation({
    mutationFn: () => {
      const payload = extractAnswers(editor.elements);
      return reportApi.saveAnswers(report._links.save!.href, payload);
    },
    onSuccess: async () => {
      editor.commitBaseline(editor.elements);
      toast.success("Сохранено");
      await queryClient.invalidateQueries({
        queryKey: reportQueryKeys.detail(reportId),
      });
    },
    onError: (err) => {
      toast.error(err instanceof ApiError ? err.message : "Ошибка сохранения");
    },
  });

  const submitMutation = useMutation({
    mutationFn: async () => {
      if (editor.isDirty && canSave) {
        const payload = extractAnswers(editor.elements);
        await reportApi.saveAnswers(report._links.save!.href, payload);
      }
      return reportApi.submit(report._links.submit!.href);
    },
    onSuccess: async () => {
      toast.success("Работа отправлена на проверку");
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: templateQueryKeys.all }),
        queryClient.invalidateQueries({
          queryKey: reportQueryKeys.detail(reportId),
        }),
      ]);
      navigate({ to: "/" });
    },
    onError: (err) => {
      toast.error(err instanceof ApiError ? err.message : "Ошибка отправки");
    },
  });

  const unsubmitMutation = useMutation({
    mutationFn: () => reportApi.unsubmit(report._links.unsubmit!.href),
    onSuccess: async () => {
      toast.success("Отправка отменена");
      await queryClient.invalidateQueries({
        queryKey: reportQueryKeys.detail(reportId),
      });
    },
    onError: (err) => {
      toast.error(err instanceof ApiError ? err.message : "Ошибка отмены");
    },
  });

  const gradeMutation = useMutation({
    mutationFn: () => {
      const payload: UpdateAnswerScorePayload[] = [];
      for (const [elementId, ans] of answerByElementId.entries()) {
        const info = answerGrading?.get(elementId);
        if (info) {
          payload.push({
            id: ans.id,
            score: info.grade ?? 0,
            comment: info.comment ?? "",
          });
        }
      }
      return reportApi.grade(report._links.grade!.href, payload);
    },
    onSuccess: async () => {
      toast.success("Работа оценена");

      const tplId = report.template?.id;

      await Promise.all([
        queryClient.invalidateQueries({ queryKey: templateQueryKeys.all }),
        queryClient.invalidateQueries({
          queryKey: reportQueryKeys.detail(reportId),
        }),
        ...(tplId
          ? [
              queryClient.invalidateQueries({
                queryKey: templateQueryKeys.reports(tplId),
              }),
            ]
          : []),
      ]);

      if (tplId) {
        queryClient.removeQueries({
          queryKey: templateQueryKeys.reports(tplId),
        });
      }

      if (gradingQueue.isInQueue) {
        if (gradingQueue.hasNext) {
          const nextId = gradingQueue.advanceQueue();
          if (nextId) {
            navigate({ to: "/report/$reportId", params: { reportId: nextId } });
            return;
          }
        }

        clearGradingQueue();
        toast.success("Все работы проверены");

        if (tplId) {
          navigate({
            to: "/template/$templateId/reports",
            params: { templateId: tplId },
          });
        } else {
          navigate({ to: "/" });
        }
        return;
      }

      if (tplId) {
        navigate({
          to: "/template/$templateId/reports",
          params: { templateId: tplId },
        });
      } else {
        navigate({ to: "/" });
      }
    },
    onError: (err) => {
      toast.error(err instanceof ApiError ? err.message : "Ошибка оценки");
    },
  });

  const isPending =
    saveMutation.isPending ||
    submitMutation.isPending ||
    unsubmitMutation.isPending ||
    gradeMutation.isPending;

  useEffect(() => {
    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      if (!editor.isDirty && !hasUnsavedGrades) return;
      if (!isEditableStatus && !isGradingMode) return;
      e.preventDefault();
      e.returnValue = "";
    };
    window.addEventListener("beforeunload", handleBeforeUnload);
    return () => window.removeEventListener("beforeunload", handleBeforeUnload);
  }, [editor.isDirty, hasUnsavedGrades, isEditableStatus, isGradingMode]);

  useEffect(() => {
    if (!canSave) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "s") {
        e.preventDefault();
        if (editor.isDirty) saveMutation.mutate();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [canSave, editor.isDirty, saveMutation]);

  const showToolbarSecondRow = isGradingMode;

  const handleBackClick = () => {
    if (gradingQueue.isInQueue && gradingQueue.templateId) {
      clearGradingQueue();
      navigate({
        to: "/template/$templateId/reports",
        params: { templateId: gradingQueue.templateId },
      });
    } else {
      navigate({ to: "/" });
    }
  };

  const pageTitle = `${
    isGradingMode ? "Проверка" : isGradedView ? "Результат" : "Отчет"
  }: ${report.template?.name ?? "Без названия"}`;

  return (
    <>
      <Helmet>
        <title>{pageTitle}</title>
      </Helmet>

      <div className="sticky top-0 z-[80] isolate border-b border-zinc-200/80 bg-white/80 backdrop-blur dark:border-zinc-800/80 dark:bg-[#0F0F12]/80">
        <div className="flex h-16 w-full items-center gap-4 px-6">
          <button
            type="button"
            onClick={handleBackClick}
            className="text-sm opacity-70 hover:opacity-100"
          >
            ← {gradingQueue.isInQueue ? "К списку отчетов" : "Список"}
          </button>

          <div className="flex min-w-0 flex-1 items-center gap-3">
            <h1 className="truncate text-lg font-semibold text-zinc-900 dark:text-zinc-50">
              {report.template?.name}
            </h1>

            <span
              className={cx(
                "rounded-full border px-2.5 py-1 text-xs font-semibold",
                statusClassName[report.status],
              )}
            >
              {statusLabel[report.status]}
            </span>

            {isGraded && report.score != null && (
              <span className="font-bold text-emerald-600 dark:text-emerald-400">
                {report.score} / {maxScore}
              </span>
            )}

            {isGraded && report.graderName && (
              <span className="text-sm text-zinc-500 dark:text-zinc-400">
                Оценил: {report.graderName}
              </span>
            )}
          </div>

          <div className="flex items-center gap-3">
            {isGradingMode && gradingQueue.isInQueue && (
              <div className="flex items-center gap-2">
                <span className="text-sm text-zinc-500 dark:text-zinc-400 tabular-nums">
                  {gradingQueue.currentIndex + 1} / {gradingQueue.totalCount}
                </span>

                {gradingQueue.hasPrev && (
                  <button
                    type="button"
                    onClick={() => {
                      if (gradingQueue.prevReportId) {
                        navigate({
                          to: "/report/$reportId",
                          params: { reportId: gradingQueue.prevReportId },
                        });
                      }
                    }}
                    disabled={isPending}
                    className={cx(
                      "rounded-xl border px-3 py-2 text-sm font-medium transition-colors",
                      "border-zinc-300 bg-white text-zinc-700 hover:bg-zinc-50",
                      "dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-300 dark:hover:bg-zinc-700",
                      "disabled:opacity-50",
                    )}
                  >
                    ← Пред.
                  </button>
                )}

                <button
                  type="button"
                  onClick={() => {
                    clearGradingQueue();
                    navigate({ to: "/" });
                  }}
                  className="rounded-xl border border-zinc-300 px-3 py-2 text-sm font-medium text-zinc-600 hover:bg-zinc-50 transition-colors dark:border-zinc-700 dark:text-zinc-400 dark:hover:bg-zinc-800"
                >
                  Выйти
                </button>
              </div>
            )}

            {isGradingMode && (
              <>
                <span className="text-sm text-zinc-500 dark:text-zinc-400 tabular-nums">
                  {gradingProgress.graded} / {gradingProgress.total} оценено
                </span>
                <span className="text-base font-semibold tabular-nums text-zinc-900 dark:text-zinc-50">
                  {totalScore}
                  <span className="text-sm font-normal text-zinc-400 dark:text-zinc-500">
                    {" "}
                    / {maxScore}
                  </span>
                </span>
              </>
            )}

            {canGrade && maxScore === 0 && (
              <span className="text-sm font-medium text-red-600 dark:text-red-400">
                Баллы не заданы в шаблоне
              </span>
            )}

            {isEditableStatus && fillProgress.total > 0 && (
              <span className="text-sm text-zinc-500 dark:text-zinc-400 tabular-nums">
                {fillProgress.filled} / {fillProgress.total} заполнено
              </span>
            )}

            {canUnsubmit && (
              <button
                type="button"
                onClick={() => unsubmitMutation.mutate()}
                disabled={isPending}
                className={cx(
                  "rounded-xl border px-4 py-2 text-sm font-medium transition-colors disabled:opacity-60",
                  "border-zinc-300 bg-white text-zinc-800 hover:bg-zinc-50",
                  "dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-100 dark:hover:bg-zinc-700",
                )}
              >
                Отменить отправку
              </button>
            )}

            {canSave && (
              <button
                type="button"
                onClick={() => saveMutation.mutate()}
                disabled={!editor.isDirty || isPending}
                className={cx(
                  "rounded-xl border px-4 py-2 text-sm font-medium transition-colors disabled:opacity-50",
                  editor.isDirty && !isPending
                    ? "border-zinc-900 bg-zinc-900 text-white hover:bg-zinc-800 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-zinc-200"
                    : "border-zinc-300 bg-zinc-100 text-zinc-500 dark:border-zinc-800 dark:bg-[#141416] dark:text-zinc-600",
                )}
                title="Ctrl/Cmd + S"
              >
                Сохранить
              </button>
            )}

            {canSubmit && (
              <button
                type="button"
                onClick={() => {
                  if (window.confirm("Отправить работу на проверку?")) {
                    submitMutation.mutate();
                  }
                }}
                disabled={isPending}
                className="rounded-xl border border-blue-600 bg-blue-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-700 disabled:opacity-50"
              >
                Сдать работу
              </button>
            )}

            {isGradingMode && (
              <button
                type="button"
                onClick={() => {
                  const label =
                    gradingQueue.isInQueue && gradingQueue.hasNext
                      ? `Оценить и перейти к следующему (${gradingQueue.currentIndex + 2}/${gradingQueue.totalCount})?`
                      : `Выставить оценку ${totalScore} / ${maxScore}?`;

                  if (window.confirm(label)) {
                    gradeMutation.mutate();
                  }
                }}
                disabled={isPending || !allAnswersScored}
                title={!allAnswersScored ? "Оцените все ответы" : undefined}
                className="rounded-xl border border-emerald-600 bg-emerald-600 px-5 py-2 text-sm font-semibold text-white transition-colors hover:bg-emerald-700 disabled:opacity-50"
              >
                {gradingQueue.isInQueue && gradingQueue.hasNext
                  ? "Оценить + след."
                  : isGraded
                    ? "Переоценить"
                    : "Оценить"}
              </button>
            )}
          </div>
        </div>

        {showToolbarSecondRow && (
          <div className="w-full px-6 pb-3 flex flex-wrap items-end gap-4">
            <div className="flex flex-col gap-1">
              <div className="text-xs text-zinc-500 font-medium">
                Режим просмотра
              </div>
              <div className="flex gap-1 bg-zinc-100 p-1 rounded-xl dark:bg-zinc-800/50">
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
                      "px-3 py-1.5 text-sm rounded-lg transition-colors font-semibold",
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
          </div>
        )}
      </div>

      <div className="mx-auto mt-6 max-w-7xl px-4 pb-32">
        <div className="min-h-[70vh] rounded-2xl bg-white p-8 shadow-sm dark:bg-[#1E1E22] sm:p-14">
          <BlocksList
            elements={visibleElements}
            updateElement={editor.updateElement}
            removeElement={editor.removeElement}
            moveUp={editor.moveElementUp}
            moveDown={editor.moveElementDown}
            indent={editor.indentElement}
            outdent={editor.outdentElement}
            isReadOnly={isReadOnly || isGradingMode}
            isReportMode={!isGradingMode}
            isGradingMode={isGradingMode}
            globalScoring={showAnswerGrades ? globalScoring : undefined}
            answerGrading={answerGrading}
            onAnswerGradeChange={
              isGradingMode ? handleAnswerGradeChange : undefined
            }
            onAnswerCommentChange={
              isGradingMode ? handleAnswerCommentChange : undefined
            }
            hints={isEditableStatus ? studentHintsMap : undefined}
            onAnswerBlur={isEditableStatus ? handleAnswerBlur : undefined}
            onAnswerInput={isEditableStatus ? handleAnswerInput : undefined}
          />
        </div>
      </div>
    </>
  );
};
