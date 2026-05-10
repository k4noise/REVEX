import { useState, useCallback, useMemo, useEffect } from "react";

const STORAGE_KEY = "grading_queue";

interface GradingQueueState {
  templateId: string;
  reportIds: string[];
  currentIndex: number;
}

function loadQueue(): GradingQueueState | null {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

function saveQueue(state: GradingQueueState | null) {
  if (state) {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  } else {
    sessionStorage.removeItem(STORAGE_KEY);
  }
}

export function startGradingQueue(templateId: string, reportIds: string[]) {
  const state: GradingQueueState = {
    templateId,
    reportIds,
    currentIndex: 0,
  };
  saveQueue(state);
  window.dispatchEvent(new Event("storage"));
  return state;
}

export function clearGradingQueue() {
  saveQueue(null);
  window.dispatchEvent(new Event("storage"));
}

export function useGradingQueue(reportId: string) {
  const [queue, setQueue] = useState<GradingQueueState | null>(loadQueue);

  useEffect(() => {
    const syncState = () => {
      setQueue(loadQueue());
    };

    window.addEventListener("storage", syncState);
    return () => {
      window.removeEventListener("storage", syncState);
    };
  }, []);

  useEffect(() => {
    const q = loadQueue();
    if (!q) {
      if (queue !== null) setQueue(null);
      return;
    }

    const idx = q.reportIds.indexOf(reportId);
    if (idx === -1) {
      if (queue !== null) setQueue(null);
      return;
    }

    if (idx !== q.currentIndex) {
      const updated = { ...q, currentIndex: idx };
      saveQueue(updated);
      setQueue(updated);
    } else {
      if (JSON.stringify(queue) !== JSON.stringify(q)) {
        setQueue(q);
      }
    }
  }, [reportId, queue]);

  const isInQueue = queue !== null;
  const currentIndex = queue?.currentIndex ?? 0;
  const totalCount = queue?.reportIds.length ?? 0;
  const hasNext = isInQueue && currentIndex < totalCount - 1;
  const hasPrev = isInQueue && currentIndex > 0;

  const nextReportId = useMemo(
    () => (hasNext ? queue!.reportIds[currentIndex + 1] : null),
    [hasNext, queue, currentIndex],
  );

  const prevReportId = useMemo(
    () => (hasPrev ? queue!.reportIds[currentIndex - 1] : null),
    [hasPrev, queue, currentIndex],
  );

  const exitQueue = useCallback(() => {
    clearGradingQueue();
  }, []);

  const advanceQueue = useCallback(() => {
    if (!queue || !hasNext) return null;
    const nextIndex = queue.currentIndex + 1;
    const updated = { ...queue, currentIndex: nextIndex };
    saveQueue(updated);
    setQueue(updated);
    return updated.reportIds[nextIndex];
  }, [queue, hasNext]);

  return {
    isInQueue,
    currentIndex,
    totalCount,
    hasNext,
    hasPrev,
    nextReportId,
    prevReportId,
    templateId: queue?.templateId ?? null,
    exitQueue,
    advanceQueue,
  };
}
