import { useMemo } from "react";
import type { TemplateElementResponse } from "../../../model/templateElement";
import type { GlobalScoring } from "../types";
import { calculateGlobalScoring } from "../utils/scoring";

export function useGlobalScoring(
  elements: TemplateElementResponse[],
  totalPoints: number,
): GlobalScoring {
  return useMemo(
    () => calculateGlobalScoring(elements, totalPoints),
    [elements, totalPoints],
  );
}
