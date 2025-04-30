"""
数据索引模块
负责将奢侈品数据导入向量存储系统
"""

import os
import sys
import logging
import json
from typing import List, Dict, Any, Optional

# 添加父目录到路径，确保能够导入依赖模块
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(os.path.dirname(current_dir))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

from services.rag.vector_store import VectorStore, save_vector_store
from utils.data_loader import load_json_data

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class LuxuryDataIndexer:
    """奢侈品数据索引器，负责将数据导入向量存储"""
    
    def __init__(self, vector_store: Optional[VectorStore] = None):
        """
        初始化数据索引器
        
        Args:
            vector_store: 可选的向量存储实例，如不提供则创建新实例
        """
        self.vector_store = vector_store if vector_store else VectorStore()
        
    def _transform_listing_to_item(self, listing: Dict[str, Any]) -> Dict[str, Any]:
        """
        将listing数据转换为向量存储项目格式
        
        Args:
            listing: 原始listing数据
            
        Returns:
            转换后的项目数据
        """
        item_details = listing.get('item_details', {})
        
        # 创建适合向量存储的项目
        item = {
            'id': listing.get('listing_id', ''),
            'source': listing.get('source_platform', ''),
            'brand': item_details.get('designer', ''),
            'model': item_details.get('model', ''),
            'size': item_details.get('size', []),
            'material': item_details.get('material', ''),
            'color': item_details.get('color', ''),
            'listing_price': listing.get('listing_price', 0),
            'condition_rating': listing.get('condition_rating', 3),
            'condition_category': listing.get('condition_category', ''),
            'description': '',  # 默认为空，如有额外描述可添加
            'features': [],
            'keywords': []
        }
        
        # 组装描述文本
        description_parts = []
        if item['brand']:
            description_parts.append(f"{item['brand']}")
        if item['model']:
            description_parts.append(f"{item['model']}")
        if item['material']:
            description_parts.append(f"made of {item['material']}")
        if item['color']:
            description_parts.append(f"in {item['color']} color")
            
        if description_parts:
            item['description'] = " ".join(description_parts)
            
        # 添加关键词
        keywords = []
        if item['brand']:
            keywords.append(item['brand'])
        if item['model']:
            keywords.append(item['model'])
        if item['material']:
            keywords.append(item['material'])
        if item['color']:
            keywords.append(item['color'])
            
        item['keywords'] = keywords
        
        return item
        
    def index_listings_data(self, listings_file: str) -> bool:
        """
        将listings数据索引到向量存储
        
        Args:
            listings_file: listings数据文件路径
            
        Returns:
            是否成功索引
        """
        # 加载listings数据
        listings = load_json_data(listings_file)
        if not listings:
            logger.error(f"Failed to load listings data from {listings_file}")
            return False
            
        logger.info(f"Loaded {len(listings)} listings from {listings_file}")
        
        # 转换为向量存储项目格式
        items = []
        for listing in listings:
            try:
                item = self._transform_listing_to_item(listing)
                items.append(item)
            except Exception as e:
                logger.error(f"Error transforming listing: {str(e)}", exc_info=True)
                
        # 添加到向量存储
        if not items:
            logger.error("No valid items to index")
            return False
            
        logger.info(f"Adding {len(items)} items to vector store")
        successful, total = self.vector_store.add_items(items)
        
        success_rate = (successful / total) if total > 0 else 0
        logger.info(f"Indexed {successful}/{total} items ({success_rate:.2%} success rate)")
        
        return successful > 0
    
    def save_index(self, directory: str) -> bool:
        """
        保存索引到指定目录
        
        Args:
            directory: 目录路径
            
        Returns:
            是否成功保存
        """
        try:
            if not os.path.exists(directory):
                os.makedirs(directory)
                
            return save_vector_store(self.vector_store, directory)
        except Exception as e:
            logger.error(f"Error saving index: {str(e)}", exc_info=True)
            return False
            
def index_luxury_data(
    data_file: str = 'data/cleaned_listings.json',
    output_dir: str = 'data/vector_store'
) -> bool:
    """
    索引奢侈品数据的便捷函数
    
    Args:
        data_file: 输入数据文件路径
        output_dir: 输出向量存储目录
        
    Returns:
        是否成功索引
    """
    try:
        indexer = LuxuryDataIndexer()
        success = indexer.index_listings_data(data_file)
        
        if success:
            return indexer.save_index(output_dir)
        return False
    except Exception as e:
        logger.error(f"Error indexing luxury data: {str(e)}", exc_info=True)
        return False

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Index luxury goods data into vector store")
    parser.add_argument(
        "--input", 
        default="data/cleaned_listings.json", 
        help="Input data file path"
    )
    parser.add_argument(
        "--output", 
        default="data/vector_store", 
        help="Output vector store directory"
    )
    
    args = parser.parse_args()
    
    success = index_luxury_data(args.input, args.output)
    
    if success:
        print(f"Successfully indexed luxury data from {args.input} to {args.output}")
        sys.exit(0)
    else:
        print(f"Failed to index luxury data")
        sys.exit(1) 