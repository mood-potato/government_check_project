from abc import ABC, abstractmethod

class BasePipeline(ABC):
    def __init__(self, extractor, loader, transformer=None):
        self.extractor = extractor
        self.transformer = transformer
        self.loader = loader

    @abstractmethod
    def run(self):
        """
        파이프라인 실행 메서드. 서브클래스에서 정의해야 함.
        """
        pass