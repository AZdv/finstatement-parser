import finstatement
import sys
import os
from datetime import datetime
import json

def main():
    if len(sys.argv) < 2:
        print("Usage: python example.py <path_to_statement.pdf>")
        print("\nNo PDF provided. Running demo with sample output...")
        
        # Demo mode with sample data
        result = create_sample_result()
    else:
        file_path = sys.argv[1]
        if not os.path.exists(file_path):
            print(f"Error: File '{file_path}' not found.")
            return
            
        try:
            print(f"Parsing statement file: {file_path}")
            # Enable debug mode if requested
            debug = "--debug" in sys.argv
            result = finstatement.parse(file_path, debug=debug)
        except Exception as e:
            print(f"Error parsing statement: {e}")
            return
    
    # Print summary
    print_summary(result)
    
    # Save as JSON
    output_file = "statement_data.json"
    with open(output_file, "w") as json_file:
        json_file.write(result.to_json())
    print(f"\nSaved JSON data to '{output_file}'")

def create_sample_result():
    """Create a sample result for demo purposes"""
    return finstatement.StatementResult(
        account_info=finstatement.AccountInfo(
            number="xxxx-xxxx-xxxx-1234",
            institution="chase",
            type="credit_card"
        ),
        period=finstatement.Period(
            start=datetime(2023, 1, 1),
            end=datetime(2023, 1, 31)
        ),
        balance=finstatement.Balance(
            opening=1000.0,
            closing=1250.0
        ),
        transactions=[
            finstatement.Transaction(
                date=datetime(2023, 1, 15),
                description="WHOLEFDS ABC 12345",
                amount=-50.0,
                category="grocery"
            ),
            finstatement.Transaction(
                date=datetime(2023, 1, 17),
                description="AMAZON.COM*A123B4567",
                amount=-29.99,
                category="shopping"
            ),
            finstatement.Transaction(
                date=datetime(2023, 1, 20),
                description="PAYMENT THANK YOU",
                amount=500.0,
                category="payment"
            )
        ],
        confidence={
            "account_info": 0.9,
            "period": 0.9,
            "balance": 0.8,
            "transactions": 0.7,
            "overall": 0.825
        }
    )

def print_summary(result):
    """Print a summary of the parsing results"""
    def money(value):
        return "not read" if value is None else f"${value:,.2f}"

    def day(value):
        return "not read" if value is None else value.strftime("%B %d, %Y")

    # Every field here can legitimately be None. This demo used to assume
    # otherwise and died with an AttributeError on exactly the statements the
    # README is written to celebrate, which is the worst place to crash.
    print(f"\n=== Statement Summary ===")
    print(f"Account: {result.account_info.number or 'not read'} "
          f"({result.account_info.institution or 'unknown institution'})")
    print(f"Period: {day(result.period.start)} to {day(result.period.end)}")
    print(f"Opening Balance: {money(result.balance.opening)}")
    print(f"Closing Balance: {money(result.balance.closing)}")
    print(f"Transaction Count: {len(result.transactions)}")

    if result.parse_errors:
        print("\n=== Could not be read ===")
        for problem in result.parse_errors:
            print(f"  {problem}")
    
    # Print confidence scores
    if result.confidence:
        print("\n=== Confidence Scores ===")
        for field, score in result.confidence.items():
            print(f"{field.capitalize()}: {score:.2f}")
    
    # Print transaction details
    print("\n=== Transactions ===")
    for idx, tx in enumerate(result.transactions, 1):
        category = f"[{tx.category}]" if tx.category else ""
        print(f"{idx}. {tx.date.strftime('%m/%d/%Y')} | ${tx.amount:.2f} | {tx.description} {category}")

if __name__ == "__main__":
    main()
