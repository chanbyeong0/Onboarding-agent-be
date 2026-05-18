from app.epd_stt_client._filters import is_noise


def test_empty_is_noise():
    assert is_noise("", 0.9)
    assert is_noise(None, 0.9)
    assert is_noise("   ", 0.9)


def test_low_confidence_is_noise():
    assert is_noise("hello", 0.1)


def test_single_char_noise_policy():
    assert is_noise("아", 0.9)
    assert not is_noise("응", 0.9)
    assert not is_noise("왜", 0.9)
    assert not is_noise("뭐", 0.9)
