#!/usr/bin/env python3
"""
Sample Financial Statement PDF Generator

This script generates sample financial statement PDFs for testing the finstatement parser.
It creates realistic but fictional bank and credit card statements with typical sections
and formatting similar to major financial institutions.

Note: This script is for internal testing only and is not included in the public package.

Developed by AZdev (https://azdv.co)
"""

import argparse
import random
import os
from datetime import datetime, timedelta
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table, 
                               TableStyle, PageBreak, Image)

# Get the base styles
styles = getSampleStyleSheet()

# Define custom styles with unique names to avoid conflicts
# Use add() method instead of dictionary assignment
styles.add(ParagraphStyle(
    name='StatementHeader',
    fontName='Helvetica-Bold',
    fontSize=14,
    spaceAfter=12
))

styles.add(ParagraphStyle(
    name='StatementSubHeader',
    fontName='Helvetica-Bold',
    fontSize=12,
    spaceAfter=6
))

styles.add(ParagraphStyle(
    name='StatementText',
    fontName='Helvetica',
    fontSize=10,
    spaceAfter=6
))

styles.add(ParagraphStyle(
    name='StatementSmall',
    fontName='Helvetica',
    fontSize=8,
    spaceAfter=3
))

# Sample business names for transactions
businesses = [
    "AMAZON.COM", "WALMART", "TARGET", "COSTCO WHOLESALE", "WHOLE FOODS",
    "TRADER JOE'S", "STARBUCKS", "MCDONALD'S", "CHIPOTLE", "UBER", "UBER EATS",
    "LYFT", "CHEVRON", "SHELL", "NETFLIX", "SPOTIFY", "APPLE", "GOOGLE",
    "AT&T", "VERIZON", "T-MOBILE", "COMCAST", "CVS PHARMACY", "WALGREENS",
    "HOME DEPOT", "LOWE'S", "IKEA", "BEST BUY", "ZAPPOS", "NORDSTROM", 
    "MACY'S", "URBAN OUTFITTERS", "GRUBHUB", "DOORDASH", "INSTACART"
]

# Sample transaction categories and descriptions
transaction_types = {
    "dining": [
        "Restaurant", "Cafe", "Coffee Shop", "Bar", "Diner", "Bistro", "Steakhouse"
    ],
    "grocery": [
        "Supermarket", "Grocery Store", "Market", "Convenience Store", "Bakery"
    ],
    "shopping": [
        "Clothing", "Electronics", "Merchandise", "Retail Purchase", "Department Store"
    ],
    "utilities": [
        "Electric Bill", "Water Bill", "Gas Bill", "Internet Service", "Phone Bill"
    ],
    "entertainment": [
        "Movie Theater", "Concert Tickets", "Streaming Service", "Music Subscription"
    ],
    "transportation": [
        "Ride Share", "Taxi", "Gas Station", "Parking", "Transit", "Airline Tickets"
    ],
    "health": [
        "Pharmacy", "Doctor Visit", "Medical Services", "Dental Care", "Health Insurance"
    ],
    "subscription": [
        "Monthly Subscription", "Annual Membership", "Online Service", "Software License"
    ]
}

def generate_account_number():
    """Generate a masked account number."""
    last_four = ''.join(str(random.randint(0, 9)) for _ in range(4))
    return f"XXXX XXXX XXXX {last_four}"

def generate_transactions(start_date, end_date, account_type="credit", count=20):
    """Generate sample transactions for the date range."""
    transactions = []
    current_balance = 2500.00 if account_type == "bank" else 0.00
    
    # Create date list between start and end dates
    date_range = (end_date - start_date).days
    transaction_dates = sorted([
        start_date + timedelta(days=random.randint(0, date_range)) 
        for _ in range(count)
    ])
    
    # Generate transactions
    for date in transaction_dates:
        # Decide transaction type and amount
        is_credit = random.random() > 0.7 or (account_type == "bank" and len(transactions) == 0)
        
        if is_credit:
            # Credits/deposits
            if account_type == "bank" and random.random() > 0.7:
                # Payroll deposit
                amount = round(random.uniform(1000, 3000), 2)
                description = "DIRECT DEPOSIT - EMPLOYER PAYROLL"
                category = "income"
            else:
                # Payment or refund
                amount = round(random.uniform(10, 500), 2)
                if account_type == "credit":
                    description = "PAYMENT THANK YOU"
                    category = "payment"
                else:
                    business = random.choice(businesses)
                    description = f"{business} REFUND"
                    category = "refund"
        else:
            # Debits/charges
            category = random.choice(list(transaction_types.keys()))
            business = random.choice(businesses)
            descriptor = random.choice(transaction_types[category])
            amount = -round(random.uniform(5, 150), 2)
            
            # Format description
            if random.random() > 0.5:
                description = f"{business} {descriptor}"
            else:
                description = f"{business} #{random.randint(10000, 99999)}"
        
        # Update balance
        if account_type == "bank":
            current_balance += amount
            
        # Add transaction
        transactions.append({
            "date": date,
            "description": description,
            "amount": amount,
            "balance": round(current_balance, 2) if account_type == "bank" else None,
            "category": category
        })
    
    return transactions

def generate_chase_credit_statement(output_path, statement_date=None):
    """Generate a sample Chase credit card statement."""
    # Setup dates
    if statement_date is None:
        statement_date = datetime.now().replace(day=15)
    
    end_date = statement_date
    start_date = (end_date.replace(day=1) - timedelta(days=1)).replace(day=16)
    due_date = (end_date + timedelta(days=25)).replace(day=12)
    
    # Generate transactions
    transactions = generate_transactions(start_date, end_date, account_type="credit", count=25)
    
    # Calculate totals
    previous_balance = 1245.67
    payments = sum(tx["amount"] for tx in transactions if tx["category"] == "payment")
    purchases = sum(tx["amount"] for tx in transactions if tx["amount"] < 0 and tx["category"] != "payment")
    fees = 0.00
    interest = 0.00
    new_balance = previous_balance + purchases - payments + fees + interest
    
    # Create the document
    doc = SimpleDocTemplate(output_path, pagesize=letter)
    story = []
    
    # Header
    story.append(Paragraph("CHASE", styles["StatementHeader"]))
    story.append(Paragraph("CREDIT CARD STATEMENT", styles["StatementSubHeader"]))
    story.append(Spacer(1, 12))
    
    # Account information
    account_info = [
        ["Account Number:", generate_account_number()],
        ["Statement Date:", end_date.strftime("%m/%d/%Y")],
        ["Payment Due Date:", due_date.strftime("%m/%d/%Y")],
        ["New Balance:", f"${new_balance:.2f}"],
        ["Minimum Payment Due:", f"${max(new_balance * 0.02, 25):.2f}"]
    ]
    
    account_table = Table(account_info, colWidths=[150, 300])
    account_table.setStyle(TableStyle([
        ('FONT', (0, 0), (-1, -1), 'Helvetica'),
        ('FONT', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(account_table)
    story.append(Spacer(1, 12))
    
    # Account summary
    story.append(Paragraph("ACCOUNT SUMMARY", styles["StatementSubHeader"]))
    summary_data = [
        ["Previous Balance:", f"${previous_balance:.2f}"],
        ["Payment, Credits:", f"${payments:.2f}"],
        ["Purchases:", f"${abs(purchases):.2f}"],
        ["Fees Charged:", f"${fees:.2f}"],
        ["Interest Charged:", f"${interest:.2f}"],
        ["New Balance:", f"${new_balance:.2f}"]
    ]
    
    summary_table = Table(summary_data, colWidths=[150, 300])
    summary_table.setStyle(TableStyle([
        ('FONT', (0, 0), (-1, -1), 'Helvetica'),
        ('FONT', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LINEBELOW', (0, -1), (-1, -1), 1, colors.black),
        ('FONT', (0, -1), (-1, -1), 'Helvetica-Bold'),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 24))
    
    # Transactions
    story.append(Paragraph("TRANSACTIONS", styles["StatementSubHeader"]))
    
    # Payments and credits
    story.append(Paragraph("Payments and Credits", styles["StatementText"]))
    payments_data = [["Date", "Description", "Amount"]]
    
    payment_txs = [tx for tx in transactions if tx["amount"] > 0]
    for tx in payment_txs:
        payments_data.append([
            tx["date"].strftime("%m/%d"),
            tx["description"],
            f"${tx['amount']:.2f}"
        ])
    
    if not payment_txs:
        payments_data.append(["", "No payments or credits in this period", ""])
    
    payments_table = Table(payments_data, colWidths=[70, 330, 70])
    payments_table.setStyle(TableStyle([
        ('FONT', (0, 0), (-1, -1), 'Helvetica'),
        ('FONT', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('ALIGN', (0, 0), (0, -1), 'CENTER'),
        ('ALIGN', (-1, 0), (-1, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, 0), 1, colors.black),
        ('LINEBELOW', (0, -1), (-1, -1), 0.5, colors.black),
    ]))
    story.append(payments_table)
    story.append(Spacer(1, 12))
    
    # Purchases
    story.append(Paragraph("Purchases", styles["StatementText"]))
    purchases_data = [["Date", "Description", "Amount"]]
    
    purchase_txs = [tx for tx in transactions if tx["amount"] < 0]
    for tx in purchase_txs:
        purchases_data.append([
            tx["date"].strftime("%m/%d"),
            tx["description"],
            f"${abs(tx['amount']):.2f}"
        ])
    
    purchases_table = Table(purchases_data, colWidths=[70, 330, 70])
    purchases_table.setStyle(TableStyle([
        ('FONT', (0, 0), (-1, -1), 'Helvetica'),
        ('FONT', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('ALIGN', (0, 0), (0, -1), 'CENTER'),
        ('ALIGN', (-1, 0), (-1, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, 0), 1, colors.black),
        ('LINEBELOW', (0, -1), (-1, -1), 0.5, colors.black),
    ]))
    story.append(purchases_table)
    
    # Footer
    story.append(Spacer(1, 30))
    story.append(Paragraph("For Customer Service, call 1-800-555-1234", styles["StatementSmall"]))
    story.append(Paragraph("Visit us online at www.chase.com", styles["StatementSmall"]))
    
    # Build the PDF
    doc.build(story)
    return output_path

def generate_bofa_bank_statement(output_path, statement_date=None):
    """Generate a sample Bank of America checking account statement."""
    # Setup dates
    if statement_date is None:
        statement_date = datetime.now().replace(day=25)
    
    end_date = statement_date
    start_date = end_date.replace(day=1)
    
    # Generate transactions
    transactions = generate_transactions(start_date, end_date, account_type="bank", count=18)
    
    # Calculate totals
    beginning_balance = 2500.00
    deposits = sum(tx["amount"] for tx in transactions if tx["amount"] > 0)
    withdrawals = sum(tx["amount"] for tx in transactions if tx["amount"] < 0)
    ending_balance = beginning_balance + deposits + withdrawals
    
    # Create the document
    doc = SimpleDocTemplate(output_path, pagesize=letter)
    story = []
    
    # Header
    story.append(Paragraph("Bank of America", styles["StatementHeader"]))
    story.append(Paragraph("CHECKING ACCOUNT STATEMENT", styles["StatementSubHeader"]))
    story.append(Spacer(1, 12))
    
    # Account information
    account_info = [
        ["Account Number:", generate_account_number()],
        ["Statement Period:", f"{start_date.strftime('%m/%d/%Y')} to {end_date.strftime('%m/%d/%Y')}"],
        ["Account Holder:", "JOHN Q CUSTOMER"]
    ]
    
    account_table = Table(account_info, colWidths=[150, 300])
    account_table.setStyle(TableStyle([
        ('FONT', (0, 0), (-1, -1), 'Helvetica'),
        ('FONT', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(account_table)
    story.append(Spacer(1, 12))
    
    # Account summary
    story.append(Paragraph("ACCOUNT SUMMARY", styles["StatementSubHeader"]))
    summary_data = [
        ["Beginning Balance:", f"${beginning_balance:.2f}"],
        ["Deposits and Credits:", f"${deposits:.2f}"],
        ["Withdrawals and Debits:", f"${abs(withdrawals):.2f}"],
        ["Ending Balance:", f"${ending_balance:.2f}"]
    ]
    
    summary_table = Table(summary_data, colWidths=[150, 300])
    summary_table.setStyle(TableStyle([
        ('FONT', (0, 0), (-1, -1), 'Helvetica'),
        ('FONT', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LINEBELOW', (0, -1), (-1, -1), 1, colors.black),
        ('FONT', (0, -1), (-1, -1), 'Helvetica-Bold'),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 24))
    
    # Transactions
    story.append(Paragraph("TRANSACTIONS", styles["StatementSubHeader"]))
    
    transactions_data = [["Date", "Description", "Amount", "Balance"]]
    
    # Sort transactions by date
    sorted_txs = sorted(transactions, key=lambda x: x["date"])
    
    for tx in sorted_txs:
        transactions_data.append([
            tx["date"].strftime("%m/%d/%Y"),
            tx["description"],
            f"${tx['amount']:.2f}",
            f"${tx['balance']:.2f}"
        ])
    
    transactions_table = Table(transactions_data, colWidths=[80, 280, 70, 70])
    transactions_table.setStyle(TableStyle([
        ('FONT', (0, 0), (-1, -1), 'Helvetica'),
        ('FONT', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('ALIGN', (0, 0), (0, -1), 'CENTER'),
        ('ALIGN', (-2, 0), (-1, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, 0), 1, colors.black),
        ('LINEBELOW', (0, -1), (-1, -1), 0.5, colors.black),
    ]))
    story.append(transactions_table)
    
    # Footer
    story.append(Spacer(1, 30))
    story.append(Paragraph("For Customer Service, call 1-800-555-5678", styles["StatementSmall"]))
    story.append(Paragraph("Visit us online at www.bankofamerica.com", styles["StatementSmall"]))
    
    # Build the PDF
    doc.build(story)
    return output_path

def generate_amex_credit_statement(output_path, statement_date=None):
    """Generate a sample American Express credit card statement."""
    # Setup dates
    if statement_date is None:
        statement_date = datetime.now().replace(day=20)
    
    end_date = statement_date
    start_date = (end_date.replace(day=1) - timedelta(days=1)).replace(day=21)
    due_date = (end_date + timedelta(days=25)).replace(day=15)
    
    # Generate transactions
    transactions = generate_transactions(start_date, end_date, account_type="credit", count=30)
    
    # Calculate totals
    previous_balance = 2033.45
    payments = sum(tx["amount"] for tx in transactions if tx["category"] == "payment")
    purchases = sum(tx["amount"] for tx in transactions if tx["amount"] < 0 and tx["category"] != "payment")
    fees = 0.00
    interest = 0.00
    new_balance = previous_balance + purchases - payments + fees + interest
    
    # Create the document
    doc = SimpleDocTemplate(output_path, pagesize=letter)
    story = []
    
    # Header
    story.append(Paragraph("American Express", styles["StatementHeader"]))
    story.append(Paragraph("CARD MEMBER STATEMENT", styles["StatementSubHeader"]))
    story.append(Spacer(1, 12))
    
    # Account information
    account_info = [
        ["Account Number:", generate_account_number()],
        ["Member Since:", "2015"],
        ["Statement Date:", end_date.strftime("%m/%d/%Y")],
        ["Payment Due Date:", due_date.strftime("%m/%d/%Y")],
        ["Total Balance:", f"${new_balance:.2f}"],
        ["Minimum Payment Due:", f"${max(new_balance * 0.02, 35):.2f}"]
    ]
    
    account_table = Table(account_info, colWidths=[150, 300])
    account_table.setStyle(TableStyle([
        ('FONT', (0, 0), (-1, -1), 'Helvetica'),
        ('FONT', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(account_table)
    story.append(Spacer(1, 12))
    
    # Account summary
    story.append(Paragraph("ACCOUNT SUMMARY", styles["StatementSubHeader"]))
    summary_data = [
        ["Previous Balance:", f"${previous_balance:.2f}"],
        ["Payments and Credits:", f"${payments:.2f}"],
        ["Purchases and Charges:", f"${abs(purchases):.2f}"],
        ["Fees:", f"${fees:.2f}"],
        ["Interest Charged:", f"${interest:.2f}"],
        ["New Balance:", f"${new_balance:.2f}"]
    ]
    
    summary_table = Table(summary_data, colWidths=[150, 300])
    summary_table.setStyle(TableStyle([
        ('FONT', (0, 0), (-1, -1), 'Helvetica'),
        ('FONT', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LINEBELOW', (0, -1), (-1, -1), 1, colors.black),
        ('FONT', (0, -1), (-1, -1), 'Helvetica-Bold'),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 24))
    
    # Add a page break
    story.append(PageBreak())
    
    # Transactions
    story.append(Paragraph("TRANSACTIONS", styles["StatementSubHeader"]))
    
    # Payments and credits
    story.append(Paragraph("Payments and Credits", styles["StatementText"]))
    payments_data = [["Date", "Description", "Amount"]]
    
    payment_txs = [tx for tx in transactions if tx["amount"] > 0]
    for tx in payment_txs:
        payments_data.append([
            tx["date"].strftime("%m/%d/%Y"),
            tx["description"],
            f"${tx['amount']:.2f}"
        ])
    
    if not payment_txs:
        payments_data.append(["", "No payments or credits in this period", ""])
    
    payments_table = Table(payments_data, colWidths=[80, 320, 70])
    payments_table.setStyle(TableStyle([
        ('FONT', (0, 0), (-1, -1), 'Helvetica'),
        ('FONT', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('ALIGN', (0, 0), (0, -1), 'CENTER'),
        ('ALIGN', (-1, 0), (-1, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, 0), 1, colors.black),
        ('LINEBELOW', (0, -1), (-1, -1), 0.5, colors.black),
    ]))
    story.append(payments_table)
    story.append(Spacer(1, 12))
    
    # Purchases
    story.append(Paragraph("Charges", styles["StatementText"]))
    purchases_data = [["Date", "Description", "Amount"]]
    
    purchase_txs = [tx for tx in transactions if tx["amount"] < 0]
    for tx in purchase_txs:
        purchases_data.append([
            tx["date"].strftime("%m/%d/%Y"),
            tx["description"],
            f"${abs(tx['amount']):.2f}"
        ])
    
    purchases_table = Table(purchases_data, colWidths=[80, 320, 70])
    purchases_table.setStyle(TableStyle([
        ('FONT', (0, 0), (-1, -1), 'Helvetica'),
        ('FONT', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('ALIGN', (0, 0), (0, -1), 'CENTER'),
        ('ALIGN', (-1, 0), (-1, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, 0), 1, colors.black),
        ('LINEBELOW', (0, -1), (-1, -1), 0.5, colors.black),
    ]))
    story.append(purchases_table)
    
    # Footer
    story.append(Spacer(1, 30))
    story.append(Paragraph("For Customer Service, call 1-800-555-3939", styles["StatementSmall"]))
    story.append(Paragraph("Visit us online at www.americanexpress.com", styles["StatementSmall"]))
    
    # Build the PDF
    doc.build(story)
    return output_path

def main():
    """Main function to generate sample PDFs."""
    parser = argparse.ArgumentParser(description="Generate sample financial statement PDFs")
    parser.add_argument("--output-dir", default="sample_statements",
                       help="Directory to save generated PDFs")
    parser.add_argument("--type", choices=["chase", "bofa", "amex", "all"],
                       default="all", help="Type of statement to generate")
    args = parser.parse_args()
    
    # Create output directory if it doesn't exist
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Generate statements based on type
    if args.type == "chase" or args.type == "all":
        output_path = os.path.join(args.output_dir, "chase_credit_statement.pdf")
        generate_chase_credit_statement(output_path)
        print(f"Generated Chase credit card statement: {output_path}")
    
    if args.type == "bofa" or args.type == "all":
        output_path = os.path.join(args.output_dir, "bofa_checking_statement.pdf")
        generate_bofa_bank_statement(output_path)
        print(f"Generated Bank of America checking statement: {output_path}")
    
    if args.type == "amex" or args.type == "all":
        output_path = os.path.join(args.output_dir, "amex_credit_statement.pdf")
        generate_amex_credit_statement(output_path)
        print(f"Generated American Express credit card statement: {output_path}")

if __name__ == "__main__":
    main()