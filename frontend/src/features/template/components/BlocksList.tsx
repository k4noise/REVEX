import { memo } from "react";
import type {
  TemplateElementResponse,
  ElementType,
} from "../../../model/templateElement";
import type { FilterMode, GlobalScoring, AnswerGradingInfo } from "../types";
import type { QuestionGroups } from "../hooks/useQuestions";
import type { HintEntry } from "../hooks/useHints";
import { BlockEditor } from "./BlockEditor";
import { InsertDivider } from "./common/InsertDivider";

interface BlocksListProps {
  elements: TemplateElementResponse[];
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
  forceShowAll?: boolean;
  parentType?: ElementType;
  inContainer?: boolean;
  insideQuestion?: boolean;
  parentChildrenCount?: number;
  availableQuestions?: QuestionGroups;
  globalScoring?: GlobalScoring | null;
  isReportMode?: boolean;
  isGradingMode?: boolean;
  answerGrading?: Map<string, AnswerGradingInfo>;
  onAnswerGradeChange?: (elementId: string, grade: number) => void;
  onAnswerCommentChange?: (elementId: string, comment: string) => void;
  convertCellToAnswer?: (cellId: string) => void;
  clearCell?: (cellId: string) => void;
  insertTextAt?: (index: number) => void;
  insertQuestionAnswerAt?: (index: number) => void;
  insertGroupAt?: (index: number) => void;
  insertImageAt?: (index: number) => void;
  hints?: Map<string, HintEntry>;
  onAnswerBlur?: (elementId: string) => void;
  onAnswerInput?: (elementId: string) => void;
}

export const BlocksList = memo(function BlocksList({
  elements,
  filterMode = "all",
  forceShowAll = false,
  insertTextAt,
  insertQuestionAnswerAt,
  insertGroupAt,
  insertImageAt,
  isReadOnly,
  isReportMode,
  isGradingMode,
  parentType,
  ...restProps
}: BlocksListProps) {
  const canInsert =
    !isReadOnly &&
    !isReportMode &&
    !isGradingMode &&
    !parentType &&
    !!insertTextAt;

  return (
    <div className="flex flex-col gap-2">
      {elements.map((element, index) => (
        <div key={element.id}>
          {canInsert && index === 0 && (
            <InsertDivider
              onInsertText={() => insertTextAt!(index)}
              onInsertQA={() => insertQuestionAnswerAt?.(index)}
              onInsertGroup={() => insertGroupAt?.(index)}
              onInsertImage={
                insertImageAt ? () => insertImageAt(index) : undefined
              }
            />
          )}

          <BlockEditor
            element={element}
            filterMode={filterMode}
            forceShowAll={forceShowAll}
            isReadOnly={isReadOnly}
            isReportMode={isReportMode}
            isGradingMode={isGradingMode}
            parentType={parentType}
            {...restProps}
          />

          {canInsert && (
            <InsertDivider
              onInsertText={() => insertTextAt!(index + 1)}
              onInsertQA={() => insertQuestionAnswerAt?.(index + 1)}
              onInsertGroup={() => insertGroupAt?.(index + 1)}
              onInsertImage={
                insertImageAt ? () => insertImageAt(index + 1) : undefined
              }
            />
          )}
        </div>
      ))}

      {canInsert && elements.length === 0 && (
        <InsertDivider
          onInsertText={() => insertTextAt!(0)}
          onInsertQA={() => insertQuestionAnswerAt?.(0)}
          onInsertGroup={() => insertGroupAt?.(0)}
          onInsertImage={insertImageAt ? () => insertImageAt(0) : undefined}
        />
      )}
    </div>
  );
});
