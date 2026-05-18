from abc import ABC, abstractmethod

from answer.graders.config import GraderConfig, DEFAULT_CONFIG
from answer.schemas import GradingContext


class BaseGrader(ABC):
    def __init__(self, config: GraderConfig = DEFAULT_CONFIG):
        self.config = config

    @abstractmethod
    def process(self, context: GradingContext) -> None:
        pass