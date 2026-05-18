from typing import Sequence

from answer.graders.base import BaseGrader
from answer.graders.config import GraderConfig, DEFAULT_CONFIG
from answer.schemas import GradingContext, ErrorType


class GraderPipeline:
    def __init__(
            self,
            graders: Sequence[BaseGrader],
            config: GraderConfig = DEFAULT_CONFIG
    ):
        self.graders = list(graders)
        self.config = config

    def run(self, context: GradingContext) -> GradingContext:
        for grader in self.graders:
            if context.should_stop(self.config.early_exit_threshold):
                break

            if context.is_perfect_match:
                break

            if self._should_skip_remaining(context):
                break

            grader.process(context)

        return context

    def _should_skip_remaining(self, context: GradingContext) -> bool:
        return any(e.type == ErrorType.REGEX_NO_MATCH for e in context.errors)