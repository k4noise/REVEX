import { useMemo } from "react";
import type { TemplateElementResponse } from "@/model/templateElement";
import type { QuestionReference } from "../types";

export function useQuestions(
  elements: TemplateElementResponse[],
): QuestionReference[] {
  return useMemo(() => {
    const questions: QuestionReference[] = [];

    const traverse = (nodes: TemplateElementResponse[]) => {
      for (const node of nodes) {
        if (node.type === "question") {
          questions.push({
            id: node.id,
            marker: node.marker || "",
            text: node.data || "Пустой вопрос",
          });
        }
        if (node.children) {
          traverse(node.children);
        }
      }
    };

    traverse(elements);
    return questions;
  }, [elements]);
}
