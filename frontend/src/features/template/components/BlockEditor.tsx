import { memo } from "react";
import type { CommonBlockProps } from "../types";
import { BlockWrapper } from "./common/BlockWrapper";
import { HeaderBlock } from "./blocks/HeaderBlock";
import { TextBlock } from "./blocks/TextBlock";
import { QuestionBlock } from "./blocks/QuestionBlock";
import { AnswerBlock } from "./blocks/AnswerBlock";
import { ImageBlock } from "./blocks/ImageBlock";
import { ContainerBlock } from "./blocks/ContainerBlock";
import { TableBlock } from "./blocks/TableBlock";

const blockComponents = {
  header: HeaderBlock,
  text: TextBlock,
  question: QuestionBlock,
  answer: AnswerBlock,
  image: ImageBlock,
  container: ContainerBlock,
  table: TableBlock,
} as const;

function BlockEditorComponent(props: CommonBlockProps) {
  const { element } = props;
  if (element.type === "row" || element.type === "cell") return null;

  const Component =
    blockComponents[element.type as keyof typeof blockComponents];
  if (!Component) {
    console.warn(`Unknown block type: ${element.type}`);
    return null;
  }

  return (
    <BlockWrapper {...props}>
      <Component {...props} />
    </BlockWrapper>
  );
}

function arePropsEqual(
  prev: CommonBlockProps,
  next: CommonBlockProps,
): boolean {
  if (prev.element !== next.element) return false;
  if (prev.isReadOnly !== next.isReadOnly) return false;
  if (prev.inContainer !== next.inContainer) return false;
  if (prev.insideQuestion !== next.insideQuestion) return false;
  if (prev.parentType !== next.parentType) return false;
  if (prev.parentChildrenCount !== next.parentChildrenCount) return false;
  if (prev.isReportMode !== next.isReportMode) return false;
  if (prev.isGradingMode !== next.isGradingMode) return false;

  if (prev.element.type === "answer") {
    if (prev.globalScoring !== next.globalScoring) return false;

    const prevGrading = prev.answerGrading?.get(prev.element.id);
    const nextGrading = next.answerGrading?.get(next.element.id);
    if (prevGrading?.grade !== nextGrading?.grade) return false;
    if (prevGrading?.comment !== nextGrading?.comment) return false;
    if (prevGrading?.status !== nextGrading?.status) return false;

    const prevHint = prev.hints?.get(prev.element.id);
    const nextHint = next.hints?.get(next.element.id);
    if (prevHint?.hint !== nextHint?.hint) return false;
    if (prevHint?.score !== nextHint?.score) return false;
  }

  if (prev.element.type === "question") {
    if (prev.answerGrading !== next.answerGrading) return false;
    if (prev.availableQuestions !== next.availableQuestions) return false;
    if (prev.hints !== next.hints) return false;
  }

  if (prev.element.type === "container" || prev.element.type === "table") {
    if (prev.hints !== next.hints) return false;
    if (prev.answerGrading !== next.answerGrading) return false;
  }

  return true;
}

export const BlockEditor = memo(BlockEditorComponent, arePropsEqual);
