#!/usr/bin/env python3
"""
RAG System Initialization Script
Loads luxury item data and builds vector store
"""

import os
import sys
import json
import argparse
import logging
from datetime import datetime

# Add project root directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.rag.initialize_rag import RAGInitializer

# Set up logging format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Initialize luxury items RAG system")
    parser.add_argument("--data_file", type=str, default="data/luxury_items.json",
                         help="Path to luxury items data file")
    parser.add_argument("--force", action="store_true", 
                         help="Force rebuild vector store, even if it already exists")
    parser.add_argument("--vector_store_dir", type=str, default="vector_store",
                         help="Vector store directory")
    parser.add_argument("--cache_dir", type=str, default="cache",
                         help="Cache directory")
    parser.add_argument("--test_query", type=str, 
                         help="Test query to validate the system after initialization")
    return parser.parse_args()

def main():
    """Main function"""
    # Parse command line arguments
    args = parse_args()
    
    # Set data file and directories
    data_file = args.data_file
    vector_store_dir = args.vector_store_dir
    cache_dir = args.cache_dir
    force_rebuild = args.force
    test_query = args.test_query
    
    logger.info(f"Initializing RAG system, data file: {data_file}")
    logger.info(f"Vector store directory: {vector_store_dir}")
    logger.info(f"Cache directory: {cache_dir}")
    
    # Check if data file exists
    if not os.path.exists(data_file):
        logger.error(f"Data file does not exist: {data_file}")
        return 1
    
    # Create RAG initializer
    initializer = RAGInitializer(
        data_dir=os.path.dirname(data_file),
        vector_store_dir=vector_store_dir,
        cache_dir=cache_dir
    )
    
    # Initialize RAG system
    logger.info("Starting RAG system initialization...")
    success = initializer.initialize(data_file, force_reindex=force_rebuild)
    
    if not success:
        logger.error("RAG system initialization failed")
        logger.error(f"Error message: {initializer.initialization_state.get('error', 'Unknown error')}")
        return 1
    
    logger.info("RAG system initialization successful")
    
    # Display initialization statistics
    stats = initializer.initialization_state.get("stats", {})
    data_stats = stats.get("data_processing", {})
    
    if data_stats:
        logger.info("Data processing statistics:")
        logger.info(f"  Total items: {data_stats.get('total_items', 0)}")
        logger.info(f"  Items with price: {data_stats.get('items_with_price', 0)}")
        logger.info(f"  Items with brand: {data_stats.get('items_with_brand', 0)}")
        logger.info(f"  Items with model: {data_stats.get('items_with_model', 0)}")
        logger.info(f"  Items with category: {data_stats.get('items_with_category', 0)}")
        logger.info(f"  Number of brands: {len(data_stats.get('brands', []))}")
        logger.info(f"  Number of categories: {len(data_stats.get('categories', []))}")
    
    # If a test query is provided, execute test
    if test_query:
        logger.info(f"Executing test query: '{test_query}'")
        test_results = initializer.test_search(test_query)
        
        if test_results:
            print("\nTest Query Results:")
            print(f"Query: {test_query}")
            print(f"Found {len(test_results['results'])} relevant items\n")
            
            for i, result in enumerate(test_results['results']):
                print(f"{i+1}. {result.get('brand', '')} {result.get('model', '')}")
                if "category" in result:
                    print(f"   Category: {result['category']}")
                if "price" in result:
                    if isinstance(result['price'], (int, float)):
                        print(f"   Price: ${result['price']:,.2f}")
                    else:
                        print(f"   Price: {result['price']}")
                if "score" in result:
                    print(f"   Relevance: {result['score']:.4f}")
                if "description" in result:
                    desc = result["description"]
                    if len(desc) > 100:
                        desc = desc[:97] + "..."
                    print(f"   Description: {desc}")
                print("")
    
    logger.info("RAG system initialization complete")
    return 0

if __name__ == "__main__":
    exit(main()) 