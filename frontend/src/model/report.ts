import type { HalLink } from "../model/common";
import type { TemplateElementResponse } from "../model/templateElement";

export type ReportStatus = "created" | "saved" | "submitted" | "graded";

export interface ReportHalLinks {
  self?: HalLink;
  save?: HalLink;
  submit?: HalLink;
  unsubmit?: HalLink;
  grade?: HalLink;
  get_hint?: HalLink;
}

export interface AnswerData {
  id: string;
  elementId: string;
  score: number | null;
  data: Record<string, unknown> | null;
  comment?: string | null;
}

export interface PreGradeError {
  type: string;
  expected: string;
  actual?: string | null;
}

export interface PreGradeResult {
  score: number;
  errors: PreGradeError[];
  needsManualReview?: boolean;
  type?: string;
  explanation?: string;
}

export interface PreGradedAnswerData extends AnswerData {
  preGrade?: PreGradeResult | null;
}

export interface WorkTemplateStructure {
  id: string;
  name: string;
  maxScore: number;
  isDraft?: boolean;
  elements: TemplateElementResponse[];
}

export interface FullWorkResponse {
  id: string;
  status: ReportStatus;
  graderName?: string | null;
  score?: number | null;
  template: WorkTemplateStructure;
  _links: ReportHalLinks;
  _embedded?: {
    answers?: (AnswerData | PreGradedAnswerData)[];
  };
}

export interface ReportCreationResponse {
  id: string;
  _links: {
    self?: HalLink;
  };
}

export interface MinimalReportLinks {
  self?: HalLink;
  create_report?: HalLink;
}

export interface MinimalReport {
  createdAt: string;
  reportId: string;
  templateId: string;
  status: ReportStatus;
  authorName?: string;
  score?: number | null;
  _links?: MinimalReportLinks;
}

export interface AllReportsByUserResponse {
  templateName: string;
  templateId: string;
  maxScore: number;
  reports: MinimalReport[];
}

export interface AllReportsResponse {
  templateName: string;
  templateId: string;
  maxScore: number;
  reports?: {
    owned: MinimalReport[];
    toGrade: MinimalReport[];
  };
  _links: {
    self?: HalLink;
  };
}

export interface UpdateAnswerDataPayload {
  id: string;
  data?: Record<string, unknown> | null;
}

export interface UpdateAnswerScorePayload {
  id: string;
  score: number;
  comment?: string | null;
}

export interface HintAnswerPayload {
  id: string;
  element_id: string;
  score: number | null;
  data: Record<string, unknown> | null;
}

export interface HintRequest {
  question_id: string;
  current: HintAnswerPayload;
  params?: HintAnswerPayload[];
}

export interface HintResponse {
  hint: string;
  score?: number;
}
