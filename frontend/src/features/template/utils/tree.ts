import type { TemplateElementResponse } from "../../../model/templateElement";

export function reindex(
  nodes: TemplateElementResponse[],
): TemplateElementResponse[] {
  return nodes.map((node, i) =>
    node.order === i ? node : { ...node, order: i },
  );
}

export function flattenTree(
  elements: TemplateElementResponse[],
): Record<string, TemplateElementResponse> {
  const map: Record<string, TemplateElementResponse> = {};
  const traverse = (nodes: TemplateElementResponse[]) => {
    for (const node of nodes) {
      map[node.id] = node;
      if (node.children?.length) traverse(node.children);
    }
  };
  traverse(elements);
  return map;
}

export function updateNodeInTree(
  nodes: TemplateElementResponse[],
  id: string,
  updates: Partial<TemplateElementResponse>,
): TemplateElementResponse[] {
  let hasChanges = false;
  const newNodes = nodes.map((node) => {
    if (node.id === id) {
      hasChanges = true;
      return { ...node, ...updates };
    }
    if (node.children?.length) {
      const updatedChildren = updateNodeInTree(node.children, id, updates);
      if (updatedChildren !== node.children) {
        hasChanges = true;
        return { ...node, children: updatedChildren };
      }
    }
    return node;
  });
  return hasChanges ? newNodes : nodes;
}

export function removeNodeFromTree(
  nodes: TemplateElementResponse[],
  id: string,
): TemplateElementResponse[] {
  const filtered = nodes.filter((n) => n.id !== id);
  if (filtered.length !== nodes.length) return reindex(filtered);
  let hasChanges = false;
  const newNodes = nodes.map((node) => {
    if (node.children?.length) {
      const updated = removeNodeFromTree(node.children, id);
      if (updated !== node.children) {
        hasChanges = true;
        return { ...node, children: updated };
      }
    }
    return node;
  });
  return hasChanges ? newNodes : nodes;
}

export function insertElementAt(
  nodes: TemplateElementResponse[],
  index: number,
  element: TemplateElementResponse,
): TemplateElementResponse[] {
  const clamped = Math.min(Math.max(0, index), nodes.length);
  const newNodes = [...nodes];
  newNodes.splice(clamped, 0, element);
  return reindex(newNodes);
}

export function addChildToNode(
  nodes: TemplateElementResponse[],
  parentId: string,
  child: TemplateElementResponse,
): TemplateElementResponse[] {
  let hasChanges = false;
  const newNodes = nodes.map((node) => {
    if (node.id === parentId) {
      hasChanges = true;
      return { ...node, children: [...(node.children || []), child] };
    }
    if (node.children?.length) {
      const updated = addChildToNode(node.children, parentId, child);
      if (updated !== node.children) {
        hasChanges = true;
        return { ...node, children: updated };
      }
    }
    return node;
  });
  return hasChanges ? newNodes : nodes;
}

export function replaceCellChildren(
  nodes: TemplateElementResponse[],
  cellId: string,
  newChildren: TemplateElementResponse[],
): TemplateElementResponse[] {
  let hasChanges = false;
  const newNodes = nodes.map((node) => {
    if (node.id === cellId && node.type === "cell") {
      hasChanges = true;
      return { ...node, children: newChildren };
    }
    if (node.children?.length) {
      const updated = replaceCellChildren(node.children, cellId, newChildren);
      if (updated !== node.children) {
        hasChanges = true;
        return { ...node, children: updated };
      }
    }
    return node;
  });
  return hasChanges ? newNodes : nodes;
}

export function moveNodeUp(
  nodes: TemplateElementResponse[],
  id: string,
): TemplateElementResponse[] {
  const index = nodes.findIndex((n) => n.id === id);
  if (index > 0) {
    const newNodes = [...nodes];
    [newNodes[index - 1], newNodes[index]] = [
      newNodes[index],
      newNodes[index - 1],
    ];
    return reindex(newNodes);
  }
  let hasChanges = false;
  const newNodes = nodes.map((node) => {
    if (node.children?.length) {
      const updated = moveNodeUp(node.children, id);
      if (updated !== node.children) {
        hasChanges = true;
        return { ...node, children: updated };
      }
    }
    return node;
  });
  return hasChanges ? newNodes : nodes;
}

export function moveNodeDown(
  nodes: TemplateElementResponse[],
  id: string,
): TemplateElementResponse[] {
  const index = nodes.findIndex((n) => n.id === id);
  if (index >= 0 && index < nodes.length - 1) {
    const newNodes = [...nodes];
    [newNodes[index], newNodes[index + 1]] = [
      newNodes[index + 1],
      newNodes[index],
    ];
    return reindex(newNodes);
  }
  let hasChanges = false;
  const newNodes = nodes.map((node) => {
    if (node.children?.length) {
      const updated = moveNodeDown(node.children, id);
      if (updated !== node.children) {
        hasChanges = true;
        return { ...node, children: updated };
      }
    }
    return node;
  });
  return hasChanges ? newNodes : nodes;
}

export function indentNode(
  nodes: TemplateElementResponse[],
  id: string,
): TemplateElementResponse[] {
  for (let i = 0; i < nodes.length; i++) {
    if (nodes[i].id === id && i > 0) {
      const element = nodes[i];
      const newTarget = nodes[i - 1];
      const newNodes = [...nodes];
      newNodes.splice(i, 1);
      const newChildren = reindex([
        ...(newTarget.children || []),
        { ...element, parentElementId: newTarget.id },
      ]);
      newNodes[i - 1] = { ...newTarget, children: newChildren };
      return reindex(newNodes);
    }
    const currentChildren = nodes[i].children;
    if (currentChildren?.length) {
      const updatedChildren = indentNode(currentChildren, id);
      if (updatedChildren !== currentChildren) {
        const newNodes = [...nodes];
        newNodes[i] = { ...nodes[i], children: updatedChildren };
        return newNodes;
      }
    }
  }
  return nodes;
}

export function outdentNode(
  nodes: TemplateElementResponse[],
  id: string,
  parentId: string | null = null,
): TemplateElementResponse[] {
  for (let i = 0; i < nodes.length; i++) {
    const node = nodes[i];
    if (node.children?.length) {
      const childIndex = node.children.findIndex((child) => child.id === id);
      if (childIndex >= 0) {
        const child = node.children[childIndex];
        const newChildren = reindex(
          node.children.filter((_, idx) => idx !== childIndex),
        );
        const newNodes = [...nodes];
        newNodes[i] = { ...node, children: newChildren };
        newNodes.splice(i + 1, 0, { ...child, parentElementId: parentId });
        return reindex(newNodes);
      }
      const updatedChildren = outdentNode(node.children, id, node.id);
      if (updatedChildren !== node.children) {
        const newNodes = [...nodes];
        newNodes[i] = { ...node, children: updatedChildren };
        return newNodes;
      }
    }
  }
  return nodes;
}
