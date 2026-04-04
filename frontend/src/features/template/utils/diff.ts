import type {
  TemplateElementResponse,
  AnyPatch,
  ElementUpdatePayload,
} from "@/model/templateElement";

export function flattenTree(
  elements: TemplateElementResponse[],
): Record<string, TemplateElementResponse> {
  const map: Record<string, TemplateElementResponse> = {};
  const traverse = (nodes: TemplateElementResponse[]) => {
    for (const node of nodes) {
      map[node.id] = node;
      if (node.children && node.children.length > 0) {
        traverse(node.children);
      }
    }
  };
  traverse(elements);
  return map;
}

export function generatePatches(
  originalTree: TemplateElementResponse[],
  draftTree: TemplateElementResponse[],
): AnyPatch[] {
  const patches: AnyPatch[] = [];
  const originalMap = flattenTree(originalTree);
  const draftMap = flattenTree(draftTree);

  for (const [id, draftEl] of Object.entries(draftMap)) {
    const origEl = originalMap[id];

    if (!origEl) {
      const { children, ...payload } = draftEl;
      patches.push({
        action: "create",
        payload: payload as any,
      });
    } else {
      const updates: Partial<ElementUpdatePayload> = {};
      let hasChanges = false;

      const fields: (keyof TemplateElementResponse)[] = [
        "parentElementId", 
        "data",
        "level",
        "maxScore",
        "order",
        "marker",
        "hint",
        "displayMode",
        "altText",
        "mediaKey",
      ];

      fields.forEach((field) => {
        if ((draftEl as any)[field] !== (origEl as any)[field]) {
          (updates as any)[field] = (draftEl as any)[field];
          hasChanges = true;
        }
      });

      if (hasChanges) {
        patches.push({
          action: "update",
          payload: { id, ...updates } as ElementUpdatePayload,
        });
      }
    }
  }

  for (const id of Object.keys(originalMap)) {
    if (!draftMap[id]) {
      patches.push({
        action: "delete",
        payload: { id },
      });
    }
  }

  return patches;
}
