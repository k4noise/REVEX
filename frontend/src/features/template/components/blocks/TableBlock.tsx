import React from "react";
import type { CommonBlockProps } from "../../types";
import { cx } from "../../utils/styles";
import { BlocksList } from "../BlocksList";

export function TableBlock(props: CommonBlockProps) {
  const { element, ...restProps } = props;

  if (!element.children?.length) {
    return (
      <div className="my-6 w-full overflow-x-auto rounded-xl border border-zinc-200 dark:border-zinc-800">
        <table className="w-full text-left text-sm text-zinc-700 dark:text-zinc-300">
          <tbody className="divide-y divide-zinc-200 dark:divide-zinc-800">
            <tr>
              <td className="p-5 text-zinc-400">Таблица пуста.</td>
            </tr>
          </tbody>
        </table>
      </div>
    );
  }

  return (
    <div className="my-6 w-full overflow-x-auto rounded-xl border border-zinc-200 dark:border-zinc-800">
      <table className="w-full text-left text-sm text-zinc-700 dark:text-zinc-300">
        <tbody className="divide-y divide-zinc-200 dark:divide-zinc-800">
          {element.children.map((row) => (
            <TableRow key={row.id} {...restProps} element={row} />
          ))}
        </tbody>
      </table>
    </div>
  );
}

function TableRow(props: CommonBlockProps) {
  const { element, ...restProps } = props;

  if (element.type !== "row") return null;

  return (
    <tr className="divide-x divide-zinc-200 bg-white even:bg-zinc-50 dark:divide-zinc-800 dark:bg-[#1A1A1D] dark:even:bg-[#141416]">
      {element.children?.map((cell) => (
        <TableCell key={cell.id} {...restProps} element={cell} />
      ))}
    </tr>
  );
}

function TableCell(props: CommonBlockProps) {
  const { element, ...restProps } = props;

  if (element.type !== "cell") return null;

  const rowSpan =
    typeof element.rowspan === "number" && element.rowspan > 1
      ? element.rowspan
      : undefined;
  const colSpan =
    typeof element.colspan === "number" && element.colspan > 1
      ? element.colspan
      : undefined;

  return (
    <td
      rowSpan={rowSpan}
      colSpan={colSpan}
      className="min-w-[140px] p-3 align-middle leading-relaxed"
    >
      {element.children && element.children.length > 0 && (
        <BlocksList
          {...restProps}
          elements={element.children}
          parentType="cell"
        />
      )}
    </td>
  );
}
