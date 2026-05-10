import { memo } from "react";
import type { CommonBlockProps } from "../../types";
import { BlocksList } from "../BlocksList";

export const ContainerBlock = memo(function ContainerBlock(
  props: CommonBlockProps,
) {
  const { element, isReadOnly, ...restProps } = props;

  if (!element.children || element.children.length === 0) {
    if (isReadOnly) return null;

    return (
      <div className="my-6 rounded-xl bg-zinc-50 p-5 dark:bg-zinc-900/30">
        <div className="text-sm text-zinc-400 py-3">
          Пустая группа. Добавьте блоки и переместите сюда через меню.
        </div>
      </div>
    );
  }

  return (
    <div className="my-6 rounded-xl bg-zinc-50/80 p-5 dark:bg-zinc-900/20">
      <div className="space-y-3">
        <BlocksList
          {...restProps}
          isReadOnly={isReadOnly}
          elements={element.children}
          parentType="container"
          inContainer={true}
          parentChildrenCount={element.children.length}
        />
      </div>
    </div>
  );
});
