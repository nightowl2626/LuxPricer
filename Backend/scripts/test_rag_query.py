#!/usr/bin/env python3
"""
Test RAG Query Functionality
"""

import os
import sys
import json
import argparse
import logging
import time
from tabulate import tabulate

# Add project root directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.rag.query import query_luxury_items, get_similar_items

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Test RAG query functionality")
    parser.add_argument("--query", type=str, required=True,
                        help="Query text")
    parser.add_argument("--top_k", type=int, default=5,
                        help="Number of results to return")
    parser.add_argument("--brand", type=str,
                        help="Brand filter")
    parser.add_argument("--category", type=str,
                        help="Category filter")
    parser.add_argument("--min_price", type=float,
                        help="Minimum price")
    parser.add_argument("--max_price", type=float,
                        help="Maximum price")
    parser.add_argument("--output", type=str,
                        help="Output results to JSON file")
    parser.add_argument("--vector_store_path", type=str, default="vector_store/luxury_items_store",
                        help="Vector store path")
    return parser.parse_args()

def format_results_table(results):
    """Format results as a table"""
    table_data = []
    headers = ["#", "Brand", "Model", "Category", "Price", "Relevance"]
    
    for i, item in enumerate(results):
        price_str = ""
        if "price" in item:
            if isinstance(item["price"], (int, float)):
                price_str = f"${item['price']:,.2f}"
            else:
                price_str = str(item["price"])
                
        score_str = ""
        if "score" in item:
            score_str = f"{item['score']:.4f}"
            
        row = [
            i + 1,
            item.get("brand", ""),
            item.get("model", ""),
            item.get("category", ""),
            price_str,
            score_str
        ]
        table_data.append(row)
    
    return tabulate(table_data, headers, tablefmt="grid")

def print_query_analysis(analysis):
    """Print query analysis results"""
    print("\nQuery Analysis:")
    print(f"  Original query: {analysis['original_query']}")
    
    if analysis["brands"]:
        print(f"  Identified brands: {', '.join(analysis['brands'])}")
    
    if analysis["categories"]:
        print(f"  Identified categories: {', '.join(analysis['categories'])}")
    
    if analysis.get("price_range"):
        min_price, max_price = analysis["price_range"]
        if max_price == float('inf'):
            print(f"  Identified price range: > ${min_price:,.2f}")
        else:
            print(f"  Identified price range: ${min_price:,.2f} - ${max_price:,.2f}")
            
    print(f"  Contains brand filter: {analysis['has_brand_filter']}")
    print(f"  Contains category filter: {analysis['has_category_filter']}")
    print(f"  Contains price filter: {analysis['has_price_filter']}")

def print_item_details(item):
    """Print item detailed information"""
    print("\nItem Details:")
    print(f"  ID: {item.get('id', 'N/A')}")
    print(f"  Brand: {item.get('brand', 'N/A')}")
    print(f"  Model: {item.get('model', 'N/A')}")
    print(f"  Category: {item.get('category', 'N/A')}")
    
    if "price" in item:
        if isinstance(item["price"], (int, float)):
            print(f"  Price: ${item['price']:,.2f}")
        else:
            print(f"  Price: {item['price']}")
    
    if "description" in item:
        print(f"  Description: {item['description']}")
        
    if "materials" in item and item["materials"]:
        if isinstance(item["materials"], list):
            print(f"  Materials: {', '.join(item['materials'])}")
        else:
            print(f"  Materials: {item['materials']}")
            
    if "features" in item and item["features"]:
        if isinstance(item["features"], list):
            print(f"  Features: {', '.join(item['features'])}")
        else:
            print(f"  Features: {item['features']}")
    
    if "score" in item:
        print(f"  Relevance: {item['score']:.4f}")

def main():
    """Main function"""
    args = parse_args()
    
    # Build price range
    price_range = None
    if args.min_price is not None or args.max_price is not None:
        min_price = args.min_price if args.min_price is not None else 0
        max_price = args.max_price if args.max_price is not None else float('inf')
        price_range = (min_price, max_price)
    
    logger.info(f"Executing query: {args.query}")
    start_time = time.time()
    
    # Execute query
    results = query_luxury_items(
        query=args.query,
        top_k=args.top_k,
        brand_filter=args.brand,
        category_filter=args.category,
        price_range=price_range,
        vector_store_path=args.vector_store_path
    )
    
    query_time = time.time() - start_time
    
    # Print results
    print(f"\nQuery: {args.query}")
    print(f"Found {len(results['results'])} relevant items (in {query_time:.3f} seconds)")
    
    # Print query analysis
    print_query_analysis(results["query_analysis"])
    
    # Applied filters
    if any(results["applied_filters"].values()):
        print("\nApplied Filters:")
        if results["applied_filters"]["brand"]:
            print(f"  Brand: {results['applied_filters']['brand']}")
        if results["applied_filters"]["category"]:
            print(f"  Category: {results['applied_filters']['category']}")
        if results["applied_filters"]["price_range"]:
            min_price, max_price = results["applied_filters"]["price_range"]
            if max_price == float('inf'):
                print(f"  Price range: > ${min_price:,.2f}")
            else:
                print(f"  Price range: ${min_price:,.2f} - ${max_price:,.2f}")
    
    # Print results table
    if results["results"]:
        print("\nQuery Results:")
        print(format_results_table(results["results"]))
        
        # Print first result details
        if results["results"]:
            print_item_details(results["results"][0])
    else:
        print("\nNo matching items found")
    
    # If output file specified, save results
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"\nResults saved to: {args.output}")
    
    return 0

if __name__ == "__main__":
    exit(main()) 