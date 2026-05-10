import type { TemplateElementResponse } from "../../../model/templateElement";
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

  const walk = (
    nodes: TemplateElementResponse[],
    inheritedQuestionWeight: number | null = null,
  ) => {
    for (const node of nodes) {
      const nextInheritedQuestionWeight =
        node.type === "question"
          ? normalizeWeight(node.maxScore)
          : inheritedQuestionWeight;

      if (node.type === "answer") {
        const weightSource = node.maxScore ?? inheritedQuestionWeight ?? 1;
        const weight = normalizeWeight(weightSource);
        answers.push({ id: node.id, weight });
      }

      if (node.children?.length) {
        walk(node.children, nextInheritedQuestionWeight);
      }
    }
  };

  walk(elements);

  if (answers.length === 0) {
    return {
      templateTotalPoints: totalPoints,
      sumAnswerWeights: 0,
      byAnswerId: {},
    };
  }

  const sumWeights = answers.reduce((acc, a) => acc + a.weight, 0);

  if (sumWeights <= 0) {
    return {
      templateTotalPoints: totalPoints,
      sumAnswerWeights: 0,
      byAnswerId: {},
    };
  }

  const byAnswerId: GlobalScoring["byAnswerId"] = {};
  let pointsAccumulator = 0;

  for (let i = 0; i < answers.length; i++) {
    const answer = answers[i];
    let points = 0;

    if (i < answers.length - 1) {
      const rawPoints = (totalPoints * answer.weight) / sumWeights;
      points = floorTo2(rawPoints);
      pointsAccumulator += points;
    } else {
      const remainingPoints = totalPoints - pointsAccumulator;
      points = floorTo2(remainingPoints);
    }

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
