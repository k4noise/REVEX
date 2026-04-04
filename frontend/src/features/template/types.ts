import type {
  TemplateElementResponse,
  ElementType,
} from "@/model/templateElement";

export type FilterMode = "all" | "important" | "key";

export interface QuestionReference {
  id: string;
  marker: string;
  text: string;
}

export interface GlobalScoring {
  templateTotalPoints: number;
  sumAnswerWeights: number;
  byAnswerId: Record<
    string,
    {
      answerId: string;
      weight: number;
      points: number;
    }
  >;
}

export interface CommonBlockProps {
  element: TemplateElementResponse;
  updateElement: (
    id: string,
    updates: Partial<TemplateElementResponse>,
  ) => void;
  removeElement: (id: string) => void;
  moveUp: (id: string) => void;
  moveDown: (id: string) => void;
  indent: (id: string) => void;
  outdent: (id: string) => void;
  isReadOnly?: boolean;
  filterMode?: FilterMode;
  availableQuestions?: QuestionReference[];
  parentType?: ElementType;
  forceShowAll?: boolean;
  inContainer?: boolean;
  insideQuestion?: boolean;
  parentChildrenCount?: number;
  globalScoring?: GlobalScoring | null;
}
