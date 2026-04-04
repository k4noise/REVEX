import React, { memo } from "react";
import type { CommonBlockProps } from "../types";
import { BlockWrapper } from "./common/BlockWrapper";
import { checkVisibility } from "../utils/visibility";
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
  const { element, filterMode = "all", forceShowAll = false } = props;

  if (!checkVisibility(element, filterMode, forceShowAll)) {
    return null;
  }

  if (element.type === "row" || element.type === "cell") {
    return null;
  }

  const Component =
    blockComponents[element.type as keyof typeof blockComponents];

  if (!Component) {
    console.warn(`Unknown block type: ${element.type}`);
    return null;
  }

  if (
    element.type === "question" ||
    element.type === "container" ||
    element.type === "table"
  ) {
    return (
      <BlockWrapper {...props}>
        <Component {...props} />
      </BlockWrapper>
    );
  }

  return (
    <BlockWrapper {...props}>
      <Component {...props} />
    </BlockWrapper>
  );
}

export const BlockEditor = memo(BlockEditorComponent, (prev, next) => {
  if (prev.element !== next.element) return false;

  if (prev.filterMode !== next.filterMode) return false;
  if (prev.isReadOnly !== next.isReadOnly) return false;
  if (prev.forceShowAll !== next.forceShowAll) return false;
  if (prev.inContainer !== next.inContainer) return false;
  if (prev.insideQuestion !== next.insideQuestion) return false;

  if (prev.element.type === "answer") {
    const prevScore = prev.globalScoring?.byAnswerId?.[prev.element.id];
    const nextScore = next.globalScoring?.byAnswerId?.[next.element.id];

    if (prevScore?.points !== nextScore?.points) return false;
    if (prevScore?.weight !== nextScore?.weight) return false;

    if (prev.availableQuestions?.length !== next.availableQuestions?.length) {
      return false;
    }
  }

  return true;
});
