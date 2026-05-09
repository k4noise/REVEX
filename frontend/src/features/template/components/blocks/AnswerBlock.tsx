import { useState, memo, useEffect } from "react";
import type { CommonBlockProps } from "../../types";
import { cx } from "../../utils/styles";
import { AutoResizeTextarea } from "../common/AutoResizeTextarea";
import { ParamLegend } from "../common/ParamLegend";
import { normalizeWeight } from "../../utils/validation";

function preGradeLabel(score: number | null): string {
  if (score === null) return "Нет данных";
  if (score >= 1) return " верно";
  if (score <= 0) return " неверно";
  return "Частично верно";
}

function preGradeColor(score: number | null): string {
  if (score === null) return "text-zinc-500 dark:text-zinc-400";
  if (score >= 1) return "text-emerald-600 dark:text-emerald-400";
  if (score <= 0) return "text-red-600 dark:text-red-400";
  return "text-amber-600 dark:text-amber-400";
}

function gradeStatusLabel(grade: number | null): string {
  if (grade === null) return "";
  if (grade >= 1) return "Верно";
  if (grade <= 0) return "Неверно";
  return "Частично верно";
}

function gradeStatusColor(grade: number | null): string {
  if (grade === null) return "text-zinc-500 dark:text-zinc-400";
  if (grade >= 1) return "text-emerald-600 dark:text-emerald-400";
  if (grade <= 0) return "text-red-600 dark:text-red-400";
  return "text-amber-600 dark:text-amber-400";
}

type GradingChoice = "correct" | "partial" | "incorrect";

function gradeToChoice(grade: number | null): GradingChoice | null {
  if (grade === null) return null;
  if (grade >= 1) return "correct";
  if (grade <= 0) return "incorrect";
  return "partial";
}

function CompactGradingBlock({
  elementId,
  gradingInfo,
  onAnswerGradeChange,
}: {
  elementId: string;
  gradingInfo: NonNullable<CommonBlockProps["answerGrading"]> extends Map<
    string,
    infer V
  >
    ? V
    : never;
  onAnswerGradeChange?: (elementId: string, grade: number) => void;
}) {
  const grade = gradingInfo.grade;
  const choice = gradeToChoice(grade);
  const earnedPoints = gradingInfo.earnedPoints;
  const status = gradingInfo.status;

  return (
    <div className="flex items-center gap-2 mt-1">
      <div className="flex rounded border border-zinc-200 dark:border-zinc-700 overflow-hidden">
        <button
          type="button"
          onClick={() => onAnswerGradeChange?.(elementId, 1)}
          className={cx(
            "px-2 py-0.5 text-xs font-semibold transition-colors",
            choice === "correct"
              ? "bg-emerald-500 text-white dark:bg-emerald-600"
              : "bg-zinc-50 text-zinc-500 hover:bg-emerald-50 dark:bg-zinc-800 dark:text-zinc-400",
          )}
          title="Верно"
        >
          1
        </button>
        <button
          type="button"
          onClick={() => onAnswerGradeChange?.(elementId, 0.5)}
          className={cx(
            "px-2 py-0.5 text-xs font-semibold transition-colors border-x border-zinc-200 dark:border-zinc-700",
            choice === "partial"
              ? "bg-amber-500 text-white dark:bg-amber-600"
              : "bg-zinc-50 text-zinc-500 hover:bg-amber-50 dark:bg-zinc-800 dark:text-zinc-400",
          )}
          title="Частично"
        >
          .5
        </button>
        <button
          type="button"
          onClick={() => onAnswerGradeChange?.(elementId, 0)}
          className={cx(
            "px-2 py-0.5 text-xs font-semibold transition-colors",
            choice === "incorrect"
              ? "bg-red-500 text-white dark:bg-red-600"
              : "bg-zinc-50 text-zinc-500 hover:bg-red-50 dark:bg-zinc-800 dark:text-zinc-400",
          )}
          title="Неверно"
        >
          0
        </button>
      </div>
      <span
        className={cx(
          "text-xs font-bold tabular-nums",
          status === "correct"
            ? "text-emerald-600 dark:text-emerald-400"
            : status === "partial"
              ? "text-amber-600 dark:text-amber-400"
              : status === "incorrect"
                ? "text-red-600 dark:text-red-400"
                : "text-zinc-400 dark:text-zinc-500",
        )}
      >
        {earnedPoints.toFixed(2)}
      </span>
    </div>
  );
}

function CompactGradedView({
  grade,
  earnedPoints,
  maxPoints,
}: {
  grade: number | null;
  earnedPoints: number;
  maxPoints: number;
}) {
  return (
    <div className="flex items-center gap-2 mt-1">
      <span className={cx("text-xs font-semibold", gradeStatusColor(grade))}>
        {gradeStatusLabel(grade)}
      </span>
      <span
        className={cx(
          "text-xs font-bold tabular-nums",
          gradeStatusColor(grade),
        )}
      >
        {earnedPoints.toFixed(2)}
      </span>
      <span className="text-xs text-zinc-400 dark:text-zinc-500">
        / {maxPoints.toFixed(2)}
      </span>
    </div>
  );
}

function PreviousAnswerNotice({
  grade,
  earnedPoints,
  maxPoints,
  previousText,
  comment,
  invalidated,
  compact = false,
}: {
  grade: number | null;
  earnedPoints: number;
  maxPoints: number;
  previousText: string;
  comment: string;
  invalidated: boolean | undefined;
  compact?: boolean;
}) {
  const label = gradeStatusLabel(grade);

  if (compact) {
    return (
      <div
        className={cx(
          "mt-1 rounded-md border px-2 py-1",
          invalidated
            ? "border-blue-200 bg-blue-50/70 dark:border-blue-900/50 dark:bg-blue-900/20"
            : "border-zinc-200 bg-zinc-50/80 dark:border-zinc-700 dark:bg-zinc-900/40",
        )}
      >
        <div className="space-y-0.5">
          <div className="text-[11px] leading-snug text-zinc-600 dark:text-zinc-300">
            <span className="font-medium">Оцененный ответ</span>
            {invalidated && " · неактуален"}
          </div>
          {grade !== null && (
            <div className="text-[11px] leading-snug text-zinc-600 dark:text-zinc-300">
              {label} · {earnedPoints.toFixed(2)} / {maxPoints.toFixed(2)}
            </div>
          )}
          {previousText && (
            <div className="truncate text-[11px] text-zinc-500 dark:text-zinc-400">
              Ответ: {previousText}
            </div>
          )}
        </div>
      </div>
    );
  }

  return (
    <div
      className={cx(
        "mt-4 rounded-xl border px-4 py-3",
        invalidated
          ? "border-blue-200 bg-blue-50/70 dark:border-blue-900/50 dark:bg-blue-900/20"
          : "border-zinc-200 bg-zinc-50/70 dark:border-zinc-700 dark:bg-zinc-900/30",
      )}
    >
      <div className="space-y-2">
        <div className="flex flex-wrap items-center gap-3">
          <span className="text-xs font-semibold uppercase tracking-wider text-zinc-500 dark:text-zinc-400">
            Оцененный ответ
          </span>
          {invalidated && (
            <span className="text-xs font-medium text-blue-700 dark:text-blue-300">
              Неактуален после редактирования
            </span>
          )}
        </div>

        {grade !== null && (
          <div className="flex flex-wrap items-center gap-4">
            <span
              className={cx("text-sm font-semibold", gradeStatusColor(grade))}
            >
              {label}
            </span>
            <span className="text-sm tabular-nums text-zinc-700 dark:text-zinc-300">
              <span className={cx("font-bold", gradeStatusColor(grade))}>
                {earnedPoints.toFixed(2)}
              </span>
              <span className="text-zinc-500 dark:text-zinc-400">
                {" "}
                / {maxPoints.toFixed(2)} б.
              </span>
            </span>
          </div>
        )}

        {previousText && (
          <div className="rounded-lg bg-white/70 px-3 py-2 text-sm text-zinc-700 dark:bg-black/10 dark:text-zinc-300">
            <span className="font-medium text-zinc-500 dark:text-zinc-400">
              Оцененный ответ:
            </span>{" "}
            {previousText}
          </div>
        )}

        {comment && (
          <div className="rounded-lg bg-white/70 px-3 py-2 dark:bg-black/10">
            <div className="mb-1 text-xs font-semibold uppercase tracking-wider text-zinc-500 dark:text-zinc-400">
              Комментарий преподавателя
            </div>
            <div className="text-sm whitespace-pre-wrap text-zinc-800 dark:text-zinc-200">
              {comment}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export const AnswerBlock = memo(function AnswerBlock(props: CommonBlockProps) {
  const {
    element,
    updateElement,
    isReadOnly,
    isReportMode,
    isGradingMode,
    globalScoring,
    answerGrading,
    onAnswerGradeChange,
    onAnswerCommentChange,
    parentType,
    availableQuestions,
    hints,
    onAnswerBlur,
    onAnswerInput,
  } = props;

  const [showComment, setShowComment] = useState(false);
  const [showDetails, setShowDetails] = useState(false);
  const [partialOpen, setPartialOpen] = useState(false);

  const gradingInfo = answerGrading?.get(element.id);
  const grade = gradingInfo?.grade ?? null;
  const previousGrade = gradingInfo?.previousGrade ?? null;
  const previousEarnedPoints = gradingInfo?.previousEarnedPoints ?? 0;
  const previousComment = gradingInfo?.previousComment ?? "";
  const [partialInputValue, setPartialInputValue] = useState<string>("");

  useEffect(() => {
    const isPartial = grade !== null && grade > 0 && grade < 1;
    setPartialInputValue(isPartial ? String(grade) : "");
    if (isPartial) {
      setPartialOpen(true);
    }
  }, [grade]);

  const inCell = parentType === "cell";

  const text = element.data || "";
  const scoringInfo = globalScoring?.byAnswerId?.[element.id];
  const hint = hints?.get(element.id);

  const placeholder =
    isReportMode && !isReadOnly ? "Введите ответ..." : "Ответ...";

  const maxPoints = gradingInfo?.maxPoints ?? 0;
  const earnedPoints = gradingInfo?.earnedPoints ?? 0;
  const status = gradingInfo?.status ?? "ungraded";

  const isEditing = isReportMode && !isReadOnly;
  const textModified =
    isEditing &&
    gradingInfo?.originalText !== undefined &&
    text !== gradingInfo.originalText;

  const isGradedView =
    !isGradingMode &&
    !textModified &&
    !isEditing &&
    !!gradingInfo &&
    grade !== null;

  const hasHistoricalAssessment =
    isEditing &&
    !isGradingMode &&
    !!gradingInfo &&
    (previousGrade !== null ||
      previousComment.trim().length > 0 ||
      (gradingInfo.originalText?.trim().length ?? 0) > 0);

  const isTemplateEdit =
    !isReportMode && !isGradingMode && !isGradedView && !isReadOnly;

  const emptyInReport = isEditing && !textModified && !text.trim();

  const showHint =
    !!hint && !!hint.hint && !isGradingMode && !isGradedView && !isTemplateEdit;

  const previousText = gradingInfo?.originalText?.trim() ?? "";

  if (inCell) {
    const showCellGrade =
      !textModified &&
      (isGradingMode || isGradedView || hasHistoricalAssessment);

    const cellBg =
      textModified && hasHistoricalAssessment
        ? "bg-blue-50/40 dark:bg-blue-900/10"
        : showCellGrade
          ? status === "correct"
            ? "bg-emerald-50/40 dark:bg-emerald-900/10"
            : status === "partial"
              ? "bg-amber-50/40 dark:bg-amber-900/10"
              : status === "incorrect"
                ? "bg-red-50/40 dark:bg-red-900/10"
                : ""
          : emptyInReport
            ? "bg-amber-50/20 dark:bg-amber-900/5"
            : "";

    return (
      <div className={cx("rounded-lg px-1 py-0.5 transition-colors", cellBg)}>
        <AutoResizeTextarea
          value={text}
          onChange={(val) => {
            if (isReadOnly || isGradingMode) return;
            updateElement(element.id, { data: val });
            onAnswerInput?.(element.id);
          }}
          onBlur={
            !isReadOnly && !isGradingMode && onAnswerBlur
              ? () => onAnswerBlur(element.id)
              : undefined
          }
          readOnly={isReadOnly || isGradingMode}
          className={cx(
            "w-full text-sm text-zinc-900 outline-none bg-transparent",
            "placeholder:text-zinc-400 dark:text-zinc-100 dark:placeholder:text-zinc-600",
            isGradingMode && !text && "italic text-zinc-400",
          )}
          placeholder={placeholder}
        />

        {hasHistoricalAssessment && gradingInfo && (
          <PreviousAnswerNotice
            grade={previousGrade}
            earnedPoints={previousEarnedPoints}
            maxPoints={maxPoints}
            previousText={previousText}
            comment={previousComment}
            invalidated={textModified}
            compact={true}
          />
        )}

        {isTemplateEdit && scoringInfo && (
          <div className="flex items-center gap-2 mt-1">
            <span className="text-xs text-zinc-400 dark:text-zinc-500">
              Вес
            </span>
            <input
              type="number"
              min={0}
              max={20}
              step={1}
              value={element.maxScore ?? 1}
              onChange={(e) => {
                const val = normalizeWeight(e.target.value);
                updateElement(element.id, { maxScore: val });
              }}
              className={cx(
                "w-10 h-5 rounded border px-1 text-xs font-semibold text-center outline-none",
                "border-zinc-300 bg-white text-zinc-700",
                "dark:border-zinc-600 dark:bg-zinc-800 dark:text-zinc-300",
                "focus:ring-1 focus:ring-blue-500/20",
              )}
            />
            <span className="text-xs text-zinc-400 dark:text-zinc-500">
              = {scoringInfo.points.toFixed(2)} б.
            </span>
          </div>
        )}

        {isGradingMode && !textModified && gradingInfo && (
          <CompactGradingBlock
            elementId={element.id}
            gradingInfo={gradingInfo}
            onAnswerGradeChange={onAnswerGradeChange}
          />
        )}

        {(isGradedView || (hasHistoricalAssessment && !textModified)) &&
          gradingInfo &&
          grade !== null && (
            <CompactGradedView
              grade={grade}
              earnedPoints={earnedPoints}
              maxPoints={maxPoints}
            />
          )}

        {showHint && (
          <div className="mt-1 animate-in fade-in duration-300">
            <div className="text-xs text-zinc-600 dark:text-zinc-400 leading-snug">
              {hint.hint}
            </div>
          </div>
        )}
      </div>
    );
  }

  const borderColor =
    textModified && hasHistoricalAssessment
      ? "border-blue-300 border-dashed dark:border-blue-700"
      : emptyInReport
        ? "border-amber-300 border-dashed dark:border-amber-700"
        : showFullGradeOrPrevious(
              isGradingMode,
              isGradedView,
              hasHistoricalAssessment,
            )
          ? status === "correct"
            ? "border-emerald-300 dark:border-emerald-700"
            : status === "partial"
              ? "border-amber-300 dark:border-amber-700"
              : status === "incorrect"
                ? "border-red-300 dark:border-red-700"
                : "border-zinc-200 dark:border-zinc-700"
          : "border-zinc-200 dark:border-zinc-800";

  const bgColor =
    textModified && hasHistoricalAssessment
      ? "bg-blue-50/30 dark:bg-blue-900/10"
      : emptyInReport
        ? "bg-amber-50/20 dark:bg-amber-900/5"
        : showFullGradeOrPrevious(
              isGradingMode,
              isGradedView,
              hasHistoricalAssessment,
            )
          ? status === "correct"
            ? "bg-emerald-50/30 dark:bg-emerald-900/10"
            : status === "partial"
              ? "bg-amber-50/30 dark:bg-amber-900/10"
              : status === "incorrect"
                ? "bg-red-50/30 dark:bg-red-900/10"
                : "bg-white dark:bg-[#141416]"
          : "bg-zinc-50/50 dark:bg-zinc-900/20";

  const preGrade = gradingInfo?.preGrade;
  const preGradeScore = preGrade?.score ?? null;
  const hasDetails =
    (preGrade?.errors?.length ?? 0) > 0 || preGrade?.needsManualReview;

  const isEmpty = !text.trim();

  const choice = gradeToChoice(grade);
  const showPartialInput = choice === "partial" || partialOpen;

  const handleChoice = (c: GradingChoice) => {
    if (c === "correct") {
      onAnswerGradeChange?.(element.id, 1);
      setPartialOpen(false);
    } else if (c === "incorrect") {
      onAnswerGradeChange?.(element.id, 0);
      setPartialOpen(false);
    } else {
      setPartialOpen(true);
      onAnswerGradeChange?.(element.id, 0.5);
    }
  };

  return (
    <div
      className={cx(
        "mt-3 rounded-2xl border px-5 py-4 transition-colors",
        borderColor,
        bgColor,
      )}
    >
      {(isGradingMode || isGradedView) && (
        <div className="mb-3 flex items-center gap-3">
          <span className="text-xs font-semibold uppercase tracking-wider text-zinc-400 dark:text-zinc-500">
            Ответ студента
          </span>
          {isEmpty && (
            <span className="text-xs font-medium text-zinc-400 dark:text-zinc-500 italic">
              — пусто
            </span>
          )}
        </div>
      )}

      <div
        className={cx(
          (isGradingMode || isGradedView || hasHistoricalAssessment) &&
            "rounded-xl bg-white/60 dark:bg-zinc-900/40 px-4 py-3",
        )}
        onBlur={
          !isReadOnly && !isGradingMode && onAnswerBlur
            ? () => onAnswerBlur(element.id)
            : undefined
        }
      >
        <AutoResizeTextarea
          value={text}
          onChange={(val) => {
            if (isReadOnly) return;
            updateElement(element.id, { data: val });
            onAnswerInput?.(element.id);
          }}
          readOnly={isReadOnly || isGradingMode}
          className={cx(
            "w-full text-base text-zinc-900 outline-none bg-transparent leading-relaxed",
            "placeholder:text-zinc-400 dark:text-zinc-100 dark:placeholder:text-zinc-600",
          )}
          placeholder={placeholder}
        />

        {isTemplateEdit &&
          availableQuestions &&
          availableQuestions.all.length > 0 && (
            <ParamLegend text={text} groups={availableQuestions} />
          )}
      </div>

      {showHint && (
        <div className="mt-2 rounded-xl px-4 py-3 bg-blue-50/50 dark:bg-blue-900/10 animate-in fade-in slide-in-from-top-1 duration-300">
          <div className="text-sm text-zinc-700 dark:text-zinc-300 leading-relaxed">
            {hint.hint}
          </div>
        </div>
      )}

      {hasHistoricalAssessment && gradingInfo && (
        <PreviousAnswerNotice
          grade={previousGrade}
          earnedPoints={previousEarnedPoints}
          maxPoints={maxPoints}
          previousText={previousText}
          comment={previousComment}
          invalidated={textModified}
        />
      )}

      {isGradingMode && !textModified && gradingInfo && (
        <div className="mt-4 space-y-3">
          {preGrade && (
            <div className="flex flex-wrap items-center gap-3">
              <span
                className={cx(
                  "text-sm font-semibold",
                  preGradeColor(preGradeScore),
                )}
              >
                Предварительно{preGradeLabel(preGradeScore)}
              </span>
              {preGrade.needsManualReview && (
                <span className="text-sm text-amber-600 dark:text-amber-400">
                  / Требует ручной проверки
                </span>
              )}
              {hasDetails && (
                <button
                  type="button"
                  onClick={() => setShowDetails((prev) => !prev)}
                  className={cx(
                    "rounded-lg border px-3 py-1.5 text-sm font-medium transition-colors",
                    showDetails
                      ? "border-zinc-300 bg-zinc-100 text-zinc-700 dark:border-zinc-600 dark:bg-zinc-700 dark:text-zinc-200"
                      : "border-zinc-200 bg-zinc-50 text-zinc-600 hover:bg-zinc-100 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-400 dark:hover:bg-zinc-700",
                  )}
                >
                  {showDetails ? "Скрыть детали" : "Детали"}
                </button>
              )}
            </div>
          )}

          {preGrade?.explanation && (
            <div className="text-sm text-zinc-600 dark:text-zinc-400 leading-relaxed">
              {preGrade.explanation}
            </div>
          )}

          {showDetails && hasDetails && (
            <div className="rounded-xl border border-zinc-200 bg-zinc-50/50 p-4 dark:border-zinc-700 dark:bg-zinc-800/50 space-y-2">
              {preGrade?.needsManualReview && (
                <div className="text-sm font-medium text-amber-600 dark:text-amber-400">
                  Требует ручной проверки
                </div>
              )}
              {preGrade?.errors?.map((err, i) => (
                <div
                  key={i}
                  className="text-sm text-zinc-700 dark:text-zinc-300"
                >
                  <span className="font-medium text-zinc-500 dark:text-zinc-400">
                    {err.type}:
                  </span>{" "}
                  ожидалось [{err.expected}]
                  {err.actual && `, получено [${err.actual}]`}
                </div>
              ))}
            </div>
          )}

          <div
            className={cx(
              "rounded-xl p-4",
              "bg-white border border-zinc-200",
              "dark:bg-zinc-900/60 dark:border-zinc-700",
            )}
          >
            <div className="flex items-center justify-between gap-6">
              <div className="flex items-center gap-3">
                <div className="flex rounded-lg border border-zinc-200 dark:border-zinc-700 overflow-hidden">
                  <button
                    type="button"
                    onClick={() => handleChoice("correct")}
                    className={cx(
                      "h-10 px-4 text-sm font-semibold transition-colors border-r border-zinc-200 dark:border-zinc-700",
                      choice === "correct"
                        ? "bg-emerald-500 text-white dark:bg-emerald-600"
                        : "bg-zinc-50 text-zinc-600 hover:bg-emerald-50 hover:text-emerald-700 dark:bg-zinc-800 dark:text-zinc-400 dark:hover:bg-emerald-900/30 dark:hover:text-emerald-300",
                    )}
                  >
                    Верно
                  </button>
                  <button
                    type="button"
                    onClick={() => handleChoice("partial")}
                    className={cx(
                      "h-10 px-4 text-sm font-semibold transition-colors border-r border-zinc-200 dark:border-zinc-700",
                      choice === "partial"
                        ? "bg-amber-500 text-white dark:bg-amber-600"
                        : "bg-zinc-50 text-zinc-600 hover:bg-amber-50 hover:text-amber-700 dark:bg-zinc-800 dark:text-zinc-400 dark:hover:bg-amber-900/30 dark:hover:text-amber-300",
                    )}
                  >
                    Частично
                  </button>
                  <button
                    type="button"
                    onClick={() => handleChoice("incorrect")}
                    className={cx(
                      "h-10 px-4 text-sm font-semibold transition-colors",
                      choice === "incorrect"
                        ? "bg-red-500 text-white dark:bg-red-600"
                        : "bg-zinc-50 text-zinc-600 hover:bg-red-50 hover:text-red-700 dark:bg-zinc-800 dark:text-zinc-400 dark:hover:bg-red-900/30 dark:hover:text-red-300",
                    )}
                  >
                    Неверно
                  </button>
                </div>

                {showPartialInput && (
                  <>
                    <div className="h-6 w-px bg-zinc-200 dark:bg-zinc-700" />
                    <div className="flex items-center gap-2">
                      <input
                        type="text"
                        value={partialInputValue}
                        onChange={(e) => {
                          const raw = e.target.value;
                          setPartialInputValue(raw);
                          if (raw.trim() === "" || raw.trim() === ".") {
                            return;
                          }
                          const val = parseFloat(raw);
                          if (Number.isFinite(val)) {
                            onAnswerGradeChange?.(
                              element.id,
                              Math.min(0.99, Math.max(0.01, val)),
                            );
                          }
                        }}
                        className={cx(
                          "w-20 h-10 rounded-lg border px-3 text-base font-bold text-center outline-none tabular-nums",
                          "border-amber-300 bg-amber-50 text-amber-800",
                          "dark:border-amber-700 dark:bg-amber-900/30 dark:text-amber-200",
                          "focus:ring-2 focus:ring-amber-500/30",
                        )}
                        placeholder="0.5"
                      />
                      <span className="text-sm text-zinc-400 dark:text-zinc-500">
                        / 1
                      </span>
                    </div>
                  </>
                )}
              </div>

              <div className="flex items-center gap-3">
                <span className="text-sm text-zinc-400 dark:text-zinc-500 tabular-nums">
                  x{maxPoints.toFixed(2)} =
                </span>
                <span
                  className={cx(
                    "text-2xl font-bold tabular-nums leading-none",
                    status === "correct"
                      ? "text-emerald-600 dark:text-emerald-400"
                      : status === "partial"
                        ? "text-amber-600 dark:text-amber-400"
                        : status === "incorrect"
                          ? "text-red-600 dark:text-red-400"
                          : "text-zinc-300 dark:text-zinc-600",
                  )}
                >
                  {earnedPoints.toFixed(2)}
                </span>
              </div>
            </div>
          </div>

          <div className="flex items-center">
            <button
              type="button"
              onClick={() => setShowComment((prev) => !prev)}
              className={cx(
                "rounded-lg border px-3 py-1.5 text-sm font-medium transition-colors",
                showComment || gradingInfo.comment
                  ? "border-blue-200 bg-blue-50 text-blue-700 dark:border-blue-900/50 dark:bg-blue-900/20 dark:text-blue-300"
                  : "border-zinc-200 bg-zinc-50 text-zinc-600 hover:bg-zinc-100 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-400 dark:hover:bg-zinc-700",
              )}
            >
              {showComment ? "Скрыть комментарий" : "Комментарий"}
              {!showComment && gradingInfo.comment && " *"}
            </button>
          </div>

          {showComment && (
            <textarea
              value={gradingInfo.comment}
              onChange={(e) =>
                onAnswerCommentChange?.(element.id, e.target.value)
              }
              rows={2}
              placeholder="Комментарий для студента..."
              className={cx(
                "w-full rounded-xl border px-4 py-3 text-sm outline-none resize-y",
                "border-zinc-200 bg-white text-zinc-800",
                "dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-200",
                "placeholder:text-zinc-400 dark:placeholder:text-zinc-500",
                "focus:ring-2 focus:ring-blue-500/20",
              )}
            />
          )}
        </div>
      )}

      {isGradedView && gradingInfo && (
        <div className="mt-4 space-y-2">
          <div className="flex flex-wrap items-center gap-4">
            <span
              className={cx("text-sm font-semibold", gradeStatusColor(grade))}
            >
              {gradeStatusLabel(grade)}
            </span>
            <span className="text-sm tabular-nums text-zinc-600 dark:text-zinc-300">
              <span className={cx("font-bold", gradeStatusColor(grade))}>
                {earnedPoints.toFixed(2)}
              </span>
              <span className="text-zinc-400 dark:text-zinc-500">
                {" "}
                / {maxPoints.toFixed(2)} б.
              </span>
            </span>
          </div>

          {gradingInfo.comment && (
            <div className="rounded-xl bg-zinc-100/80 px-4 py-3 dark:bg-zinc-800/40">
              <div className="text-xs font-semibold uppercase tracking-wider text-zinc-500 dark:text-zinc-400 mb-1">
                Комментарий преподавателя
              </div>
              <div className="text-sm text-zinc-800 dark:text-zinc-200 whitespace-pre-wrap">
                {gradingInfo.comment}
              </div>
            </div>
          )}
        </div>
      )}

      {isTemplateEdit && scoringInfo && (
        <div className="mt-3 flex items-center gap-4 text-sm text-zinc-500 dark:text-zinc-400">
          <div className="flex items-center gap-2">
            <span>Вес:</span>
            <input
              type="number"
              min={0}
              max={20}
              step={1}
              value={element.maxScore ?? 1}
              onChange={(e) => {
                const val = normalizeWeight(e.target.value);
                updateElement(element.id, { maxScore: val });
              }}
              className={cx(
                "w-14 h-7 rounded border px-1 text-sm font-semibold text-center outline-none",
                "border-zinc-300 bg-white text-zinc-700",
                "dark:border-zinc-600 dark:bg-zinc-800 dark:text-zinc-300",
                "focus:ring-2 focus:ring-blue-500/20",
              )}
            />
          </div>
          <span>
            Баллы:{" "}
            <span className="font-semibold">
              {scoringInfo.points.toFixed(2)}
            </span>
          </span>
        </div>
      )}

      {!isTemplateEdit &&
        scoringInfo &&
        !isReportMode &&
        !isGradingMode &&
        !isGradedView && (
          <div className="mt-3 flex items-center gap-4 text-sm text-zinc-500 dark:text-zinc-400">
            <span>
              Вес: <span className="font-semibold">{scoringInfo.weight}</span>
            </span>
            <span>
              Баллы:{" "}
              <span className="font-semibold">
                {scoringInfo.points.toFixed(2)}
              </span>
            </span>
          </div>
        )}
    </div>
  );
});

function showFullGradeOrPrevious(
  isGradingMode: boolean | undefined,
  isGradedView: boolean,
  hasHistoricalAssessment: boolean | undefined,
) {
  return isGradingMode || isGradedView || hasHistoricalAssessment;
}
