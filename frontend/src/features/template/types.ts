import type {
  TemplateElementResponse,
  ElementType,
} from "../../model/templateElement";
import type { PreGradeResult } from "../../model/report";
import type { QuestionGroups } from "./hooks/useQuestions";
import type { HintEntry } from "./hooks/useHints";

export type FilterMode = "all" | "important" | "key";

export type GradingStatus = "correct" | "partial" | "incorrect" | "ungraded";

export interface QuestionReference {
  id: string;
  marker: string;
  text: string;
}

export interface GlobalScoring {
  templateTotalPoints: number;
  sumAnswerWeights: number;
  byAnswerId: Record<
    string,
    {
      answerId: string;
      weight: number;
      points: number;
    }
  >;
}

export interface AnswerGradingInfo {
  grade: number | null;
  maxPoints: number;
  earnedPoints: number;
  preGrade?: PreGradeResult | null;
  comment: string;
  status: GradingStatus;
  originalText?: string;
}

export function getGradingStatus(grade: number | null): GradingStatus {
  if (grade === null) return "ungraded";
  if (grade >= 1) return "correct";
  if (grade <= 0) return "incorrect";
  return "partial";
}

export function getQuestionGradingStatus(
  element: TemplateElementResponse,
  answerGrading?: Map<string, AnswerGradingInfo>,
): GradingStatus {
  if (!answerGrading) return "ungraded";

  const statuses: GradingStatus[] = [];

  const collect = (nodes: TemplateElementResponse[]) => {
    for (const node of nodes) {
      if (node.type === "answer") {
        const info = answerGrading.get(node.id);
        statuses.push(info?.status ?? "ungraded");
      }
      if (node.children?.length) collect(node.children);
    }
  };

  collect(element.children ?? []);

  if (statuses.length === 0) return "ungraded";
  if (statuses.every((s) => s === "correct")) return "correct";
  if (statuses.every((s) => s === "incorrect")) return "incorrect";
  if (statuses.every((s) => s === "ungraded")) return "ungraded";

  return "partial";
}

export const gradingBorderColor: Record<GradingStatus, string> = {
  correct: "border-emerald-300 dark:border-emerald-700",
  partial: "border-amber-300 dark:border-amber-700",
  incorrect: "border-red-300 dark:border-red-700",
  ungraded: "border-blue-200 dark:border-blue-900/50",
};

export const gradingBgTint: Record<GradingStatus, string> = {
  correct: "bg-emerald-50/40 dark:bg-emerald-900/10",
  partial: "bg-amber-50/40 dark:bg-amber-900/10",
  incorrect: "bg-red-50/40 dark:bg-red-900/10",
  ungraded: "bg-blue-50/40 dark:bg-blue-900/10",
};

export interface CommonBlockProps {
  element: TemplateElementResponse;
  updateElement: (
    id: string,
    updates: Partial<TemplateElementResponse>,
  ) => void;
  removeElement: (id: string) => void;
  moveUp: (id: string) => void;
  moveDown: (id: string) => void;
  indent: (id: string) => void;
  outdent: (id: string) => void;
  isReadOnly?: boolean;
  filterMode?: FilterMode;
  availableQuestions?: QuestionGroups;
  parentType?: ElementType;
  forceShowAll?: boolean;
  inContainer?: boolean;
  insideQuestion?: boolean;
  parentChildrenCount?: number;
  globalScoring?: GlobalScoring | null;
  isReportMode?: boolean;
  isGradingMode?: boolean;
  answerGrading?: Map<string, AnswerGradingInfo>;
  onAnswerGradeChange?: (elementId: string, grade: number) => void;
  onAnswerCommentChange?: (elementId: string, comment: string) => void;
  convertCellToAnswer?: (cellId: string) => void;
  clearCell?: (cellId: string) => void;
  hints?: Map<string, HintEntry>;
  onAnswerBlur?: (elementId: string) => void;
  onAnswerInput?: (elementId: string) => void;
}
