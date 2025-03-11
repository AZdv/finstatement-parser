# finstatement/parser.py
"""
Financial Statement Parser

This module provides functionality to extract structured data from financial statement PDFs.
It detects statement type, institution, and extracts key financial data including account 
information, statement period, balances, and transaction history.

Developed by AZdev (https://azdv.co)
"""

import re
import json
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import List, Optional, Dict, Any
import PyPDF2  # For PDF text extraction

@dataclass
class AccountInfo:
    """Account information extracted from a financial statement."""
    number: str
    name: Optional[str] = None
    institution: Optional[str] = None
    type: Optional[str] = None
    
@dataclass
class Period:
    """Statement period with start and end dates."""
    start: datetime
    end: datetime
    
@dataclass
class Balance:
    """Statement balances."""
    closing: float
    opening: Optional[float] = None
    
@dataclass
class Transaction:
    """Financial transaction details."""
    date: datetime
    description: str
    amount: float
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
        # Extract text from PDF
        text = self._extract_text(file_path)
        
        # Detect institution and statement type
        institution = self._detect_institution(text)
        statement_type = self._detect_statement_type(text)
        
        # Extract core data components
        account_info = self._extract_account_info(text, institution, statement_type)
        period = self._extract_period(text, institution, statement_type)
        balance = self._extract_balance(text, institution, statement_type)
        transactions = self._extract_transactions(text, institution, statement_type)
        
        # Calculate confidence scores for each extraction
        confidence = self._calculate_confidence(account_info, period, balance, transactions)
        
        # Construct and return result
        return StatementResult(
            account_info=account_info,
            period=period,
            balance=balance,
            transactions=transactions,
            confidence=confidence
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
        text = ""
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                # Check if PDF is encrypted and try to decrypt with empty password
                if pdf_reader.is_encrypted:
                    try:
                        pdf_reader.decrypt('')
                    except:
                        # If decryption fails, we'll work with whatever we can extract
                        pass
                
                # Extract text from each page with page markers for debugging
                for page_num in range(len(pdf_reader.pages)):
                    page = pdf_reader.pages[page_num]
                    page_text = page.extract_text()
                    
                    # Add page delimiter for multi-page analysis
                    if page_num > 0:
                        text += f"\n\n--- PAGE {page_num + 1} ---\n\n"
                    
                    text += page_text
        except Exception as e:
            # Provide informative error but continue with partial extraction if possible
            print(f"Warning: Error extracting text from PDF: {e}")
            if not text:
                text = "ERROR: Unable to extract text from PDF"
        
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
        account_number = "Unknown"
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
                    account_number = f"xxxx-xxxx-xxxx-{account_matches.group(1)}"
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
        
        return AccountInfo(
            number=account_number,
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
                try:
                    start_date = datetime.strptime(start_date_str, "%m/%d/%Y")
                except ValueError:
                    try:
                        start_date = datetime.strptime(start_date_str, "%m/%d/%y")
                    except ValueError:
                        start_date = datetime.now()  # Fallback
                    
                try:
                    end_date = datetime.strptime(end_date_str, "%m/%d/%Y")
                except ValueError:
                    try:
                        end_date = datetime.strptime(end_date_str, "%m/%d/%y")
                    except ValueError:
                        end_date = datetime.now()  # Fallback
                
                return Period(start=start_date, end=end_date)
        
        # Fallback to current month if no period found
        today = datetime.now()
        start_date = datetime(today.year, today.month, 1)
        return Period(start=start_date, end=today)
    
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
        amount_pattern = r'[\$]?[\d,]+\.\d{2}'
        
        # Look for closing balance patterns based on statement type
        closing_patterns = [
            rf"(?i)closing\s+balance:?\s+({amount_pattern})",
            rf"(?i)ending\s+balance:?\s+({amount_pattern})",
            rf"(?i)new\s+balance:?\s+({amount_pattern})",
            rf"(?i)balance\s+forward:?\s+({amount_pattern})",
        ]
        
        # For credit cards, add more specific patterns
        if statement_type == "credit_card":
            closing_patterns.extend([
                rf"(?i)new\s+balance:?\s+({amount_pattern})",
                rf"(?i)total\s+balance:?\s+({amount_pattern})",
                rf"(?i)statement\s+balance:?\s+({amount_pattern})",
            ])
        
        closing_balance = 0.0
        for pattern in closing_patterns:
            match = re.search(pattern, text)
            if match:
                # Extract and clean the amount string
                amount_str = match.group(1)
                closing_balance = float(amount_str.replace('$', '').replace(',', ''))
                break
        
        # Look for opening balance patterns
        opening_patterns = [
            rf"(?i)opening\s+balance:?\s+({amount_pattern})",
            rf"(?i)previous\s+balance:?\s+({amount_pattern})",
            rf"(?i)beginning\s+balance:?\s+({amount_pattern})",
            rf"(?i)balance\s+(?:from|as of)\s+last\s+statement:?\s+({amount_pattern})",
        ]
        
        opening_balance = None
        for pattern in opening_patterns:
            match = re.search(pattern, text)
            if match:
                amount_str = match.group(1)
                opening_balance = float(amount_str.replace('$', '').replace(',', ''))
                break
        
        return Balance(closing=closing_balance, opening=opening_balance)
    
    def _extract_transactions(self, text: str, institution: str, statement_type: str) -> List[Transaction]:
        """
        Extract transaction list from the statement.
        
        This method uses institution-specific patterns where available, falling back
        to generic patterns for unknown institutions. It also attempts to categorize
        transactions based on their descriptions.
        
        Args:
            text: Extracted text content
            institution: Detected institution identifier
            statement_type: Detected statement type
            
        Returns:
            List of Transaction objects containing parsed transactions
        """
        # Transaction category patterns
        category_patterns = {
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
        transactions = []
        
        # Try to find the transactions section using common headers
        transaction_headers = [
            r'(?i)transactions?',
            r'(?i)account\s+activity',
            r'(?i)payments\s+and\s+(?:other\s+)?credits',
            r'(?i)purchases\s+and\s+(?:other\s+)?charges',
        ]
        
        # Try to find transaction section boundaries
        transaction_section = text
        for header in transaction_headers:
            # Look for the transactions section followed by common section endings
            match = re.search(f"{header}.*?(?=SUMMARY|TOTAL|BALANCE|STATEMENT|INFORMATION|$)", 
                             text, re.DOTALL | re.IGNORECASE)
            if match:
                transaction_section = match.group(0)
                break
        
        # Different formats for different institutions
        if institution == "chase" and statement_type == "credit_card":
            # Chase credit card format: DATE DESCRIPTION AMOUNT
            tx_pattern = r'(\d{2}/\d{2})\s+([A-Za-z0-9\s.,&\'"-]+?)\s+([-+]?\$[\d,]+\.\d{2})'
            for match in re.finditer(tx_pattern, transaction_section):
                date_str, description, amount_str = match.groups()
                
                # Parse date (assuming current year)
                current_year = datetime.now().year
                date = datetime.strptime(f"{date_str}/{current_year}", "%m/%d/%Y")
                
                # Parse amount
                amount = float(amount_str.replace('$', '').replace(',', ''))
                
                # Add transaction
                transactions.append(Transaction(
                    date=date,
                    description=description.strip(),
                    amount=amount
                ))
        elif institution == "bofa" and statement_type == "bank":
            # Bank of America checking format
            tx_pattern = r'(\d{2}/\d{2}/\d{2,4})\s+([A-Za-z0-9\s.,&\'"-]+?)\s+([-+]?\$[\d,]+\.\d{2})'
            for match in re.finditer(tx_pattern, transaction_section):
                date_str, description, amount_str = match.groups()
                
                # Parse date
                try:
                    date = datetime.strptime(date_str, "%m/%d/%Y")
                except ValueError:
                    date = datetime.strptime(date_str, "%m/%d/%y")
                
                # Parse amount
                amount = float(amount_str.replace('$', '').replace(',', ''))
                
                # Add transaction
                transactions.append(Transaction(
                    date=date,
                    description=description.strip(),
                    amount=amount
                ))
        elif institution == "amex" and statement_type == "credit_card":
            # American Express format
            tx_pattern = r'(\d{2}/\d{2}/\d{2,4})\s+([A-Za-z0-9\s.,&\'"-]+?)\s+([-+]?\$[\d,]+\.\d{2})'
            for match in re.finditer(tx_pattern, transaction_section):
                date_str, description, amount_str = match.groups()
                
                # Parse date
                try:
                    date = datetime.strptime(date_str, "%m/%d/%Y")
                except ValueError:
                    date = datetime.strptime(date_str, "%m/%d/%y")
                
                # Parse amount (Amex typically shows charges as positive)
                amount_str = amount_str.replace('$', '').replace(',', '')
                amount = -float(amount_str) if not amount_str.startswith('-') else float(amount_str)
                
                # Add transaction
                transactions.append(Transaction(
                    date=date,
                    description=description.strip(),
                    amount=amount
                ))
        else:
            # Generic approach for other statement types
            # Looking for date-like strings followed by description and amount
            date_patterns = [
                r'(\d{1,2}/\d{1,2}(?:/\d{2,4})?)',  # MM/DD or MM/DD/YYYY
                r'(\d{1,2}-\d{1,2}(?:-\d{2,4})?)',  # MM-DD or MM-DD-YYYY
            ]
            
            amount_pattern = r'([-+]?\$?[\d,]+\.\d{2})'
            
            for date_pattern in date_patterns:
                # Look for pattern: DATE DESCRIPTION AMOUNT
                combined_pattern = f"{date_pattern}\\s+([A-Za-z0-9\\s.,&'\"()-]+?)\\s+{amount_pattern}"
                for match in re.finditer(combined_pattern, transaction_section):
                    date_str, description, amount_str = match.groups()
                    
                    # Parse date
                    try:
                        # Try different date formats
                        if '/' in date_str:
                            if len(date_str.split('/')) > 2:
                                # Has year component
                                try:
                                    date = datetime.strptime(date_str, "%m/%d/%Y")
                                except ValueError:
                                    date = datetime.strptime(date_str, "%m/%d/%y")
                            else:
                                # No year, assume current year
                                current_year = datetime.now().year
                                date = datetime.strptime(f"{date_str}/{current_year}", "%m/%d/%Y")
                        else:
                            # Handle dashes
                            if len(date_str.split('-')) > 2:
                                # Has year component
                                try:
                                    date = datetime.strptime(date_str, "%m-%d-%Y")
                                except ValueError:
                                    date = datetime.strptime(date_str, "%m-%d-%y")
                            else:
                                # No year, assume current year
                                current_year = datetime.now().year
                                date = datetime.strptime(f"{date_str}-{current_year}", "%m-%d-%Y")
                                
                    except ValueError:
                        # If date parsing fails, use today's date as fallback
                        date = datetime.now()
                    
                    # Parse amount
                    amount_str = amount_str.replace('$', '').replace(',', '')
                    try:
                        amount = float(amount_str)
                    except ValueError:
                        continue  # Skip if amount can't be parsed
                    
                    # Categorize transaction
                    category = self._categorize_transaction(description.strip())
                    
                    # Add transaction
                    transactions.append(Transaction(
                        date=date,
                        description=description.strip(),
                        amount=amount,
                        category=category
                    ))
        
        return transactions
    
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
        
        # Account info confidence
        confidence["account_info"] = 0.9 if account_info.number != "Unknown" else 0.3
        
        # Period confidence
        today = datetime.now()
        is_default_period = (period.start.year == today.year and 
                            period.start.month == today.month and 
                            period.start.day == 1)
        confidence["period"] = 0.3 if is_default_period else 0.9
        
        # Balance confidence
        confidence["balance"] = 0.8 if balance.opening is not None else 0.5
        
        # Transaction confidence based on count
        if len(transactions) > 0:
            confidence["transactions"] = min(0.9, 0.3 + (len(transactions) * 0.02))
        else:
            confidence["transactions"] = 0.1
        
        # Overall confidence (weighted average)
        confidence["overall"] = (confidence["account_info"] + 
                                confidence["period"] + 
                                confidence["balance"] + 
                                confidence["transactions"]) / 4
        
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

def batch_parse(file_paths: List[str], parallel: bool = True, max_workers: int = None) -> Dict[str, StatementResult]:
    """
    Parse multiple statement PDFs in batch, optionally in parallel.
    
    Args:
        file_paths: List of paths to PDF statement files
        parallel: If True, process files in parallel
        max_workers: Maximum number of parallel workers (defaults to CPU count)
        
    Returns:
        Dictionary mapping file paths to their corresponding StatementResult objects
    """
    results = {}
    
    if parallel:
        import concurrent.futures
        with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
            # Submit all parsing tasks
            future_to_path = {executor.submit(parse, path): path for path in file_paths}
            
            # Collect results as they complete
            for future in concurrent.futures.as_completed(future_to_path):
                path = future_to_path[future]
                try:
                    results[path] = future.result()
                except Exception as e:
                    print(f"Error processing {path}: {e}")
    else:
        # Process sequentially
        for path in file_paths:
            try:
                results[path] = parse(path)
            except Exception as e:
                print(f"Error processing {path}: {e}")
    
    return results
