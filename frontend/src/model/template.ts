import type { HalLink } from "../model/common";
import type {
  TemplateElementResponse,
  TemplatePatchRequest,
} from "./templateElement";
import type { MinimalReport } from "./report";

export interface TemplateCollectionLinks {
  self?: HalLink;
  add_template?: HalLink;
  publish_many?: HalLink;
  delete_many?: HalLink;
}

export interface TemplateSummaryLinks {
  self?: HalLink;
  get_template?: HalLink;
  delete?: HalLink;
  publish?: HalLink;
  get_reports?: HalLink;
  create_report?: HalLink;
}

export interface TemplateDetailLinks {
  self?: HalLink;
  update?: HalLink;
  publish?: HalLink;
  delete?: HalLink;
  upload_image?: HalLink;
  all?: HalLink;
  get_reports?: HalLink;
  create_report?: HalLink;
}

export interface TemplateCreationLinks {
  self?: HalLink;
  get_template?: HalLink;
}

export interface TemplateCreationResponse {
  id: string;
  _links: TemplateCreationLinks;
}

export interface TemplateDetailResponse {
  id: string;
  name: string;
  maxScore: number;
  isDraft: boolean;
  _embedded: {
    elements: TemplateElementResponse[];
  };
  _links: TemplateDetailLinks;
}

export interface TemplateCourseSummary {
  id: string;
  name: string;
  isDraft: boolean;
  _embedded: {
    reports: MinimalReport[];
  };
  _links: TemplateSummaryLinks;
}

export interface TemplateCourseCollection {
  courseName: string;
  _embedded: {
    templates: TemplateCourseSummary[];
  };
  _links: TemplateCollectionLinks;
}

export interface TemplateUpdateRequest {
  name?: string;
  maxScore?: number;
  elements?: TemplatePatchRequest;
}

export interface TemplateManyRequest {
  ids: string[];
}

export type ImageUploadResponse = {
  mediaKey: string;
  imageUrl?: string | null;
  url?: string | null;
  key?: string | null;
};
