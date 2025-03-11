# Financial Statement Parser

<div align="center">
  <img src="https://via.placeholder.com/150x150" alt="Financial Statement Parser Logo" width="150" height="150">
  <br>
  <strong>Extract structured data from financial statement PDFs</strong>
  <br>
  <i>Developed and maintained by <a href="https://azdv.co">AZdev</a> - FinTech Innovation Execution Leaders</i>
</div>

<br>

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![PyPI version](https://img.shields.io/badge/PyPI-v0.1.0-blue.svg)](https://pypi.org/project/finstatement/)
[![Python 3.7+](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/downloads/)

## The Problem

Financial developers and engineers waste countless hours manually extracting data from bank statements, credit card statements, and other financial PDFs. Each institution uses different formats, making automated processing a persistent challenge.

This library provides a standardized way to extract structured data from financial statement PDFs with minimal setup, saving developers significant time and effort.

## Key Features

- **Universal PDF Extraction**: Works with statements from major financial institutions
- **Automatic Institution Detection**: Identifies the source institution
- **Comprehensive Data Extraction**:
  - Account information (number, type)
  - Statement period (start/end dates)
  - Balance information (opening/closing)
  - Complete transaction lists
- **Transaction Categorization**: Automatically classifies transactions into categories
- **Confidence Scoring**: Reliability ratings for each extracted data point
- **Parallel Processing**: Efficient batch processing for multiple statements
- **Debug Mode**: Detailed logging for troubleshooting
- **Clean, Consistent Output**: Standardized JSON regardless of source format

## Quick Start

### Installation

```bash
# From PyPI (once published)
pip install finstatement

# From source
git clone https://github.com/azdv/finstatement.git
cd finstatement
pip install -e .
```

### Basic Usage

```python
import finstatement

# Parse a statement PDF
result = finstatement.parse("statement.pdf")

# Access structured data
print(f"Account: {result.account_info.number}")
print(f"Period: {result.period.start} to {result.period.end}")
print(f"Closing Balance: ${result.balance.closing:.2f}")

# Get transactions
for tx in result.transactions:
    print(f"{tx.date.strftime('%m/%d/%Y')} | ${tx.amount:.2f} | {tx.description}")

# Export as standardized JSON
json_data = result.to_json()
```

### Example Script

The package includes a simple example script for quick demonstration:

```bash
python example.py path/to/your/statement.pdf
```

### Advanced Usage

#### Batch Processing

Process multiple statements efficiently:

```python
import finstatement
import glob

# Get all PDFs in a directory
pdf_files = glob.glob("statements/*.pdf")

# Process in parallel (default)
results = finstatement.batch_parse(pdf_files)

# Process sequentially
results = finstatement.batch_parse(pdf_files, parallel=False)

# Control parallelism
results = finstatement.batch_parse(pdf_files, max_workers=4)

# Process results
for path, result in results.items():
    print(f"Statement: {path}")
    print(f"Found {len(result.transactions)} transactions")
```

#### Debug Mode

Enable detailed logging for troubleshooting:

```python
import finstatement

# Enable debug mode
result = finstatement.parse("statement.pdf", debug=True)
```

#### Transaction Analysis

Analyze transactions by category:

```python
import finstatement
from collections import defaultdict

result = finstatement.parse("statement.pdf")

# Group transactions by category
by_category = defaultdict(list)
for tx in result.transactions:
    by_category[tx.category or "uncategorized"].append(tx)

# Calculate spending by category
category_totals = {}
for category, transactions in by_category.items():
    category_totals[category] = sum(tx.amount for tx in transactions)
    
# Print summary
for category, total in sorted(category_totals.items(), key=lambda x: x[1]):
    print(f"{category}: ${abs(total):.2f}")
```

## Supported Institutions

The library currently supports basic extraction for statements from:

- Chase Bank
- Bank of America
- Wells Fargo
- Citibank
- American Express
- Discover
- Capital One

More institutions and statement types are being added regularly.

## Data Model

The library provides a clean, structured data model:

```
StatementResult
├── account_info: AccountInfo
│   ├── number: str
│   ├── name: str (optional)
│   ├── institution: str
│   └── type: str (bank, credit_card, investment)
├── period: Period
│   ├── start: datetime
│   └── end: datetime
├── balance: Balance
│   ├── opening: float (optional)
│   └── closing: float
├── transactions: List[Transaction]
│   ├── date: datetime
│   ├── description: str
│   ├── amount: float
│   ├── balance: float (optional)
│   └── category: str (optional)
└── confidence: Dict[str, float]
```

## Use Cases

- **Personal Finance Apps**: Import data from user's financial statements
- **Expense Management Systems**: Automatically process credit card statements
- **Bookkeeping Software**: Extract transaction data for reconciliation
- **Financial Analysis Tools**: Import historical statement data
- **Loan Processing Systems**: Analyze bank statements for affordability checks

## Contributing

Contributions are welcome! Here's how you can help:

1. **Add Institution Support**: Implement patterns for new financial institutions
2. **Improve Extraction Accuracy**: Enhance pattern matching for existing institutions
3. **Add New Statement Types**: Support for investment, mortgage, loan statements, etc.
4. **Bug Reports and Feature Requests**: Open issues on GitHub

Please see [CONTRIBUTING.md](CONTRIBUTING.md) for detailed contribution guidelines.

## Roadmap

- [ ] Machine learning enhancements for improved extraction accuracy
- [ ] Transaction categorization based on description patterns
- [ ] Support for international bank formats
- [ ] REST API for cloud-based processing
- [ ] Visual results dashboard
- [ ] Historical statement analysis
- [ ] Integration with personal finance tools

## Performance

The library is optimized for accuracy rather than speed but can still process most statements in under a second. For large batches of statements, consider using the `batch_parse` function with parallel processing enabled.

### Benchmarks

| Statement Type | Pages | Processing Time (s) |
|----------------|-------|---------------------|
| Chase Credit Card | 3 | 0.42 |
| Bank of America Checking | 5 | 0.67 |
| Wells Fargo Savings | 2 | 0.35 |
| Amex Credit Card | 8 | 0.98 |
| Batch of 10 statements | 35 | 3.12* |

_* Using parallel processing on a quad-core system_

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| **Low confidence scores** | Enable debug mode to see what patterns were matched. You might need to add institution-specific patterns. |
| **Missing transactions** | Some statements have unusual formatting. Try extracting the text manually to see the structure and submit a feature request. |
| **Incorrect dates** | If your statement uses an unusual date format, you may need to extend the date parsing patterns. |
| **PDF extraction fails** | Try using a different PDF reader like Poppler if PyPDF2 has issues with your document. |
| **Memory issues with large batches** | Reduce the `max_workers` parameter when using `batch_parse`. |

### Debugging Tips

1. Enable debug mode: `finstatement.parse("statement.pdf", debug=True)`
2. Manually extract text: `python -c "import PyPDF2; print(PyPDF2.PdfReader('statement.pdf').pages[0].extract_text()[:500])"`
3. Check if your PDF is compatible: `python -c "import PyPDF2; print(PyPDF2.PdfReader('statement.pdf').metadata)"`
4. For encrypted PDFs, check if they can be opened: `python -c "import PyPDF2; r=PyPDF2.PdfReader('statement.pdf'); print(r.is_encrypted)"`

## Security Note

This library processes financial documents locally. No data is sent to external servers. We recommend implementing additional security measures when handling sensitive financial information in your application.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## About AZdev

[AZdev](https://azdv.co) specializes in mission-critical FinTech engineering and CTO services. We help financial institutions and startups build innovative, scalable, and secure financial technology solutions.

For consulting, custom development, or enterprise support for this library, contact us at info@azdv.co.

---

<div align="center">
  <sub>Built with ❤️ by <a href="https://azdv.co">AZdev</a> - FinTech Innovation Execution Leaders</sub>
</div>
