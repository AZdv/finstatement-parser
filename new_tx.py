    # Amounts as they appear on US statements. Ordered longest-first so the
    # parenthesised and trailing-minus forms win before the bare form matches
    # their inner digits.
    _AMOUNT_FORMS = [
        (re.compile(r'^\((\$?[\d,]+\.\d{2})\)$'), -1),      # (1,234.56)  accounting negative
        (re.compile(r'^-\$?([\d,]+\.\d{2})$'), -1),          # -$1,234.56
        (re.compile(r'^\$-([\d,]+\.\d{2})$'), -1),           # $-1,234.56
        (re.compile(r'^\$?([\d,]+\.\d{2})-$'), -1),          # 1,234.56-   trailing minus
        (re.compile(r'^\+\$?([\d,]+\.\d{2})$'), 1),          # +$1,234.56
        (re.compile(r'^\$?([\d,]+\.\d{2})$'), 0),            # 1,234.56    no explicit sign
    ]

    # A date at the start of a line. No \s inside any class, so there is no
    # lazy-class-then-\s+ backtracking path. The previous patterns took cubic
    # time and ~2KB of whitespace after a date token could pin a core.
    _LINE_DATE = re.compile(r'^\s*(\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?)\s+(.*)$')

    @classmethod
    def _parse_amount(cls, token: str):
        """
        Return (value, sign_explicit) or None.

        sign_explicit is False when the statement wrote a bare figure. Direction
        is then genuinely unknown from the line alone, because many layouts put
        charges and credits in separate columns that flatten into one text run.
        The earlier code guessed, and guessed inconsistently by institution: Amex
        charges were forced negative by a branch that returned an already
        negative value unchanged, so charges and credits ended up with the same
        sign and a month of charges plus an equal payment netted to double the
        charges instead of zero.
        """
        token = token.strip()
        for pattern, sign in cls._AMOUNT_FORMS:
            m = pattern.match(token)
            if not m:
                continue
            try:
                value = float(m.group(1).replace('$', '').replace(',', ''))
            except ValueError:
                return None
            if sign == 0:
                return value, False
            return value * sign, True
        return None

    def _extract_transactions(self, text: str, institution: str, statement_type: str,
                              period: Period) -> List[Transaction]:
        """
        Extract transactions, one line at a time.

        Line-anchored on purpose. The previous implementation used patterns whose
        description class contained \\s, which matches newlines, so a match could
        span arbitrary line breaks. It assembled transactions that did not exist:
        a date from one line, a description from two others and an amount from a
        fourth, returned with a category and an empty parse_errors. Anchoring per
        line makes that impossible rather than unlikely.
        """
        transactions = []

        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line or line.startswith('---'):
                continue

            m = self._LINE_DATE.match(line)
            if not m:
                continue
            date_str, remainder = m.group(1), m.group(2).strip()
            if not remainder:
                continue

            # The amount is the last whitespace-separated token on the line.
            parts = remainder.rsplit(None, 1)
            if len(parts) != 2:
                continue
            description, amount_token = parts
            description = description.strip(' .:\t')
            if not description:
                continue

            parsed = self._parse_amount(amount_token)
            if parsed is None:
                continue  # not a transaction line, e.g. a column header
            amount, sign_explicit = parsed

            date = self._resolve_date_token(date_str, period)
            if date is None:
                self._errors.append(
                    f"skipped transaction {date_str!r} {description[:40]!r}: the date "
                    f"could not be placed unambiguously inside the statement period")
                continue

            transactions.append(Transaction(
                date=date,
                description=description,
                amount=amount,
                sign_explicit=sign_explicit,
                category=self._categorize_transaction(description),
            ))

        if not transactions:
            self._errors.append("no transactions found")
        return transactions

    def _resolve_date_token(self, token: str, period: Period) -> Optional[datetime]:
        """Resolve a date token that may or may not carry a year."""
        sep = '-' if '-' in token else '/'
        parts = token.split(sep)
        if len(parts) == 3:
            return self._parse_date(token.replace('-', '/'))
        if len(parts) == 2:
            return self._resolve_md(token, period, sep)
        return None
