"""EPD/STT 클라이언트 예외."""


class EpdSttError(Exception):
    """EPD/STT 클라이언트 기본 예외."""


class EpdReadyTimeout(EpdSttError):
    """READY 응답 대기 타임아웃."""


class EpdNotConnected(EpdSttError):
    """연결되지 않은 상태에서 작업 시도."""
