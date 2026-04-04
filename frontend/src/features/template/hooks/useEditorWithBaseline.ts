import { useState, useRef, useCallback, useMemo } from "react";
import type { TemplateElementResponse } from "@/model/templateElement";

export function useEditorWithBaseline(
  initialElements: TemplateElementResponse[],
) {
  const [elements, setElements] =
    useState<TemplateElementResponse[]>(initialElements);
  const baselineRef = useRef<TemplateElementResponse[]>(initialElements);

  const isDirty = useMemo(() => {
    return JSON.stringify(elements) !== JSON.stringify(baselineRef.current);
  }, [elements]);

  const commitBaseline = useCallback(
    (newBaseline: TemplateElementResponse[]) => {
      baselineRef.current = JSON.parse(JSON.stringify(newBaseline));
    },
    [],
  );

  const resetToBaseline = useCallback(() => {
    setElements(JSON.parse(JSON.stringify(baselineRef.current)));
  }, []);

  const updateElement = useCallback(
    (id: string, updates: Partial<TemplateElementResponse>) => {
      setElements((prev) => {
        const updateNode = (
          nodes: TemplateElementResponse[],
        ): TemplateElementResponse[] => {
          let hasChanges = false;

          const newNodes = nodes.map((node) => {
            if (node.id === id) {
              hasChanges = true;
              return { ...node, ...updates };
            }
            if (node.children) {
              const updatedChildren = updateNode(node.children);
              if (updatedChildren !== node.children) {
                hasChanges = true;
                return { ...node, children: updatedChildren };
              }
            }
            return node;
          });

          return hasChanges ? newNodes : nodes;
        };

        return updateNode(prev);
      });
    },
    [],
  );

  const removeElement = useCallback((id: string) => {
    setElements((prev) => {
      const removeNode = (
        nodes: TemplateElementResponse[],
      ): TemplateElementResponse[] => {
        const filtered = nodes.filter((node) => node.id !== id);

        if (filtered.length !== nodes.length) {
          return filtered;
        }

        let hasChanges = false;
        const newNodes = nodes.map((node) => {
          if (node.children) {
            const updatedChildren = removeNode(node.children);
            if (updatedChildren !== node.children) {
              hasChanges = true;
              return { ...node, children: updatedChildren };
            }
          }
          return node;
        });

        return hasChanges ? newNodes : nodes;
      };

      return removeNode(prev);
    });
  }, []);

  const moveElementUp = useCallback((id: string) => {
    setElements((prev) => {
      const moveUp = (
        nodes: TemplateElementResponse[],
      ): TemplateElementResponse[] => {
        const index = nodes.findIndex((node) => node.id === id);
        if (index > 0) {
          const newNodes = [...nodes];
          [newNodes[index - 1], newNodes[index]] = [
            newNodes[index],
            newNodes[index - 1],
          ];
          newNodes[index - 1] = { ...newNodes[index - 1], order: index - 1 };
          newNodes[index] = { ...newNodes[index], order: index };
          return newNodes;
        }

        let hasChanges = false;
        const newNodes = nodes.map((node) => {
          if (node.children && node.children.length > 0) {
            const updatedChildren = moveUp(node.children);
            if (updatedChildren !== node.children) {
              hasChanges = true;
              return { ...node, children: updatedChildren };
            }
          }
          return node;
        });

        return hasChanges ? newNodes : nodes;
      };
      return moveUp(prev);
    });
  }, []);

  const moveElementDown = useCallback((id: string) => {
    setElements((prev) => {
      const moveDown = (
        nodes: TemplateElementResponse[],
      ): TemplateElementResponse[] => {
        const index = nodes.findIndex((node) => node.id === id);
        if (index >= 0 && index < nodes.length - 1) {
          const newNodes = [...nodes];
          [newNodes[index], newNodes[index + 1]] = [
            newNodes[index + 1],
            newNodes[index],
          ];
          newNodes[index] = { ...newNodes[index], order: index };
          newNodes[index + 1] = { ...newNodes[index + 1], order: index + 1 };
          return newNodes;
        }

        let hasChanges = false;
        const newNodes = nodes.map((node) => {
          if (node.children && node.children.length > 0) {
            const updatedChildren = moveDown(node.children);
            if (updatedChildren !== node.children) {
              hasChanges = true;
              return { ...node, children: updatedChildren };
            }
          }
          return node;
        });

        return hasChanges ? newNodes : nodes;
      };
      return moveDown(prev);
    });
  }, []);

  const indentElement = useCallback((id: string) => {
    setElements((prev) => {
      const indent = (
        nodes: TemplateElementResponse[],
      ): TemplateElementResponse[] => {
        for (let i = 0; i < nodes.length; i++) {
          if (nodes[i].id === id && i > 0) {
            const element = nodes[i];
            const newTarget = nodes[i - 1];
            const newNodes = [...nodes];

            newNodes.splice(i, 1);

            newNodes[i - 1] = {
              ...newTarget,
              children: [
                ...(newTarget.children || []),
                { ...element, parentElementId: newTarget.id },
              ],
            };

            return newNodes;
          }

          const currentChildren = nodes[i].children;
          if (currentChildren && currentChildren.length > 0) {
            const updatedChildren = indent(currentChildren);
            if (updatedChildren !== currentChildren) {
              const newNodes = [...nodes];
              newNodes[i] = { ...nodes[i], children: updatedChildren };
              return newNodes;
            }
          }
        }
        return nodes;
      };

      return indent(prev);
    });
  }, []);

  const outdentElement = useCallback((id: string) => {
    setElements((prev) => {
      const outdent = (
        nodes: TemplateElementResponse[],
        parentId: string | null = null,
      ): TemplateElementResponse[] => {
        for (let i = 0; i < nodes.length; i++) {
          const node = nodes[i];

          if (node.children && node.children.length > 0) {
            const childIndex = node.children.findIndex(
              (child) => child.id === id,
            );

            if (childIndex >= 0) {
              const child = node.children[childIndex];
              const newChildren = [...node.children];
              newChildren.splice(childIndex, 1);

              const newNodes = [...nodes];
              newNodes[i] = { ...node, children: newChildren };

              newNodes.splice(i + 1, 0, {
                ...child,
                parentElementId: parentId,
              });

              return newNodes;
            }

            const updatedChildren = outdent(node.children, node.id);
            if (updatedChildren !== node.children) {
              const newNodes = [...nodes];
              newNodes[i] = { ...node, children: updatedChildren };
              return newNodes;
            }
          }
        }
        return nodes;
      };

      return outdent(prev);
    });
  }, []);

  const addText = useCallback(() => {
    setElements((prev) => [
      ...prev,
      {
        id: crypto.randomUUID(),
        type: "text",
        order: prev.length,
        data: "",
        children: [],
      },
    ]);
  }, []);

  const addQuestionAnswer = useCallback(() => {
    const questionId = crypto.randomUUID();
    const answerId = crypto.randomUUID();

    setElements((prev) => [
      ...prev,
      {
        id: questionId,
        type: "question",
        order: prev.length,
        data: "",
        children: [
          {
            id: answerId,
            type: "answer",
            order: 0,
            parentElementId: questionId,
            data: "",
            maxScore: 1,
            children: [],
          },
        ],
      },
    ]);
  }, []);

  const addImageWithMediaKey = useCallback(
    (mediaKey: string, altText: string = "") => {
      setElements((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          type: "image",
          order: prev.length,
          mediaKey,
          altText,
          children: [],
        },
      ]);
    },
    [],
  );

  const addGroup = useCallback(() => {
    setElements((prev) => [
      ...prev,
      {
        id: crypto.randomUUID(),
        type: "container",
        order: prev.length,
        children: [],
      },
    ]);
  }, []);

  return {
    elements,
    isDirty,
    baselineRef,
    commitBaseline,
    resetToBaseline,
    updateElement,
    removeElement,
    moveElementUp,
    moveElementDown,
    indentElement,
    outdentElement,
    addText,
    addQuestionAnswer,
    addImageWithMediaKey,
    addGroup,
  };
}
