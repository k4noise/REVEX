import React, { useMemo } from "react";
import type { TemplateElementResponse } from "@/model/templateElement";
import type { CommonBlockProps } from "../types";
import { BlockEditor } from "./BlockEditor";
import { checkVisibility } from "../utils/visibility";

interface BlocksListProps extends Omit<CommonBlockProps, "element"> {
  elements: TemplateElementResponse[];
  parentType?: string;
  forceShowAll?: boolean;
  inContainer?: boolean;
  insideQuestion?: boolean;
  parentChildrenCount?: number;
}

export function BlocksList({
  elements,
  filterMode = "all",
  forceShowAll = false,
  ...rawRestProps
}: BlocksListProps) {
  const { element: _dirtyParentEl, ...restProps } = rawRestProps as any;

  const visibleElements = useMemo(
    () =>
      elements.filter((el) => checkVisibility(el, filterMode, forceShowAll)),
    [elements, filterMode, forceShowAll],
  );

  return (
    <div className="flex flex-col gap-2">
      {visibleElements.map((element) => (
        <BlockEditor
          key={element.id}
          {...restProps}      
          element={element}    
          filterMode={filterMode}
          forceShowAll={forceShowAll}
        />
      ))}
    </div>
  );
}
