# finstatement/parser.py
"""
Financial Statement Parser

This module provides functionality to extract structured data from financial statement PDFs.
It detects statement type, institution, and extracts key financial data including account 
information, statement period, balances, and transaction history.

Developed by AZdev (https://azdv.co)
"""

import os
import re
import json
from dataclasses import dataclass, asdict, field
from datetime import datetime
from typing import List, Optional, Dict, Any
try:
    import pypdf  # maintained successor to PyPDF2
except ImportError:  # pragma: no cover
    import PyPDF2 as pypdf  # last resort, EOL and unpatched

# Guardrails for untrusted input. A statement parser is pointed at files that
# arrived by email, so an unbounded PdfReader call is a denial of service
# waiting to happen.
MAX_FILE_BYTES = 50 * 1024 * 1024
MAX_PAGES = 500


class StatementParseError(Exception):
    """Raised when a statement cannot be read at all.

    This exists because the alternative is worse. An earlier version of this
    parser caught every exception and returned the string
    "ERROR: Unable to extract text from PDF" as if it were statement text,
    which then parsed to a zero balance and a set of transactions dated today.
    Silence is the wrong default when the output is financial data.
    """


@dataclass
class AccountInfo:
    """Account information extracted from a financial statement."""
    # None when it could not be read, consistent with every other field. The
    # earlier "Unknown" sentinel was returned with no parse_errors entry, so the
    # documented contract said None and the code said otherwise.
    number: Optional[str] = None
    # True when `number` holds only the trailing digits the statement exposed.
    # The earlier code expanded a 4-digit capture into "xxxx-xxxx-xxxx-1234",
    # inventing a 16-digit card shape even for a checking account.
    number_is_partial: bool = False
    name: Optional[str] = None
    institution: Optional[str] = None
    type: Optional[str] = None
    
@dataclass
class Period:
    """Statement period. Either bound is None when it could not be read."""
    start: Optional[datetime] = None
    end: Optional[datetime] = None
    
@dataclass
class Balance:
    """Statement balances. None means not found, which is not the same as 0.00."""
    closing: Optional[float] = None
    opening: Optional[float] = None
    
@dataclass
class Transaction:
    """Financial transaction details."""
    date: datetime
    description: str
    amount: float
    # False when the statement printed a bare figure with no sign. Direction is
    # then unknown from the line alone and must not be assumed by the caller.
    sign_explicit: bool = True
    balance: Optional[float] = None
    category: Optional[str] = None
    
@dataclass
class StatementResult:
    """Comprehensive result of parsing a financial statement."""
    account_info: AccountInfo
    period: Period
    balance: Balance
    transactions: List[Transaction]
    confidence: Dict[str, float] = None
    # Every field this parser could not read, and every transaction line it
    # skipped. Read this before trusting anything above it.
    parse_errors: List[str] = field(default_factory=list)
    
    def to_json(self) -> str:
        """
        Convert the result to a JSON string with proper datetime handling.
        
        Returns:
            str: JSON representation of the parsing result
        """
        def serialize(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            return obj
        
        return json.dumps(asdict(self), default=serialize, indent=2)


class StatementParser:
    """
    Main parser class for financial statements.
    
    This class handles the extraction of structured data from financial statement PDFs.
    It uses pattern recognition to identify statement type, extract account information,
    statement period, balances, and transaction history.
    """
    
    def __init__(self):
        """Initialize the parser with detection patterns."""
        # Regex patterns for detecting financial institutions
        self.institution_patterns = {
            'chase': r'(?i)CHASE|JPMorgan Chase',
            'bofa': r'(?i)Bank\s+of\s+America|BOFA',
            'wellsfargo': r'(?i)Wells\s+Fargo',
            'citi': r'(?i)Citi(?:bank)?',
            'amex': r'(?i)American\s+Express|AMEX',
            'discover': r'(?i)Discover\s+Card',
            'capitalone': r'(?i)Capital\s+One',
            'usbank': r'(?i)U\.?S\.?\s+Bank',
            'pnc': r'(?i)PNC\s+Bank',
            'tdbank': r'(?i)TD\s+Bank',
            'regions': r'(?i)Regions\s+Bank',
            'suntrust': r'(?i)SunTrust|Truist',
            'barclays': r'(?i)Barclays',
            'ally': r'(?i)Ally\s+Bank',
            'schwab': r'(?i)Charles\s+Schwab',
            'fidelity': r'(?i)Fidelity',
            'vanguard': r'(?i)Vanguard',
            # Add more institution patterns as needed
        }
        
        # Transaction category patterns
        self.category_patterns = {
            'dining': r'(?i)restaurant|dining|food|cafe|coffee|starbucks|mcdonalds|chipotle|pizza|burger|taco|sushi',
            'grocery': r'(?i)grocery|groceries|supermarket|market|food|whole foods|trader|safeway|kroger|albertsons|wegmans|publix',
            'transportation': r'(?i)uber|lyft|taxi|cab|transport|transit|metro|subway|train|bus|airline|flight|gas|fuel|chevron|shell|exxon',
            'shopping': r'(?i)amazon|ebay|walmart|target|costco|shop|store|retail|outlet|mall|clothing|apparel',
            'utilities': r'(?i)utility|utilities|electric|water|gas|power|energy|cable|internet|phone|mobile|wireless|verizon|at&t|t-mobile',
            'entertainment': r'(?i)netflix|hulu|spotify|apple|google|movie|theater|cinema|concert|ticket|entertainment',
            'health': r'(?i)medical|doctor|pharmacy|drug|health|healthcare|hospital|clinic|dental|vision|insurance',
            'personal': r'(?i)salon|spa|beauty|barber|hair|nail|gym|fitness',
            'home': r'(?i)home|apartment|rent|lease|mortgage|furniture|decor|improvement|repair|maintenance',
            'subscription': r'(?i)subscription|recurring|monthly|annual|membership|prime|fee',
            'income': r'(?i)deposit|direct deposit|salary|payroll|payment received|income|revenue',
            'transfer': r'(?i)transfer|zelle|venmo|paypal|cash app|wire|ach',
            'withdrawal': r'(?i)withdrawal|atm|cash'
        }

        # Reset per parse() call. Collects every field that could not be read
        # and every transaction row that was dropped.
        self._errors = []
        self._page_errors = []

    def parse(self, file_path: str) -> StatementResult:
        """
        Parse a financial statement PDF and return structured data.
        
        This is the main entry point for parsing a statement. It coordinates the 
        extraction of different components and assembles them into a comprehensive result.
        
        Args:
            file_path: Path to the PDF statement file
            
        Returns:
            StatementResult object containing parsed data
        """
        self._errors = []
        self._page_errors = []

        # Raises StatementParseError if the file cannot be read at all.
        text = self._extract_text(file_path)
        self._errors.extend(self._page_errors)
        
        # Detect institution and statement type
        institution = self._detect_institution(text)
        statement_type = self._detect_statement_type(text)
        
        # Extract core data components
        account_info = self._extract_account_info(text, institution, statement_type)
        period = self._extract_period(text, institution, statement_type)
        balance = self._extract_balance(text, institution, statement_type)
        transactions = self._extract_transactions(text, institution, statement_type, period)
        
        # Calculate confidence scores for each extraction
        confidence = self._calculate_confidence(account_info, period, balance, transactions)
        
        # Construct and return result
        return StatementResult(
            account_info=account_info,
            period=period,
            balance=balance,
            transactions=transactions,
            confidence=confidence,
            parse_errors=list(self._errors),
        )
    
    def _extract_text(self, file_path: str) -> str:
        """
        Extract text from a PDF file, preserving layout where possible.
        
        This method handles multi-page PDFs and attempts to maintain the 
        document structure during extraction.
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            Extracted text content as a string
        """
        try:
            size = os.path.getsize(file_path)
        except OSError as e:
            # This sat outside the try, so a missing path raised
            # FileNotFoundError while the README promised StatementParseError.
            raise StatementParseError(f"could not open {file_path}: {e}") from e
        if size > MAX_FILE_BYTES:
            raise StatementParseError(
                f"{file_path} is {size} bytes, over the {MAX_FILE_BYTES} byte limit")

        text = ""
        page_errors = []
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = pypdf.PdfReader(file)

                if pdf_reader.is_encrypted:
                    # An empty password covers the common case of a statement
                    # encrypted for transport rather than for secrecy.
                    try:
                        pdf_reader.decrypt('')
                    except Exception as e:
                        raise StatementParseError(
                            f"{file_path} is encrypted and could not be opened: {e}")

                pages = len(pdf_reader.pages)
                if pages > MAX_PAGES:
                    raise StatementParseError(
                        f"{file_path} has {pages} pages, over the {MAX_PAGES} page limit")

                for page_num in range(pages):
                    try:
                        page_text = pdf_reader.pages[page_num].extract_text() or ""
                    except Exception as e:
                        # One unreadable page is recoverable. Record it so the
                        # caller knows the text is incomplete.
                        page_errors.append(f"page {page_num + 1} unreadable: {e}")
                        continue

                    if page_num > 0:
                        text += f"\n\n--- PAGE {page_num + 1} ---\n\n"
                    text += page_text
        except StatementParseError:
            raise
        except Exception as e:
            raise StatementParseError(f"could not read {file_path}: {e}") from e

        if not text.strip():
            raise StatementParseError(
                f"no text could be extracted from {file_path}. It may be a scan "
                f"rather than a text PDF, which this parser does not handle.")

        self._page_errors = page_errors
        return text
    
    def _detect_institution(self, text: str) -> str:
        """
        Detect financial institution from statement text.
        
        Args:
            text: Extracted text content from the statement
            
        Returns:
            Institution identifier (e.g., 'chase', 'bofa') or 'unknown'
        """
        for institution, pattern in self.institution_patterns.items():
            if re.search(pattern, text):
                return institution
        return "unknown"
    
    def _detect_statement_type(self, text: str) -> str:
        """
        Detect statement type (bank, credit card, investment).
        
        Args:
            text: Extracted text content from the statement
            
        Returns:
            Statement type identifier (e.g., 'bank', 'credit_card') or 'unknown'
        """
        # Simple heuristics for statement type detection
        if re.search(r'(?i)credit\s+card|credit\s+account|APR|cash\s+advance', text):
            return "credit_card"
        elif re.search(r'(?i)checking|savings|bank\s+statement|deposit|ATM|withdraw', text):
            return "bank"
        elif re.search(r'(?i)investment|portfolio|securities|brokerage|fund|stock|bond', text):
            return "investment"
        else:
            return "unknown"
    
    def _extract_account_info(self, text: str, institution: str, statement_type: str) -> AccountInfo:
        """
        Extract account information from the statement.
        
        Args:
            text: Extracted text content
            institution: Detected institution identifier
            statement_type: Detected statement type
            
        Returns:
            AccountInfo object with extracted account details
        """
        # Default account number if none is found
        account_number = None
        number_is_partial = False
        account_name = None
        
        # Look for account number patterns
        if statement_type == "bank" or statement_type == "credit_card":
            # Common patterns for masked account numbers
            account_patterns = [
                r'(?i)account\s+(?:number|#|no)?[:.\s]+[*xX]+(\d{4})',
                r'(?i)account\s+(?:ending|#)?\s+(?:in|with)?\s+(\d{4})',
                r'(?i)acct\s+[*xX]+(\d{4})',
            ]
            
            for pattern in account_patterns:
                account_matches = re.search(pattern, text)
                if account_matches:
                    # Keep what was actually captured. Do not pad it into a
                    # shape the statement never showed.
                    account_number = account_matches.group(1)
                    number_is_partial = len(account_number) <= 4
                    break
            
            # Try to extract account name if present
            name_patterns = [
                r'(?i)account\s+name:?\s+([A-Z\s]+)',
                r'(?i)primary\s+account\s+holder:?\s+([A-Z\s]+)',
            ]
            
            for pattern in name_patterns:
                name_matches = re.search(pattern, text)
                if name_matches:
                    account_name = name_matches.group(1).strip()
                    break
        
        if account_number is None:
            self._errors.append("no account number found")

        return AccountInfo(
            number=account_number,
            number_is_partial=number_is_partial,
            name=account_name,
            institution=institution,
            type=statement_type
        )
    
    def _extract_period(self, text: str, institution: str, statement_type: str) -> Period:
        """
        Extract statement period (date range).
        
        Args:
            text: Extracted text content
            institution: Detected institution identifier
            statement_type: Detected statement type
            
        Returns:
            Period object with start and end dates
        """
        # Look for date patterns in various formats
        date_pattern = r'(\d{1,2}/\d{1,2}/\d{2,4})'
        period_patterns = [
            rf"(?i)statement\s+period:?\s+{date_pattern}\s+(?:to|through)\s+{date_pattern}",
            rf"(?i)from\s+{date_pattern}\s+to\s+{date_pattern}",
            rf"(?i)billing\s+period:?\s+{date_pattern}\s+(?:to|through)\s+{date_pattern}",
            rf"(?i)(?:period|cycle)(?:\s+covered)?:?\s+{date_pattern}\s*[-–]\s*{date_pattern}",
        ]
        
        for pattern in period_patterns:
            match = re.search(pattern, text)
            if match:
                # Extract start and end dates
                start_date_str = match.group(1)
                end_date_str = match.group(2)
                
                # Parse dates (try different formats)
                start_date = self._parse_date(start_date_str)
                end_date = self._parse_date(end_date_str)
                if start_date is None:
                    self._errors.append(
                        f"statement period start date {start_date_str!r} was not a "
                        f"date this parser recognises")
                if end_date is None:
                    self._errors.append(
                        f"statement period end date {end_date_str!r} was not a "
                        f"date this parser recognises")
                return Period(start=start_date, end=end_date)

        # No period found. Returning the current month here would be a guess
        # presented as a reading, and every downstream date would inherit it.
        self._errors.append("no statement period found")
        return Period(start=None, end=None)

    @staticmethod
    def _resolve_md(month_day: str, period: Period, sep: str = "/") -> Optional[datetime]:
        """
        Resolve a MM/DD transaction date against the statement period.

        Two earlier versions of this were both wrong. The first used
        datetime.now().year, so a 2024 statement parsed in 2026 came back dated
        2026. The second used the period's END year, which is wrong for every
        statement that crosses New Year: on a 15 Dec 2024 to 14 Jan 2025 cycle,
        a 12/20 transaction became 2025-12-20, eleven months into the future.
        December-to-January cycles are routine, so that was not an edge case.

        Both candidate years are tried and the one that lands inside the period
        wins. If neither fits, or the period is unknown, this returns None and
        the caller drops the row rather than guessing a third time.
        """
        if not (period.start and period.end):
            return None
        fmt = f"%m{sep}%d{sep}%Y"
        fits = []
        for year in {period.start.year, period.end.year}:
            try:
                d = datetime.strptime(f"{month_day}{sep}{year}", fmt)
            except ValueError:
                continue
            if period.start <= d <= period.end:
                fits.append(d)
        # Exactly one candidate inside the period is the only unambiguous case.
        return fits[0] if len(fits) == 1 else None

    @staticmethod
    def _parse_date(value: str) -> Optional[datetime]:
        """Parse a date string, or return None. Never guess."""
        for fmt in ("%m/%d/%Y", "%m/%d/%y", "%m-%d-%Y", "%m-%d-%y"):
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue
        return None
    
    def _extract_balance(self, text: str, institution: str, statement_type: str) -> Balance:
        """
        Extract opening and closing balances.
        
        Args:
            text: Extracted text content
            institution: Detected institution identifier
            statement_type: Detected statement type
            
        Returns:
            Balance object with opening and closing balances
        """
        # Pattern for currency amounts
        # Wide enough to capture the sign wherever the statement puts it, and
        # guarded at the end so 1,234.5678 is not silently truncated to 1,234.56.
        # The old pattern read "1,234.56-" as positive and could not read
        # "-$1,234.56" or "($1,234.56)" at all, so an overdraft came back as
        # "no closing balance found".
        amount_pattern = r'\(?[-+]?\$?-?[\d,]+\.\d{2}\)?-?(?![\d])'
        
        # Look for closing balance patterns based on statement type
        closing_patterns = [
            rf"(?i)closing\s+balance:?\s+({amount_pattern})",
            rf"(?i)ending\s+balance:?\s+({amount_pattern})",
            rf"(?i)new\s+balance:?\s+({amount_pattern})",
        ]
        
        # For credit cards, add more specific patterns
        if statement_type == "credit_card":
            closing_patterns.extend([
                rf"(?i)new\s+balance:?\s+({amount_pattern})",
                rf"(?i)total\s+balance:?\s+({amount_pattern})",
                rf"(?i)statement\s+balance:?\s+({amount_pattern})",
            ])
        
        # None rather than 0.0. A statement that genuinely closed at zero and a
        # statement this parser could not read are different facts, and a
        # reconciliation that cannot tell them apart is worse than no answer.
        closing_balance = None
        for pattern in closing_patterns:
            match = re.search(pattern, text)
            if match:
                # Extract and clean the amount string
                amount_str = match.group(1)
                parsed = self._parse_amount(amount_str)
                if parsed is None:
                    continue
                closing_balance = parsed[0]
                break
        
        # Look for opening balance patterns
        opening_patterns = [
            rf"(?i)opening\s+balance:?\s+({amount_pattern})",
            rf"(?i)previous\s+balance:?\s+({amount_pattern})",
            rf"(?i)beginning\s+balance:?\s+({amount_pattern})",
            # Balance forward is what carries in from the prior period, so it is
            # an opening figure. It was previously read as the closing balance.
            rf"(?i)balance\s+forward:?\s+({amount_pattern})",
            rf"(?i)balance\s+(?:from|as of)\s+last\s+statement:?\s+({amount_pattern})",
        ]
        
        opening_balance = None
        for pattern in opening_patterns:
            match = re.search(pattern, text)
            if match:
                amount_str = match.group(1)
                parsed = self._parse_amount(amount_str)
                if parsed is None:
                    continue
                opening_balance = parsed[0]
                break
        
        if closing_balance is None:
            self._errors.append("no closing balance found")
        if opening_balance is None:
            self._errors.append("no opening balance found")
        return Balance(closing=closing_balance, opening=opening_balance)
    
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

    def _calculate_confidence(self, account_info, period, balance, transactions) -> Dict[str, float]:
        """
        Calculate confidence scores for extracted data.
        
        The confidence score indicates how reliable the extracted information is.
        Higher scores (closer to 1.0) indicate higher confidence.
        
        Args:
            account_info: Extracted account information
            period: Extracted statement period
            balance: Extracted balances
            transactions: Extracted transactions
            
        Returns:
            Dictionary of confidence scores for each component and overall
        """
        confidence = {}

        # Every score below reflects what was actually read. The previous version
        # scored a fabricated 0.00 closing balance at 0.8, and scored thirty
        # transactions all stamped with today's date at 0.9, because the score
        # was a count rather than a measure of what was known.
        # 0.0 rather than 0.3 when the number was never found, so the invariant
        # holds across every field: nothing read means no confidence.
        confidence["account_info"] = 0.9 if account_info.number is not None else 0.0

        if period.start is None or period.end is None:
            confidence["period"] = 0.0
        else:
            confidence["period"] = 0.9

        if balance.closing is None:
            # Nothing was read. Not a zero balance, no balance.
            confidence["balance"] = 0.0
        elif balance.opening is None:
            confidence["balance"] = 0.6
        else:
            confidence["balance"] = 0.9

        if not transactions:
            confidence["transactions"] = 0.0
        else:
            # Count alone says nothing about correctness, so cap it and let the
            # dropped-row count in parse_errors carry the real signal.
            base = min(0.9, 0.4 + len(transactions) * 0.02)
            dropped = sum(1 for e in self._errors if e.startswith("skipped transaction"))
            kept = len(transactions)
            confidence["transactions"] = round(base * (kept / (kept + dropped)), 2)

        confidence["overall"] = round(
            sum(confidence[k] for k in ("account_info", "period", "balance", "transactions")) / 4, 2)

        return confidence
        
    def _categorize_transaction(self, description: str) -> Optional[str]:
        """
        Categorize a transaction based on its description.
        
        Args:
            description: Transaction description text
            
        Returns:
            Category name or None if no category matches
        """
        # Try to match description against category patterns
        for category, pattern in self.category_patterns.items():
            if re.search(pattern, description, re.IGNORECASE):
                return category
                
        # Special case for income - if amount is positive and large
        if 'deposit' in description.lower() or 'credit' in description.lower():
            return 'income'
            
        # Default to None if no category matches
        return None

# Main package interface
def parse(file_path: str, debug: bool = False) -> StatementResult:
    """
    Parse a financial statement PDF and return structured data.
    
    This is the main entry point for using the library.
    
    Args:
        file_path: Path to the PDF statement file
        debug: If True, enables verbose logging during parsing
        
    Returns:
        StatementResult object containing parsed data
    """
    if debug:
        import logging
        logging.basicConfig(level=logging.DEBUG)
        logger = logging.getLogger("finstatement")
        logger.debug(f"Parsing file: {file_path}")
    
    parser = StatementParser()
    return parser.parse(file_path)

def batch_parse(file_paths: List[str], parallel: bool = True,
                max_workers: int = None) -> Dict[str, Any]:
    """
    Parse many statements. Every input appears in the result.

    Failures used to be caught, printed to stdout and omitted from the returned
    dict, so four inputs could return one result with no programmatic signal
    that three had gone. For a reconciliation job that is worse than a crash,
    because it is invisible. Failures now come back as the StatementParseError
    instance keyed by the same path, so isinstance(v, StatementParseError)
    separates them and no input is ever silently absent.
    """
    results: Dict[str, Any] = {}

    def run(path):
        try:
            return path, StatementParser().parse(path)
        except StatementParseError as e:
            return path, e
        except Exception as e:  # a parser bug must not vanish either
            return path, StatementParseError(f"unexpected failure on {path}: {e}")

    if parallel and len(file_paths) > 1:
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
            for path, outcome in pool.map(run, file_paths):
                results[path] = outcome
    else:
        for path in file_paths:
            _, outcome = run(path)
            results[path] = outcome

    return results
