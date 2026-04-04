import type {
  TemplateElementResponse,
  TemplatePatchRequest,
} from "./templateElement";

export interface HalLink {
  href: string;
  method?: string;
}

export interface CollectionHalLinks {
  self?: HalLink;
  add_template?: HalLink;
}

export interface TemplateHalLinks {
  self?: HalLink;
  update?: HalLink;
  publish?: HalLink;
  delete?: HalLink;
  get_template?: HalLink;
  publish_many?: HalLink;
  delete_many?: HalLink;
  upload_image?: HalLink;
  all?: HalLink;
}

export interface TemplateCreationResponse {
  id: string;
  _links: TemplateHalLinks;
}

export interface TemplateDetailResponse {
  id: string;
  name: string;
  maxScore: number;
  isDraft: boolean;
  _embedded: {
    elements: TemplateElementResponse[];
  };
  _links: TemplateHalLinks;
}

export interface TemplateCourseSummary {
  id: string;
  name: string;
  isDraft: boolean;
  _links: TemplateHalLinks;
}

export interface TemplateCourseCollection {
  courseName: string;
  _embedded: {
    templates: TemplateCourseSummary[];
  };
  _links: CollectionHalLinks;
}

export interface TemplateUpdateRequest {
  name?: string;
  maxScore?: number;
  elements?: TemplatePatchRequest;
}

export type ImageUploadResponse = {
  mediaKey: string;
};
