from cakrawala.data.providers.ecb_fx import parse_ecb_strength


def test_parse_ecb_strength_builds_supported_currency_changes() -> None:
    xml = """<?xml version="1.0" encoding="UTF-8"?>
    <Envelope xmlns="gesmes" xmlns:x="http://www.ecb.int/vocabulary/2002-08-01/eurofxref">
      <Cube>
        <Cube time="2026-08-18"><Cube currency="USD" rate="1.20"/><Cube currency="JPY" rate="180"/></Cube>
        <Cube time="2026-08-19"><Cube currency="USD" rate="1.18"/><Cube currency="JPY" rate="181"/></Cube>
      </Cube>
    </Envelope>"""
    rows = parse_ecb_strength(xml)
    by_currency = {item.currency: item for item in rows}
    assert by_currency["USD"].change_1d_pct is not None
    assert by_currency["USD"].change_1d_pct > 0
    assert by_currency["JPY"].change_1d_pct is not None
    assert by_currency["JPY"].change_1d_pct < 0
