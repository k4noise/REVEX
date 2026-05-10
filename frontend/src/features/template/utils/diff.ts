import type {
  TemplateElementResponse,
  AnyPatch,
  AnyElementPayload,
  ElementUpdatePayload,
} from "../../../model/templateElement";
import { flattenTree } from "./tree";

function toCreatePayload(el: TemplateElementResponse): AnyElementPayload {
  const base = {
    id: el.id,
    order: el.order,
    parentElementId: el.parentElementId ?? null,
    displayMode: el.displayMode ?? null,
    marker: el.marker ?? null,
    hint: el.hint ?? null,
  };

  switch (el.type) {
    case "text":
      return { ...base, type: "text", data: el.data ?? "" };

    case "header":
      return {
        ...base,
        type: "header",
        data: el.data ?? "",
        level: el.level ?? 1,
      };

    case "image":
      return {
        ...base,
        type: "image",
        mediaKey: el.mediaKey ?? "",
        altText: el.altText ?? null,
      };

    case "question":
      return {
        ...base,
        type: "question",
        data: el.data ?? "",
        maxScore: el.maxScore ?? 0,
      };

    case "answer":
      return {
        ...base,
        type: "answer",
        data: el.data ?? "",
        maxScore: el.maxScore ?? null,
      };

    case "container":
      return { ...base, type: "container" };

    case "table":
      return { ...base, type: "table" };

    case "row":
      return { ...base, type: "row" };

    case "cell":
      return { ...base, type: "cell" };

    default:
      throw new Error(`Unknown element type: ${el.type}`);
  }
}

const TRACKED_FIELDS = [
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
] as const;

type TrackedField = (typeof TRACKED_FIELDS)[number];

function areValuesEqual(a: unknown, b: unknown): boolean {
  const aVal = a === undefined ? null : a;
  const bVal = b === undefined ? null : b;
  return aVal === bVal;
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
      patches.push({
        action: "create",
        payload: toCreatePayload(draftEl),
      });
    } else {
      const updates: Partial<ElementUpdatePayload> = {};
      let hasChanges = false;

      for (const field of TRACKED_FIELDS) {
        const draftVal = draftEl[field as keyof TemplateElementResponse];
        const origVal = origEl[field as keyof TemplateElementResponse];

        if (!areValuesEqual(draftVal, origVal)) {
          (updates as Record<TrackedField, unknown>)[field] =
            draftVal === undefined ? null : draftVal;
          hasChanges = true;
        }
      }

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
