import { useMemo } from "react";
import type { CommonBlockProps } from "../types";
import { isTableStructural } from "../utils/styles";

export function useBlockPermissions(props: CommonBlockProps) {
  const {
    element,
    isReportMode,
    isReadOnly,
    parentType,
    insideQuestion,
    parentChildrenCount,
  } = props;

  return useMemo(() => {
    const inTableCell = parentType === "cell";
    const isStructural = isTableStructural(element.type);

    const isQuestion = element.type === "question";

    const canShowMenu =
      !isReportMode &&
      !isReadOnly &&
      !inTableCell &&
      !isStructural &&
      !insideQuestion;

    const canDeleteBlock =
      canShowMenu &&
      !(parentType === "container" && (parentChildrenCount ?? 0) === 1);

    if (isQuestion) {
      return {
        canShowMenu: canShowMenu,
        canMove: canShowMenu,
        canDeleteBlock: canDeleteBlock,
        canEditPriority: false,
        canIndentOutdent: false,
      };
    }

    return {
      canShowMenu: canShowMenu,
      canMove: canShowMenu,
      canEditPriority: canShowMenu && element.type !== "answer",
      canIndentOutdent: canShowMenu && element.type !== "answer",
      canDeleteBlock: canDeleteBlock,
    };
  }, [
    element,
    isReportMode,
    isReadOnly,
    parentType,
    insideQuestion,
    parentChildrenCount,
  ]);
}
