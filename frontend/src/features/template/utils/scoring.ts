import type { TemplateElementResponse } from "@/model/templateElement";
import type { GlobalScoring } from "../types";
import { normalizeWeight } from "./validation";

export function floorTo2(num: number): number {
  return Math.floor((num + 1e-9) * 100) / 100;
}

export function formatPoints2(num: number): string {
  return num.toFixed(2);
}

export function calculateGlobalScoring(
  elements: TemplateElementResponse[],
  totalPoints: number,
): GlobalScoring {
  const answers: Array<{ id: string; weight: number }> = [];

  const walk = (nodes: TemplateElementResponse[]) => {
    for (const node of nodes) {
      if (node.type === "answer") {
        const weight = normalizeWeight(node.maxScore);
        answers.push({ id: node.id, weight });
      }
      if (node.children?.length) {
        walk(node.children);
      }
    }
  };

  walk(elements);

  let sumWeights = answers.reduce((acc, answer) => acc + answer.weight, 0);

  if (sumWeights <= 0) {
    sumWeights = Math.max(1, answers.length);
    for (const answer of answers) {
      answer.weight = 1;
    }
  }

  const byAnswerId: GlobalScoring["byAnswerId"] = {};

  for (const answer of answers) {
    const rawPoints =
      sumWeights > 0 ? (totalPoints * answer.weight) / sumWeights : 0;
    const points = floorTo2(rawPoints);

    byAnswerId[answer.id] = {
      answerId: answer.id,
      weight: answer.weight,
      points,
    };
  }

  return {
    templateTotalPoints: totalPoints,
    sumAnswerWeights: sumWeights,
    byAnswerId,
  };
}
