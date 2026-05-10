import { useCallback, useEffect, useRef, useState } from "react";
import { reportApi } from "../../../api/report";
import { ApiError } from "../../../lib/api";
import type {
  HintRequest,
  HintAnswerPayload,
  AnswerData,
  PreGradedAnswerData,
} from "../../../model/report";
import type { TemplateElementResponse } from "../../../model/templateElement";

export interface HintEntry {
  hint: string;
  score?: number;
}

interface UseHintsOptions {
  enabled: boolean;
  hintHref?: string;
  elements: TemplateElementResponse[];
  answerByElementId: Map<string, AnswerData | PreGradedAnswerData>;
  getCurrentText: (elementId: string) => string;
}

function findQuestionForAnswer(
  elements: TemplateElementResponse[],
  answerId: string,
): TemplateElementResponse | null {
  const walk = (
    nodes: TemplateElementResponse[],
    parent: TemplateElementResponse | null,
  ): TemplateElementResponse | null => {
    for (const node of nodes) {
      if (node.type === "answer" && node.id === answerId) {
        return parent?.type === "question" ? parent : null;
      }
      if (node.children?.length) {
        const found = walk(node.children, node);
        if (found) return found;
      }
    }
    return null;
  };
  return walk(elements, null);
}

function extractVarIds(text: string): string[] {
  const ids: string[] = [];
  const regex = /\{([0-9a-fA-F-]{36})(?:\|[^}]*)?\}/g;
  let match;
  while ((match = regex.exec(text)) !== null) {
    ids.push(match[1]);
  }
  return ids;
}

function buildAnswerPayload(
  elementId: string,
  answerByElementId: Map<string, AnswerData | PreGradedAnswerData>,
  currentText: string,
): HintAnswerPayload | null {
  const ans = answerByElementId.get(elementId);
  if (!ans) return null;
  return {
    id: ans.id,
    element_id: ans.elementId,
    score: ans.score,
    data: { text: currentText },
  };
}

export function useHints({
  enabled,
  hintHref,
  elements,
  answerByElementId,
  getCurrentText,
}: UseHintsOptions) {
  const [hints, setHints] = useState<Map<string, HintEntry>>(() => new Map());
  const abortControllerRef = useRef<Map<string, AbortController>>(new Map());
  const debounceTimerRef = useRef<Map<string, ReturnType<typeof setTimeout>>>(
    new Map(),
  );
  const cooldownRef = useRef<Map<string, number>>(new Map());

  const enabledRef = useRef(enabled);
  const hintHrefRef = useRef(hintHref);
  const elementsRef = useRef(elements);
  const answerByElementIdRef = useRef(answerByElementId);
  const getCurrentTextRef = useRef(getCurrentText);

  useEffect(() => {
    enabledRef.current = enabled;
    hintHrefRef.current = hintHref;
    elementsRef.current = elements;
    answerByElementIdRef.current = answerByElementId;
    getCurrentTextRef.current = getCurrentText;
  });

  useEffect(() => {
    const controllers = abortControllerRef.current;
    return () => {
      controllers.forEach((controller) => controller.abort());
    };
  }, []);

  const isOnCooldown = useCallback((elementId: string) => {
    const until = cooldownRef.current.get(elementId);
    if (!until) return false;
    if (Date.now() < until) return true;
    cooldownRef.current.delete(elementId);
    return false;
  }, []);

  const requestHint = useCallback(
    async (answerElementId: string) => {
      if (!enabledRef.current || !hintHrefRef.current) return;
      if (isOnCooldown(answerElementId)) return;

      if (abortControllerRef.current.has(answerElementId)) {
        abortControllerRef.current.get(answerElementId)?.abort();
      }

      const controller = new AbortController();
      abortControllerRef.current.set(answerElementId, controller);

      const question = findQuestionForAnswer(
        elementsRef.current,
        answerElementId,
      );
      if (!question) return;

      const answerText =
        question.children?.find((c) => c.type === "answer")?.data ?? "";
      const varIds = extractVarIds(answerText);
      const currentText = getCurrentTextRef.current(answerElementId);

      if (!currentText.trim() && varIds.length === 0) {
        setHints((prev) => {
          if (!prev.has(answerElementId)) return prev;
          const next = new Map(prev);
          next.delete(answerElementId);
          return next;
        });
        abortControllerRef.current.delete(answerElementId);
        return;
      }

      const current = buildAnswerPayload(
        answerElementId,
        answerByElementIdRef.current,
        currentText,
      );
      if (!current) return;

      const params: HintAnswerPayload[] = [];
      for (const varId of varIds) {
        const paramText = getCurrentTextRef.current(varId);
        const paramPayload = buildAnswerPayload(
          varId,
          answerByElementIdRef.current,
          paramText || "",
        );
        if (paramPayload) params.push(paramPayload);
      }

      const request: HintRequest = {
        question_id: question.id,
        current,
        params: params.length > 0 ? params : undefined,
      };

      try {
        const response = await reportApi.getHint(
          hintHrefRef.current,
          request,
          controller.signal,
        );

        if (response && response.hint) {
          setHints((prev) => {
            const next = new Map(prev);
            next.set(answerElementId, {
              hint: response.hint,
              score: response.score,
            });
            return next;
          });
        } else {
          setHints((prev) => {
            if (!prev.has(answerElementId)) return prev;
            const next = new Map(prev);
            next.delete(answerElementId);
            return next;
          });
        }
      } catch (err) {
        if (err instanceof Error && err.name === "AbortError") {
          return;
        }

        if (err instanceof ApiError && err.status === 429) {
          const body = err.body as Record<string, unknown> | null;
          const detail =
            typeof body === "object" && body && typeof body.detail === "string"
              ? body.detail
              : "";

          const retryMatch = detail.match(/через (\d+) сек/);
          const retryAfter = retryMatch ? parseInt(retryMatch[1], 10) : 30;

          cooldownRef.current.set(
            answerElementId,
            Date.now() + retryAfter * 1000,
          );
        } else {
          console.error("Failed to get hint:", err);
        }
      } finally {
        if (!controller.signal.aborted) {
          abortControllerRef.current.delete(answerElementId);
        }
      }
    },
    [isOnCooldown],
  );

  const scheduleHintInternal = useCallback(
    (elementId: string) => {
      if (!enabledRef.current) return;

      if (debounceTimerRef.current.has(elementId)) {
        clearTimeout(debounceTimerRef.current.get(elementId));
      }

      cooldownRef.current.delete(elementId);

      const timer = setTimeout(() => {
        debounceTimerRef.current.delete(elementId);
        requestHint(elementId);
      }, 5000);

      debounceTimerRef.current.set(elementId, timer);
    },
    [requestHint],
  );

  const requestHintNowInternal = useCallback(
    (elementId: string) => {
      if (!enabledRef.current) return;

      if (debounceTimerRef.current.has(elementId)) {
        clearTimeout(debounceTimerRef.current.get(elementId));
        debounceTimerRef.current.delete(elementId);
      }

      requestHint(elementId);
    },
    [requestHint],
  );

  const scheduleHint = useCallback(
    (changedElementId: string) => {
      if (!enabledRef.current) return;

      scheduleHintInternal(changedElementId);

      const walk = (nodes: TemplateElementResponse[]) => {
        for (const node of nodes) {
          if (node.type === "answer" && typeof node.data === "string") {
            const dependentIds = extractVarIds(node.data);
            if (dependentIds.includes(changedElementId)) {
              scheduleHintInternal(node.id);
            }
          }
          if (node.children?.length) walk(node.children);
        }
      };
      walk(elementsRef.current);
    },
    [scheduleHintInternal],
  );

  const requestHintNow = useCallback(
    (changedElementId: string) => {
      if (!enabledRef.current) return;

      requestHintNowInternal(changedElementId);

      const walk = (nodes: TemplateElementResponse[]) => {
        for (const node of nodes) {
          if (node.type === "answer" && typeof node.data === "string") {
            const dependentIds = extractVarIds(node.data);
            if (dependentIds.includes(changedElementId)) {
              requestHintNowInternal(node.id);
            }
          }
          if (node.children?.length) walk(node.children);
        }
      };
      walk(elementsRef.current);
    },
    [requestHintNowInternal],
  );

  return {
    hints,
    scheduleHint,
    requestHintNow,
  };
}
