from app.epd_stt_client.models import EpdResponse, decode_unicode_escapes


def test_decode_unicode_escapes_korean():
    assert decode_unicode_escapes("\\uc548\\ub155\\ud558\\uc138\\uc694") == "안녕하세요"


def test_decode_unicode_escapes_passthrough():
    assert decode_unicode_escapes("hello") == "hello"
    assert decode_unicode_escapes(None) is None


def test_epd_response_is_end_with_stt():
    r = EpdResponse.from_dict({"status": 3, "text": "hello", "confidence": 0.9})
    assert r.is_end_with_stt

    r2 = EpdResponse.from_dict({"status": 3, "text": "", "confidence": 0.9})
    assert not r2.is_end_with_stt

    r3 = EpdResponse.from_dict({"status": 1, "text": "hello"})
    assert not r3.is_end_with_stt
