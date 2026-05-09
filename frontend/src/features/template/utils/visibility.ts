import type {
  TemplateElementResponse,
  DisplayMode,
} from "../../../model/templateElement";
import type { FilterMode } from "../types";
import { isFixedHigh } from "./styles";
import { normalizeDisplayMode } from "./validation";

export const effectiveDisplayMode = (
  element: TemplateElementResponse,
): DisplayMode | null => {
  if (isFixedHigh(element.type)) return "always";
  return normalizeDisplayMode(element.displayMode);
};

export const shouldHideMarkers = (filterMode: FilterMode): boolean =>
  filterMode === "key";

function isElementVisibleByFilter(
  element: TemplateElementResponse,
  filter: FilterMode,
): boolean {
  if (filter === "all") return true;

  const mode = effectiveDisplayMode(element);
  const isAlways = mode === "always";
  const isPrefer = mode === "prefer";

  if (filter === "important") {
    return isAlways || isPrefer;
  }

  if (filter === "key") {
    return isAlways;
  }

  return true;
}

export function filterTreeByVisibility(
  nodes: TemplateElementResponse[],
  filter: FilterMode,
): TemplateElementResponse[] {
  if (filter === "all") {
    return nodes;
  }

  const result: TemplateElementResponse[] = [];

  for (const node of nodes) {
    const selfVisible = isElementVisibleByFilter(node, filter);

    if (selfVisible) {
      result.push(node);
      continue;
    }

    const visibleChildren = filterTreeByVisibility(node.children ?? [], filter);

    if (visibleChildren.length > 0) {
      result.push({
        ...node,
        children: visibleChildren,
      });
    }
  }

  return result;
}
