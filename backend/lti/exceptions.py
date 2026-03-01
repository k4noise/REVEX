class LisNotSupportedException(Exception):
    """Исключение, возникающее при отсутствии доступа к службе LTI 1.3 LIS"""

    def __init__(self, name: str):
        super().__init__(f"Служба {name} недоступна")


class NrpsNotSupportedException(LisNotSupportedException):
    """Исключение, возникающее при отсутствии доступа к службе имен и ролей LTI 1.3"""

    def __init__(self):
        super().__init__("имен и ролей (NRPS)")
