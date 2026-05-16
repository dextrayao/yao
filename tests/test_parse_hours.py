from scripts.aggregate import parse_hours


def test_integer_hours():
    assert parse_hours("8hr") == 8.0


def test_half_hour():
    assert parse_hours("0.5hr") == 0.5


def test_decimal_hours():
    assert parse_hours("7.5hr") == 7.5


def test_chinese_unit():
    assert parse_hours("8小時") == 8.0


def test_blank_string():
    assert parse_hours("") == 0.0


def test_no_digits():
    assert parse_hours("無") == 0.0


def test_bare_number():
    assert parse_hours("3.5") == 3.5
