export type DisplayMode = "always" | "prefer";

export type ElementType =
  | "text"
  | "header"
  | "image"
  | "table"
  | "row"
  | "cell"
  | "question"
  | "answer"
  | "container";

export interface TemplateElementResponse {
  id: string;
  type: ElementType;
  order: number;
  parentElementId?: string | null;
  displayMode?: DisplayMode | null;
  data?: string | null;
  level?: number | null;
  imageUrl?: string | null;
  altText?: string | null;
  maxScore?: number | null;
  hint?: string | null;
  rowspan?: number | null;
  colspan?: number | null;
  children: TemplateElementResponse[];
}

export type PatchAction = "create" | "update" | "delete";

interface BaseElementPayload {
  id: string;
  parentElementId?: string | null;
  order: number;
  displayMode?: DisplayMode | null;
}

export interface TextElementPayload extends BaseElementPayload {
  type: "text";
  data: string;
}

export interface HeaderElementPayload extends BaseElementPayload {
  type: "header";
  data: string;
  level: number;
}

export interface ImageElementPayload extends BaseElementPayload {
  type: "image";
  mediaKey: string;
  altText?: string | null;
}

export interface QuestionElementPayload extends BaseElementPayload {
  type: "question";
  data: string;
  maxScore: number;
}

export interface AnswerElementPayload extends BaseElementPayload {
  type: "answer";
  data: string;
}

export interface ContainerElementPayload extends BaseElementPayload {
  type: "container";
}

export interface TableElementPayload extends BaseElementPayload {
  type: "table";
}

export interface RowElementPayload extends BaseElementPayload {
  type: "row";
}

export interface CellElementPayload extends BaseElementPayload {
  type: "cell";
}

export type AnyElementPayload =
  | TextElementPayload
  | HeaderElementPayload
  | ImageElementPayload
  | QuestionElementPayload
  | AnswerElementPayload
  | ContainerElementPayload
  | TableElementPayload
  | RowElementPayload
  | CellElementPayload;

export interface ElementUpdatePayload {
  id: string;
  parentElementId?: string | null;
  order?: number;
  data?: string | null;
  level?: number | null;
  mediaKey?: string | null;
  altText?: string | null;
  maxScore?: number | null;
  displayMode?: DisplayMode | null;
}

export interface ElementDeletePayload {
  id: string;
}

export interface CreateElementPatch {
  action: "create";
  payload: AnyElementPayload;
}

export interface UpdateElementPatch {
  action: "update";
  payload: ElementUpdatePayload;
}

export interface DeleteElementPatch {
  action: "delete";
  payload: ElementDeletePayload;
}

export type AnyPatch =
  | CreateElementPatch
  | UpdateElementPatch
  | DeleteElementPatch;

export interface TemplatePatchRequest {
  patches: AnyPatch[];
}
