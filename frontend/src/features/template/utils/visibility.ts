import type {
  TemplateElementResponse,
  DisplayMode,
} from "@/model/templateElement";
import type { FilterMode } from "../types";
import { isFixedHigh } from "./styles";
import { normalizeDisplayMode } from "./validation";

export const effectiveDisplayMode = (
  element: TemplateElementResponse,
): DisplayMode | null => {
  if (isFixedHigh(element.type)) return "always";
  return normalizeDisplayMode(element.displayMode);
};

export const checkVisibility = (
  element: TemplateElementResponse,
  filter: FilterMode,
  forceShowAll?: boolean,
): boolean => {
  if (forceShowAll) return true;
  if (filter === "all") return true;

  const mode = effectiveDisplayMode(element);
  const isAlways = mode === "always";
  const isPrefer = mode === "prefer";

  if (filter === "important" && (isAlways || isPrefer)) return true;
  if (filter === "key" && isAlways) return true;

  if (element.children?.length) {
    return element.children.some((child) =>
      checkVisibility(child, filter, forceShowAll),
    );
  }

  return false;
};

export const shouldHideMarkers = (filterMode: FilterMode): boolean =>
  filterMode === "key";
