import argparse
import sys
import os

from src.detectors.hybrid_detector import HybridDetector
from src.redactors.mapper import StatefulMapper
from src.redactors.docx_handler import DocxHandler
from src.evaluation.metrics import Evaluator

def main():
    parser = argparse.ArgumentParser(description="PII Redaction Tool for Financial Documents")
    
    parser.add_argument(
        "--mode", 
        type=str, 
        required=True, 
        choices=["redact", "evaluate"],
        help="Mode of operation: 'redact' a .docx file or 'evaluate' detection metrics."
    )
    parser.add_argument(
        "--input", 
        type=str, 
        required=True, 
        help="Path to the input file (.docx for redact, .json for evaluate)."
    )
    parser.add_argument(
        "--output", 
        type=str, 
        help="Path to the output .docx file (required for redact mode)."
    )
    parser.add_argument(
        "--whitelist", 
        type=str,
        nargs='+',
        default=[
            "Cap Price", "Floor Price", "Offer Price", "Book Building Process", 
            "Cut-off Price", "Red Herring Prospectus", "Equity Shares", 
            "Offer for Sale", "Fresh Issue", "SEBI", "BSE", "NSE", "Companies Act",
            "Selling Shareholder", "Selling Shareholders", "Promoter Selling Shareholder", 
            "Company Secretary", "Compliance Officer", "Book Running Lead Manager", 
            "Statutory Auditors", "Chartered Accountants",
            "REGISTERED OFFICE", "CORPORATE OFFICE", "CONTACT PERSON", 
            "E-MAIL AND TELEPHONE", "WEBSITE", "DETAILS OF THE OFFER TO PUBLIC", 
            "TYPE", "SIZE OF THE FRESH ISSUE", "TOTAL OFFER SIZE", 
            "ELIGIBILITY AND SHARE RESERVATION", "Qualified Institutional Buyers", 
            "Retail Individual Investors", "Stock Exchanges", "BSE Limited", 
            "National Stock Exchange of India Limited", "ISSUER'S"
        ],
        help="List of terms to whitelist (ignore during PII detection)."
    )
    
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"Error: Input file '{args.input}' not found.")
        sys.exit(1)

    # Initialize the core detector with whitelist
    detector = HybridDetector(whitelist=args.whitelist)

    if args.mode == "redact":
        if not args.output:
            print("Error: --output is required for 'redact' mode.")
            sys.exit(1)
            
        print(f"Starting redaction on {args.input}...")
        
        # Initialize mapper (seed can be specified if reproducible fakes are needed)
        mapper = StatefulMapper()
        
        # Initialize DOCX handler
        handler = DocxHandler(detector=detector, mapper=mapper)
        
        # Process and save
        handler.process_document(args.input, args.output)
        
    elif args.mode == "evaluate":
        print(f"Evaluating metrics using ground truth from {args.input}...")
        
        # Initialize evaluator
        evaluator = Evaluator(detector=detector)
        
        # Run evaluation
        evaluator.evaluate_from_file(args.input)

if __name__ == "__main__":
    main()
