#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
创建向量存储的脚本
从cleaned_listings.json读取数据，创建向量存储
"""

import os
import sys
import json
import logging
import argparse
from typing import Dict, List, Any
import time

# 将项目根目录添加到导入路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.rag.vector_store import VectorStore

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("vector_store_creator")

def load_listings(input_file: str) -> List[Dict[str, Any]]:
    """
    从指定文件加载数据列表
    
    Args:
        input_file: 输入文件路径
        
    Returns:
        加载的数据列表
    """
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if isinstance(data, list):
            logger.info(f"Successfully loaded {len(data)} listings from {input_file}")
            return data
        else:
            logger.error(f"Expected list in {input_file}, but got {type(data)}")
            return []
    except Exception as e:
        logger.error(f"Error loading listings from {input_file}: {str(e)}")
        return []

def create_vector_store(listings: List[Dict[str, Any]], output_dir: str, batch_size: int = 100) -> bool:
    """
    从奢侈品数据创建向量存储
    
    Args:
        listings: 奢侈品数据列表
        output_dir: 输出目录
        batch_size: 每批处理的数据量
        
    Returns:
        是否成功创建
    """
    if not listings:
        logger.error("No listings to process")
        return False
        
    try:
        start_time = time.time()
        logger.info(f"Creating vector store in {output_dir}")
        
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        # 初始化向量存储
        vector_store = VectorStore()
        
        # 批量处理，避免一次性处理过多项目
        total_items = len(listings)
        successful_items = 0
        
        for i in range(0, total_items, batch_size):
            batch = listings[i:i+batch_size]
            logger.info(f"Processing batch {i//batch_size + 1}/{(total_items-1)//batch_size + 1} ({len(batch)} items)")
            
            # 添加批量数据
            added_count = vector_store.add_items(batch)
            successful_items += added_count
            
            # 记录进度
            progress = (i + len(batch)) / total_items * 100
            logger.info(f"Progress: {progress:.1f}% ({successful_items}/{total_items} successful)")
            
        # 保存向量存储
        vector_store.save(output_dir)
        
        elapsed_time = time.time() - start_time
        logger.info(f"Vector store created successfully in {elapsed_time:.2f} seconds")
        logger.info(f"Successfully processed {successful_items}/{total_items} items")
        
        return True
        
    except Exception as e:
        logger.error(f"Error creating vector store: {str(e)}", exc_info=True)
        return False
        
def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="Create vector store from luxury listings")
    parser.add_argument("--input", "-i", default="data/cleaned_listings.json", 
                        help="Input JSON file with listings data")
    parser.add_argument("--output", "-o", default="data/vector_store", 
                        help="Output directory for vector store")
    parser.add_argument("--batch-size", "-b", type=int, default=100, 
                        help="Batch size for processing")
    parser.add_argument("--verbose", "-v", action="store_true", 
                        help="Enable verbose logging")
    
    args = parser.parse_args()
    
    # 设置更详细的日志级别（如果请求）
    if args.verbose:
        logger.setLevel(logging.DEBUG)
        
    logger.info(f"Starting vector store creation from {args.input} to {args.output}")
    
    # 加载数据
    listings = load_listings(args.input)
    if not listings:
        logger.error("No listings loaded, exiting")
        return 1
        
    # 创建向量存储
    success = create_vector_store(listings, args.output, args.batch_size)
    
    if success:
        logger.info("Vector store creation completed successfully")
        return 0
    else:
        logger.error("Vector store creation failed")
        return 1
        
if __name__ == "__main__":
    sys.exit(main()) 