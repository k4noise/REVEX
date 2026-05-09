import type { QuestionReference } from "../types";

export function buildQuestionsMap(
  questions: QuestionReference[],
): Map<string, QuestionReference> {
  const map = new Map<string, QuestionReference>();
  for (const question of questions) {
    map.set(question.id, question);
  }
  return map;
}

export function extractVarIds(value: string): string[] {
  const ids: string[] = [];
  const regex = /\{([0-9a-fA-F-]{36})(?:\|[^}]*)?\}/g;
  let match;
  while ((match = regex.exec(value)) !== null) {
    ids.push(match[1]);
  }
  return ids;
}

export function normalizeVarsToIdOnly(value: string): string {
  return value.replace(/\{([0-9a-fA-F-]{36})(?:\|[^}]*)?\}/g, "{$1}");
}

export function insertVar(
  text: string,
  id: string,
  start: number,
  end: number,
): { next: string; cursor: number } {
  const token = `{${id}}`;
  const before = text.slice(0, start);
  const after = text.slice(end);

  const needSpaceBefore = before.length > 0 && !/\s$/.test(before);
  const needSpaceAfter = after.length > 0 && !/^\s/.test(after);

  const insert = `${needSpaceBefore ? " " : ""}${token}${needSpaceAfter ? " " : ""}`;
  const nextText = before + insert + after;
  const cursor = before.length + insert.length;

  return { next: nextText, cursor };
}
