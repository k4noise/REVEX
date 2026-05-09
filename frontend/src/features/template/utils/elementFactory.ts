import type { TemplateElementResponse } from "../../../model/templateElement";
import { generateId } from "./id";

export function createTextElement(order: number): TemplateElementResponse {
  return {
    id: generateId(),
    type: "text",
    order,
    data: "",
    children: [],
  };
}

export function createQuestionWithAnswer(
  order: number,
): TemplateElementResponse {
  const questionId = generateId();
  return {
    id: questionId,
    type: "question",
    order,
    data: "",
    maxScore: 1,
    children: [
      {
        id: generateId(),
        type: "answer",
        order: 0,
        parentElementId: questionId,
        data: "",
        maxScore: 1,
        children: [],
      },
    ],
  };
}

export function createAnswerElement(
  order: number,
  parentId: string,
): TemplateElementResponse {
  return {
    id: generateId(),
    type: "answer",
    order,
    parentElementId: parentId,
    data: "",
    maxScore: 1,
    children: [],
  };
}

export function createImageElement(
  order: number,
  mediaKey: string,
  altText = "",
  imageUrl?: string,
): TemplateElementResponse {
  return {
    id: generateId(),
    type: "image",
    order,
    mediaKey,
    imageUrl,
    altText,
    children: [],
  };
}

export function createContainerElement(order: number): TemplateElementResponse {
  return {
    id: generateId(),
    type: "container",
    order,
    children: [],
  };
}
