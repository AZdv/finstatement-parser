"""
The contract this library actually sells: it does not invent financial data.

Every test here corresponds to a defect that shipped publicly. They are written
as regression tests rather than as coverage, because each one was found by a
reviewer after a previous round was called fixed. If one of these fails, the
library is lying to somebody about their money.
"""
import os
import tempfile
from datetime import datetime

import pytest

from finstatement.parser import (
    StatementParser, StatementParseError, Period, Balance, AccountInfo,
)


@pytest.fixture
def parser():
    p = StatementParser()
    p._errors = []
    return p


# --- it raises rather than returning something plausible --------------------

def test_corrupt_pdf_raises_rather_than_returning_zeroes():
    """Used to return "ERROR: Unable to extract text from PDF" as statement text,
    which then parsed to a zero balance and transactions dated today."""
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(b"this is not a pdf")
        path = f.name
    try:
        with pytest.raises(StatementParseError):
            StatementParser().parse(path)
    finally:
        os.unlink(path)


def test_missing_file_raises_the_documented_exception():
    """os.path.getsize sat outside the try, so this leaked FileNotFoundError
    while the README promised StatementParseError."""
    with pytest.raises(StatementParseError):
        StatementParser().parse("/nonexistent/nowhere.pdf")


# --- unknown means unknown, never a plausible default -----------------------

def test_missing_period_is_none_not_the_current_month(parser):
    period = parser._extract_period("no dates in here", "chase", "bank")
    assert period.start is None and period.end is None
    assert any("period" in e for e in parser._errors)


def test_missing_closing_balance_is_none_not_zero(parser):
    balance = parser._extract_balance("nothing resembling a balance", "chase", "bank")
    assert balance.closing is None, "0.0 is a balance a real account can have"
    assert any("closing balance" in e for e in parser._errors)


def test_missing_account_number_is_none_not_the_string_unknown(parser):
    info = parser._extract_account_info("no account number", "chase", "bank")
    assert info.number is None
    assert any("account number" in e for e in parser._errors)


def test_partial_account_number_is_not_padded_into_a_card_shape(parser):
    """Used to expand a 4-digit capture into xxxx-xxxx-xxxx-1234, inventing a
    16-digit card shape even for a checking account."""
    info = parser._extract_account_info("Account Number: ****1234\n", "chase", "bank")
    if info.number is not None:
        assert "xxxx" not in info.number
        assert info.number_is_partial is True


# --- dates come from the statement, never from the clock --------------------

def test_md_dates_resolve_inside_a_period_that_crosses_new_year(parser):
    """Two earlier versions were wrong here: first datetime.now().year, then the
    period's END year, which put December transactions eleven months ahead."""
    period = Period(datetime(2024, 12, 15), datetime(2025, 1, 14))
    text = "TRANSACTIONS\n12/20 STARBUCKS STORE 123 $12.50\n01/05 AMAZON COM $40.00\n"
    txs = parser._extract_transactions(text, "chase", "credit_card", period)
    assert len(txs) == 2
    for tx in txs:
        assert period.start <= tx.date <= period.end, f"{tx.date} outside the statement"
    assert {t.date.year for t in txs} == {2024, 2025}


def test_md_dates_are_dropped_when_the_period_is_unknown(parser):
    text = "TRANSACTIONS\n12/20 STARBUCKS $12.50\n"
    txs = parser._extract_transactions(text, "chase", "credit_card", Period(None, None))
    assert txs == []
    assert any("skipped transaction" in e for e in parser._errors)


# --- transactions are read, never assembled ---------------------------------

def test_does_not_assemble_a_transaction_from_unrelated_lines(parser):
    """The old description class contained \\s, which matches newlines, so a
    match could take a date from one line, a description from two others and an
    amount from a fourth and return it as a real transaction."""
    text = (
        "ACCOUNT ACTIVITY\n"
        "Reference number 01/02\n"
        "Customer service hours Monday to Friday\n"
        "Annual fee assessed 95.00\n"
    )
    period = Period(datetime(2025, 1, 1), datetime(2025, 1, 31))
    txs = parser._extract_transactions(text, "citi", "credit_card", period)
    for tx in txs:
        assert "\n" not in tx.description
        assert "Customer service hours" not in tx.description


@pytest.mark.parametrize("token,expected,explicit", [
    ("$1,234.56", 1234.56, False),
    ("-$1,234.56", -1234.56, True),
    ("$-1,234.56", -1234.56, True),
    ("($1,234.56)", -1234.56, True),
    ("1,234.56-", -1234.56, True),
    ("+$1,234.56", 1234.56, True),
])
def test_amount_signs_are_read_not_guessed(token, expected, explicit):
    """The Amex branch negated only unsigned values, so charges and credits came
    out with the same sign and a month of charges plus an equal payment netted
    to double the charges instead of zero."""
    value, sign_explicit = StatementParser._parse_amount(token)
    assert value == pytest.approx(expected)
    assert sign_explicit is explicit


def test_over_precise_amount_is_not_silently_truncated():
    """1,234.5678 used to come back as 1234.56 with no error recorded."""
    assert StatementParser._parse_amount("$1,234.5678") is None


# --- adversarial input terminates -------------------------------------------

def test_whitespace_run_after_a_date_does_not_hang(parser):
    """~2KB of whitespace after a date token took cubic time in the old
    patterns and could pin a core. batch_parse across cores took the host."""
    import time
    text = "TRANSACTIONS\n01/15 " + " " * 4000 + "no amount here\n"
    period = Period(datetime(2025, 1, 1), datetime(2025, 1, 31))
    started = time.monotonic()
    parser._extract_transactions(text, "chase", "credit_card", period)
    assert time.monotonic() - started < 2.0


def test_impossible_date_does_not_abort_the_whole_parse(parser):
    """13/45 and 02/30 raised a bare ValueError out of parse() in three of the
    four institution branches, and under batch_parse that deleted the file from
    the results entirely."""
    period = Period(datetime(2025, 1, 1), datetime(2025, 12, 31))
    text = "TRANSACTIONS\n13/45 SOME MERCHANT $10.00\n01/15 REAL ONE $20.00\n"
    txs = parser._extract_transactions(text, "bofa", "bank", period)
    assert any(t.description.startswith("REAL ONE") for t in txs)


# --- balances -----------------------------------------------------------------

def test_balance_forward_is_an_opening_balance(parser):
    """It was the fourth CLOSING pattern. Balance forward is what carries in
    from the prior period."""
    balance = parser._extract_balance("Balance Forward: $500.00", "chase", "bank")
    assert balance.opening == pytest.approx(500.00)
    assert balance.closing is None


def test_overdraft_closing_balance_is_readable(parser):
    """The old amount pattern could not match a negative, so an overdrawn
    account reported "no closing balance found"."""
    balance = parser._extract_balance("Ending Balance: -$1,234.56", "chase", "bank")
    assert balance.closing == pytest.approx(-1234.56)


# --- confidence reflects what was read ---------------------------------------

def test_confidence_is_zero_when_nothing_was_read(parser):
    scores = parser._calculate_confidence(
        AccountInfo(), Period(None, None), Balance(closing=None), [])
    assert scores["overall"] == 0.0
    for field in ("account_info", "period", "balance", "transactions"):
        assert scores[field] == 0.0


# --- batch ---------------------------------------------------------------------

def test_batch_parse_reports_every_input_including_failures():
    """Failures were caught, printed and omitted, so four inputs could return
    one result with no programmatic signal."""
    from finstatement.parser import batch_parse
    paths = []
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(b"not a pdf")
        paths.append(f.name)
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        paths.append(f.name)
    paths.append("/nonexistent/nowhere.pdf")
    try:
        results = batch_parse(paths, parallel=False)
        assert set(results) == set(paths), "an input vanished from the results"
        assert all(isinstance(v, StatementParseError) for v in results.values())
    finally:
        for p in paths[:2]:
            os.unlink(p)


# --- gaps a final pre-publication review found -------------------------------

def test_bare_amounts_are_flagged_as_unsigned(parser):
    """The README teaches callers to sum tx.amount. On layouts that print
    charges unsigned that would be silently wrong, so the flag has to be set."""
    period = Period(datetime(2025, 1, 1), datetime(2025, 1, 31))
    txs = parser._extract_transactions(
        "TRANSACTIONS\n01/15 SOME MERCHANT 1,234.56\n", "chase", "credit_card", period)
    assert len(txs) == 1
    assert txs[0].sign_explicit is False, "a bare figure must not look signed"


def test_signed_amounts_are_flagged_as_signed(parser):
    period = Period(datetime(2025, 1, 1), datetime(2025, 1, 31))
    txs = parser._extract_transactions(
        "TRANSACTIONS\n01/15 REFUND -$40.00\n", "chase", "credit_card", period)
    assert txs[0].sign_explicit is True
    assert txs[0].amount == pytest.approx(-40.00)


def test_full_dates_outside_the_period_are_rejected(parser):
    """A full date used to bypass the period check entirely, so a line from a
    summary block or a prior statement could enter the transaction list."""
    period = Period(datetime(2025, 1, 1), datetime(2025, 1, 31))
    txs = parser._extract_transactions(
        "TRANSACTIONS\n06/15/2019 ANCIENT CHARGE $10.00\n01/15/2025 REAL ONE $20.00\n",
        "bofa", "bank", period)
    assert [t.description for t in txs] == ["REAL ONE"]


def test_file_size_bound_is_enforced(parser, monkeypatch, tmp_path):
    """The README promises a 50 MB bound. Promised is not the same as tested."""
    from finstatement import parser as parser_module
    monkeypatch.setattr(parser_module, "MAX_FILE_BYTES", 10)
    big = tmp_path / "big.pdf"
    big.write_bytes(b"x" * 100)
    with pytest.raises(StatementParseError, match="over the"):
        StatementParser().parse(str(big))


def test_page_count_bound_is_enforced(monkeypatch, tmp_path):
    """The README promises a 500-page bound."""
    reportlab = pytest.importorskip("reportlab.pdfgen.canvas")
    from finstatement import parser as parser_module
    monkeypatch.setattr(parser_module, "MAX_PAGES", 2)
    path = tmp_path / "many.pdf"
    c = reportlab.Canvas(str(path))
    for _ in range(4):
        c.drawString(100, 700, "page")
        c.showPage()
    c.save()
    with pytest.raises(StatementParseError, match="page limit"):
        StatementParser().parse(str(path))
