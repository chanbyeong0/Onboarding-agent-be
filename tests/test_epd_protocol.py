from app.epd_stt_client.protocol import build_audio_frame, build_config_message, session_id_to_bytes


def test_session_id_to_bytes_hex():
    sid = "abcdef1234567890abcdef1234567890"
    b = session_id_to_bytes(sid)
    assert len(b) == 16
    assert b.hex() == sid


def test_session_id_to_bytes_uuid():
    sid = "12345678-1234-1234-1234-1234567890ab"
    b = session_id_to_bytes(sid)
    assert len(b) == 16


def test_build_audio_frame_layout():
    sid = "abcdef1234567890abcdef1234567890"
    pcm = b"\x01\x02\x03\x04"
    frame = build_audio_frame(sid, pcm)
    assert len(frame) == 16 + 2 + 4
    assert frame[:16].hex() == sid
    assert frame[16:18] == b"\x00\x00"
    assert frame[18:] == pcm


def test_build_audio_frame_tts_status_big_endian():
    sid = "abcdef1234567890abcdef1234567890"
    frame = build_audio_frame(sid, b"", tts_status=0x0102)
    assert frame[16:18] == b"\x01\x02"


def test_build_config_message():
    msg = build_config_message(language="ko")
    assert "mode=agent" in msg
    assert "language=ko" in msg
    assert msg.startswith("min_speech=")
