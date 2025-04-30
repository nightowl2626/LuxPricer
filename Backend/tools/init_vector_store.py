#!/usr/bin/env python3
"""
Vector Store Initialization Tool

Import luxury goods data from JSON file into vector database for RAG system retrieval.
"""

import os
import sys
import json
import logging
import argparse
from pathlib import Path
from tqdm import tqdm
import time

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("vector_store_init")

# Add project root directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

# Import vector store module
from services.rag.vector_store import VectorStore

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Initialize luxury goods vector database")
    parser.add_argument("--data-file", type=str, default="data/cleaned_listings.json",
                      help="Path to JSON file containing luxury goods data")
    parser.add_argument("--output-dir", type=str, default="data/vector_store",
                      help="Output directory for vector database")
    parser.add_argument("--batch-size", type=int, default=100,
                      help="Processing batch size")
    parser.add_argument("--force", action="store_true",
                      help="Force recreation of vector store if it exists")
    return parser.parse_args()

def load_data(file_path):
    """Load luxury goods data from JSON file"""
    logger.info(f"Loading data from {file_path}")
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        logger.info(f"Successfully loaded {len(data)} data records")
        return data
    except Exception as e:
        logger.error(f"Failed to load data: {str(e)}")
        return None

def enrich_item(item):
    """
    简单处理 - 保留原始数据结构，只添加ID
    只需确保每个条目都有一个唯一标识符
    """
    # 复制原始数据，避免修改原始对象
    enriched_item = item.copy()
    
    # 确保有唯一ID
    if "id" not in enriched_item:
        import uuid
        enriched_item["id"] = str(uuid.uuid4())
    
    # 确保有价格字段（用于价格估算）
    if "price" not in enriched_item and "listing_price" in enriched_item:
        enriched_item["price"] = enriched_item["listing_price"]
    
    return enriched_item

def main():
    """Main function"""
    args = parse_arguments()
    
    # Check if data file exists
    data_file = Path(args.data_file)
    if not data_file.exists():
        logger.error(f"Data file does not exist: {data_file}")
        return 1
    
    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Check if vector store already exists
    vector_store_exists = (output_dir / "faiss_index.bin").exists() and (output_dir / "items.json").exists()
    
    if vector_store_exists and not args.force:
        logger.info(f"Vector store already exists at {output_dir}. Use --force option to recreate.")
        return 0
    
    # Load data
    items = load_data(data_file)
    if not items:
        return 1
    
    # Create vector store
    logger.info("Initializing vector store")
    vector_store = VectorStore()
    
    # Process and add data
    batch_size = args.batch_size
    total_items = len(items)
    successful_items = 0
    
    start_time = time.time()
    
    # Use tqdm to create progress bar
    logger.info(f"Starting to process {total_items} luxury goods items, batch size: {batch_size}")
    
    for i in tqdm(range(0, total_items, batch_size), desc="Processing data batches"):
        batch = items[i:i+batch_size]
        
        # Enrich data items
        enriched_batch = [enrich_item(item) for item in batch]
        
        # Add to vector store
        added_count, _ = vector_store.add_items(enriched_batch)
        successful_items += added_count
        
    elapsed_time = time.time() - start_time
    
    # Save vector store
    logger.info(f"Saving vector store to {output_dir}")
    vector_store.save(str(output_dir))
    
    # Output statistics
    success_rate = (successful_items / total_items) * 100 if total_items > 0 else 0
    logger.info(f"Vector store initialization complete:")
    logger.info(f"  - Total items processed: {total_items}")
    logger.info(f"  - Successfully added items: {successful_items} ({success_rate:.2f}%)")
    logger.info(f"  - Processing time: {elapsed_time:.2f} seconds")
    logger.info(f"  - Save location: {output_dir}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 