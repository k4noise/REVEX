import { useReducer, useRef, useCallback, useEffect } from "react";
import type { TemplateElementResponse } from "../../../model/templateElement";
import {
  updateNodeInTree,
  removeNodeFromTree,
  moveNodeUp,
  moveNodeDown,
  indentNode,
  outdentNode,
  insertElementAt,
  replaceCellChildren,
} from "../utils/tree";
import {
  createTextElement,
  createQuestionWithAnswer,
  createAnswerElement,
  createImageElement,
  createContainerElement,
} from "../utils/elementFactory";
import { generateId } from "../utils/id";

type EditorState = {
  elements: TemplateElementResponse[];
  isDirty: boolean;
};

type EditorAction =
  | {
      type: "APPLY";
      updater: (prev: TemplateElementResponse[]) => TemplateElementResponse[];
    }
  | {
      type: "RESET";
      payload: TemplateElementResponse[];
    }
  | {
      type: "COMMIT_BASELINE";
    };

function reducer(state: EditorState, action: EditorAction): EditorState {
  switch (action.type) {
    case "APPLY": {
      const nextElements = action.updater(state.elements);

      if (nextElements === state.elements) {
        return state;
      }

      return {
        elements: nextElements,
        isDirty: true,
      };
    }

    case "RESET":
      return {
        elements: structuredClone(action.payload),
        isDirty: false,
      };

    case "COMMIT_BASELINE":
      return {
        ...state,
        isDirty: false,
      };

    default:
      return state;
  }
}

export function useEditorWithBaseline(
  initialElements: TemplateElementResponse[],
) {
  const baselineRef = useRef<TemplateElementResponse[]>(
    structuredClone(initialElements),
  );

  const [state, dispatch] = useReducer(reducer, {
    elements: structuredClone(initialElements),
    isDirty: false,
  });

  useEffect(() => {
    baselineRef.current = structuredClone(initialElements);
    dispatch({
      type: "RESET",
      payload: initialElements,
    });
  }, [initialElements]);

  const commitBaseline = useCallback(
    (newBaseline: TemplateElementResponse[]) => {
      baselineRef.current = structuredClone(newBaseline);
      dispatch({ type: "COMMIT_BASELINE" });
    },
    [],
  );

  const resetToBaseline = useCallback(() => {
    dispatch({
      type: "RESET",
      payload: baselineRef.current,
    });
  }, []);

  const apply = useCallback(
    (
      updater: (prev: TemplateElementResponse[]) => TemplateElementResponse[],
    ) => {
      dispatch({ type: "APPLY", updater });
    },
    [],
  );

  return {
    elements: state.elements,
    isDirty: state.isDirty,
    baselineRef,
    commitBaseline,
    resetToBaseline,

    updateElement: useCallback(
      (id: string, updates: Partial<TemplateElementResponse>) =>
        apply((prev) => updateNodeInTree(prev, id, updates)),
      [apply],
    ),

    removeElement: useCallback(
      (id: string) => apply((prev) => removeNodeFromTree(prev, id)),
      [apply],
    ),

    moveElementUp: useCallback(
      (id: string) => apply((prev) => moveNodeUp(prev, id)),
      [apply],
    ),

    moveElementDown: useCallback(
      (id: string) => apply((prev) => moveNodeDown(prev, id)),
      [apply],
    ),

    indentElement: useCallback(
      (id: string) => apply((prev) => indentNode(prev, id)),
      [apply],
    ),

    outdentElement: useCallback(
      (id: string) => apply((prev) => outdentNode(prev, id)),
      [apply],
    ),

    addText: useCallback(
      () => apply((prev) => [...prev, createTextElement(prev.length)]),
      [apply],
    ),

    addQuestionAnswer: useCallback(
      () => apply((prev) => [...prev, createQuestionWithAnswer(prev.length)]),
      [apply],
    ),

    addImageWithMediaKey: useCallback(
      (mediaKey: string, altText = "", imageUrl?: string) =>
        apply((prev) => [
          ...prev,
          createImageElement(prev.length, mediaKey, altText, imageUrl),
        ]),
      [apply],
    ),

    addGroup: useCallback(
      () => apply((prev) => [...prev, createContainerElement(prev.length)]),
      [apply],
    ),

    insertTextAt: useCallback(
      (index: number) =>
        apply((prev) => insertElementAt(prev, index, createTextElement(index))),
      [apply],
    ),

    insertQuestionAnswerAt: useCallback(
      (index: number) =>
        apply((prev) =>
          insertElementAt(prev, index, createQuestionWithAnswer(index)),
        ),
      [apply],
    ),

    insertImageAt: useCallback(
      (index: number, mediaKey: string, altText = "", imageUrl?: string) =>
        apply((prev) =>
          insertElementAt(
            prev,
            index,
            createImageElement(index, mediaKey, altText, imageUrl),
          ),
        ),
      [apply],
    ),

    insertGroupAt: useCallback(
      (index: number) =>
        apply((prev) =>
          insertElementAt(prev, index, createContainerElement(index)),
        ),
      [apply],
    ),

    convertCellToAnswer: useCallback(
      (cellId: string) => {
        apply((prev) => {
          const answer = createAnswerElement(0, cellId);
          return replaceCellChildren(prev, cellId, [answer]);
        });
      },
      [apply],
    ),

    clearCell: useCallback(
      (cellId: string) =>
        apply((prev) => {
          const textNode: TemplateElementResponse = {
            id: generateId(),
            type: "text",
            order: 0,
            parentElementId: cellId,
            data: "",
            children: [],
          };
          return replaceCellChildren(prev, cellId, [textNode]);
        }),
      [apply],
    ),
  };
}
