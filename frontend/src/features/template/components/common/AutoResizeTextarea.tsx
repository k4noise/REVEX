import React, { useRef, useLayoutEffect } from "react";
import { cx } from "../../utils/styles";

interface AutoResizeTextareaProps {
  value: string;
  onChange: (value: string) => void;
  className?: string;
  placeholder: string;
  readOnly?: boolean;
  inputRef?: React.RefObject<HTMLTextAreaElement>;
}

export function AutoResizeTextarea({
  value,
  onChange,
  className,
  placeholder,
  readOnly,
  inputRef,
}: AutoResizeTextareaProps) {
  const localRef = useRef<HTMLTextAreaElement>(null);
  const ref = inputRef ?? localRef;

  useLayoutEffect(() => {
    const element = ref.current;
    if (!element) return;
    element.style.height = "auto";
    element.style.height = `${element.scrollHeight}px`;
  }, [value, ref]);

  return (
    <textarea
      ref={ref}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      onInput={(e) => {
        const element = e.currentTarget;
        element.style.height = "auto";
        element.style.height = `${element.scrollHeight}px`;
      }}
      readOnly={readOnly}
      placeholder={placeholder}
      rows={1}
      className={cx(
        "resize-none overflow-hidden bg-transparent outline-none",
        className,
      )}
    />
  );
}
