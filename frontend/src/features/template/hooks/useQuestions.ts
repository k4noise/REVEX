import { useMemo } from "react";
import type { TemplateElementResponse } from "../../../model/templateElement";
import type { QuestionReference } from "../types";

export interface QuestionGroups {
  questions: QuestionReference[];
  tableCells: QuestionReference[];
  all: QuestionReference[];
}

function findDeep(
  node: TemplateElementResponse,
  type: string,
): TemplateElementResponse | null {
  if (node.type === type) return node;
  for (const child of node.children ?? []) {
    const found = findDeep(child, type);
    if (found) return found;
  }
  return null;
}

function cellText(cell: TemplateElementResponse | undefined): string {
  if (!cell) return "";
  const texts: string[] = [];
  const walk = (n: TemplateElementResponse) => {
    if (n.type === "answer") return;
    if (n.data?.trim()) texts.push(n.data.trim());
    for (const child of n.children ?? []) walk(child);
  };
  walk(cell);
  return texts.join(" ");
}

function collectTableCells(
  table: TemplateElementResponse,
  refs: QuestionReference[],
  seen: Set<string>,
) {
  const rows = table.children ?? [];
  if (rows.length === 0) return;

  const headerRow = rows[0];
  const headerTexts = (headerRow?.children ?? []).map(
    (cell) => cellText(cell) || "",
  );

  for (let rIdx = 0; rIdx < rows.length; rIdx++) {
    const row = rows[rIdx];
    if (row.type !== "row") continue;

    const cells = row.children ?? [];
    const firstCellContainsAnswer = !!findDeep(cells[0], "answer");
    const rowLabel = firstCellContainsAnswer
      ? `Строка ${rIdx + 1}`
      : cellText(cells[0]) || `Строка ${rIdx + 1}`;

    for (let cIdx = 0; cIdx < cells.length; cIdx++) {
      const cell = cells[cIdx];
      if (cell.type !== "cell") continue;

      const colLabel = headerTexts[cIdx] || `Столбец ${cIdx + 1}`;

      const answer = findDeep(cell, "answer");
      if (answer && !seen.has(answer.id)) {
        seen.add(answer.id);
        refs.push({
          id: answer.id,
          marker: "",
          text: `${rowLabel} / ${colLabel}`,
        });
        continue;
      }

      const textNode = findDeep(cell, "text");
      if (textNode && textNode.data?.trim() && !seen.has(textNode.id)) {
        seen.add(textNode.id);
        refs.push({
          id: textNode.id,
          marker: "",
          text: `${rowLabel} / ${colLabel} = ${textNode.data.trim()}`,
        });
      }
    }
  }
}

function traverse(
  nodes: TemplateElementResponse[],
  questions: QuestionReference[],
  tableCells: QuestionReference[],
  seen: Set<string>,
  inContainer: boolean,
) {
  for (const node of nodes) {
    if (node.type === "question" && !seen.has(node.id)) {
      seen.add(node.id);
      questions.push({
        id: node.id,
        marker: node.marker ?? "",
        text: node.data || "Пустой вопрос",
      });
    }

    const isContainer = node.type === "container";

    if (node.type === "table" && inContainer) {
      collectTableCells(node, tableCells, seen);
    }

    if (node.children?.length) {
      traverse(
        node.children,
        questions,
        tableCells,
        seen,
        inContainer || isContainer,
      );
    }
  }
}

export function useQuestions(
  elements: TemplateElementResponse[],
): QuestionGroups {
  return useMemo(() => {
    const questions: QuestionReference[] = [];
    const tableCells: QuestionReference[] = [];
    const seen = new Set<string>();
    traverse(elements, questions, tableCells, seen, false);
    return {
      questions,
      tableCells,
      all: [...questions, ...tableCells],
    };
  }, [elements]);
}
