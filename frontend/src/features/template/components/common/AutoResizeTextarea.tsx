import {
  useRef,
  useLayoutEffect,
  type RefObject,
  type TextareaHTMLAttributes,
  memo,
} from "react";
import { cx } from "../../utils/styles";

type NativeTextareaProps = Omit<
  TextareaHTMLAttributes<HTMLTextAreaElement>,
  "value" | "onChange"
>;

interface AutoResizeTextareaProps extends NativeTextareaProps {
  value: string;
  onChange: (value: string) => void;
  inputRef?: RefObject<HTMLTextAreaElement | null>;
}

export const AutoResizeTextarea = memo(function AutoResizeTextarea({
  value,
  onChange,
  className,
  inputRef,
  ...restProps
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
      rows={1}
      className={cx(
        "resize-none overflow-hidden bg-transparent outline-none",
        "transition-shadow duration-150",
        !restProps.readOnly &&
          "focus:ring-2 focus:ring-blue-500/20 focus:rounded-lg",
        className,
      )}
      {...restProps}
    />
  );
});
