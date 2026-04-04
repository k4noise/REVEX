import React from "react";
import type { CommonBlockProps } from "../../types";
import { cx } from "../../utils/styles";
import { BlocksList } from "../BlocksList";

export function ContainerBlock(props: CommonBlockProps) {
  const {
    element,
    forceShowAll = true,
    inContainer = true,
    ...restProps
  } = props;

  if (!element.children || element.children.length === 0) {
    if (props.isReadOnly) return null;

    return (
      <div className="my-4 rounded-xl border border-zinc-200 p-5 dark:border-zinc-800">
        <div className="text-sm text-zinc-400 py-3">
          Пустая группа. Добавь блоки и сделай "→ Внутрь группы".
        </div>
      </div>
    );
  }

  return (
    <div className="my-4 rounded-xl border border-zinc-200 p-5 dark:border-zinc-800">
      <div className="space-y-3">
        <BlocksList
          {...restProps} 
          elements={element.children}
          parentType="container"
          forceShowAll={forceShowAll}
          inContainer={inContainer}
          parentChildrenCount={element.children.length}
        />
      </div>
    </div>
  );
}
