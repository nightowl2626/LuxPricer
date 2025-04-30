"""
初始化RAG系统
加载数据并创建向量存储
"""

import os
import json
import argparse
import logging
from typing import Optional, Dict, Any
import time
from datetime import datetime

from data_processor import LuxuryDataProcessor
from vector_store import VectorStore

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class RAGInitializer:
    """RAG系统初始化器"""
    
    def __init__(self, 
                 data_dir: str = "data",
                 vector_store_dir: str = "vector_store",
                 cache_dir: str = "cache"):
        """
        初始化RAG初始化器
        
        Args:
            data_dir: 数据目录
            vector_store_dir: 向量存储目录
            cache_dir: 缓存目录
        """
        # 创建必要的目录
        self.data_dir = data_dir
        self.vector_store_dir = vector_store_dir
        self.cache_dir = cache_dir
        self.processed_data_path = os.path.join(self.data_dir, "processed_luxury_items.json")
        
        self._ensure_directories()
        
        # 初始化组件
        self.data_processor = LuxuryDataProcessor()
        self.vector_store = None
        
        # 状态
        self.initialization_state = {
            "status": "not_initialized",
            "data_processed": False,
            "vector_store_created": False,
            "last_updated": None,
            "error": None,
            "stats": {}
        }
    
    def _ensure_directories(self):
        """确保所需目录存在"""
        for dir_path in [self.data_dir, self.vector_store_dir, self.cache_dir]:
            os.makedirs(dir_path, exist_ok=True)
            logger.info(f"Ensured directory exists: {dir_path}")
    
    def load_data(self, data_path: str) -> bool:
        """
        加载原始数据
        
        Args:
            data_path: 数据文件路径
            
        Returns:
            是否成功加载数据
        """
        logger.info(f"Loading data from {data_path}")
        success = self.data_processor.load_json_data(data_path)
        
        if success:
            self.initialization_state["data_loaded"] = True
            self.initialization_state["data_source"] = data_path
            logger.info(f"Successfully loaded data from {data_path}")
        else:
            self.initialization_state["error"] = f"Failed to load data from {data_path}"
            logger.error(self.initialization_state["error"])
            
        return success
    
    def process_data(self) -> bool:
        """
        处理数据
        
        Returns:
            是否成功处理数据
        """
        logger.info("Processing luxury item data")
        start_time = time.time()
        processed_data = self.data_processor.process_data()
        process_time = time.time() - start_time
        
        if processed_data:
            # 保存处理后的数据
            success = self.data_processor.save_processed_data(self.processed_data_path)
            if success:
                self.initialization_state["data_processed"] = True
                self.initialization_state["process_time"] = process_time
                self.initialization_state["stats"]["data_processing"] = self.data_processor.get_statistics()
                logger.info(f"Successfully processed and saved data to {self.processed_data_path}")
                return True
            else:
                self.initialization_state["error"] = "Failed to save processed data"
                logger.error(self.initialization_state["error"])
                return False
        else:
            self.initialization_state["error"] = "No data to process"
            logger.error(self.initialization_state["error"])
            return False
    
    def create_vector_store(self) -> bool:
        """
        创建向量存储
        
        Returns:
            是否成功创建向量存储
        """
        if not os.path.exists(self.processed_data_path):
            self.initialization_state["error"] = f"Processed data not found at {self.processed_data_path}"
            logger.error(self.initialization_state["error"])
            return False
        
        logger.info("Loading processed data for vector store creation")
        try:
            with open(self.processed_data_path, "r", encoding="utf-8") as f:
                processed_items = json.load(f)
            
            if not processed_items:
                self.initialization_state["error"] = "Processed data is empty"
                logger.error(self.initialization_state["error"])
                return False
            
            logger.info(f"Creating vector store with {len(processed_items)} items")
            start_time = time.time()
            self.vector_store = VectorStore()
            self.vector_store.add_items(processed_items)
            vector_store_time = time.time() - start_time
            
            # 保存向量存储
            vector_store_path = os.path.join(self.vector_store_dir, "luxury_items_store")
            success = self.vector_store.save(vector_store_path)
            
            if success:
                self.initialization_state["vector_store_created"] = True
                self.initialization_state["vector_store_path"] = vector_store_path
                self.initialization_state["vector_store_time"] = vector_store_time
                logger.info(f"Successfully created and saved vector store to {vector_store_path}")
                return True
            else:
                self.initialization_state["error"] = "Failed to save vector store"
                logger.error(self.initialization_state["error"])
                return False
            
        except Exception as e:
            self.initialization_state["error"] = f"Error creating vector store: {str(e)}"
            logger.error(self.initialization_state["error"], exc_info=True)
            return False
    
    def load_vector_store(self) -> bool:
        """
        加载向量存储
        
        Returns:
            是否成功加载向量存储
        """
        vector_store_path = os.path.join(self.vector_store_dir, "luxury_items_store")
        if not os.path.exists(vector_store_path):
            self.initialization_state["error"] = f"Vector store not found at {vector_store_path}"
            logger.error(self.initialization_state["error"])
            return False
        
        try:
            logger.info(f"Loading vector store from {vector_store_path}")
            self.vector_store = VectorStore()
            success = self.vector_store.load(vector_store_path)
            
            if success:
                self.initialization_state["vector_store_loaded"] = True
                logger.info(f"Successfully loaded vector store from {vector_store_path}")
                return True
            else:
                self.initialization_state["error"] = "Failed to load vector store"
                logger.error(self.initialization_state["error"])
                return False
        except Exception as e:
            self.initialization_state["error"] = f"Error loading vector store: {str(e)}"
            logger.error(self.initialization_state["error"], exc_info=True)
            return False
    
    def test_search(self, query: str, k: int = 5) -> Optional[Dict[str, Any]]:
        """
        测试向量存储搜索
        
        Args:
            query: 搜索查询
            k: 返回结果数量
            
        Returns:
            搜索结果
        """
        if not self.vector_store:
            logger.error("Vector store not initialized")
            return None
        
        try:
            logger.info(f"Testing search with query: '{query}'")
            results = self.vector_store.search(query, k=k)
            logger.info(f"Search returned {len(results)} results")
            return {
                "query": query,
                "results": results
            }
        except Exception as e:
            logger.error(f"Error during search: {str(e)}", exc_info=True)
            return None
    
    def initialize(self, data_path: str, force_reindex: bool = False) -> bool:
        """
        初始化RAG系统
        
        Args:
            data_path: 数据文件路径
            force_reindex: 是否强制重建索引
            
        Returns:
            是否成功初始化
        """
        logger.info(f"Initializing RAG system with data from {data_path}")
        self.initialization_state["status"] = "initializing"
        self.initialization_state["start_time"] = datetime.now().isoformat()
        
        # 如果不强制重建索引且向量存储已存在，直接加载
        vector_store_path = os.path.join(self.vector_store_dir, "luxury_items_store")
        if not force_reindex and os.path.exists(vector_store_path):
            logger.info("Found existing vector store, loading it")
            if self.load_vector_store():
                self.initialization_state["status"] = "initialized"
                self.initialization_state["last_updated"] = datetime.now().isoformat()
                return True
            else:
                logger.warning("Failed to load existing vector store, will create a new one")
        
        # 加载并处理数据
        if not self.load_data(data_path):
            self.initialization_state["status"] = "failed"
            return False
        
        if not self.process_data():
            self.initialization_state["status"] = "failed"
            return False
        
        # 创建向量存储
        if not self.create_vector_store():
            self.initialization_state["status"] = "failed"
            return False
        
        self.initialization_state["status"] = "initialized"
        self.initialization_state["last_updated"] = datetime.now().isoformat()
        logger.info("RAG system successfully initialized")
        
        # 测试搜索功能
        test_queries = [
            "Louis Vuitton bag",
            "Rolex watch",
            "Chanel classic flap",
            "Hermes Birkin"
        ]
        test_results = {}
        for query in test_queries:
            test_results[query] = self.test_search(query, k=3)
        
        self.initialization_state["test_searches"] = test_results
        
        # 保存初始化状态
        self._save_initialization_state()
        return True
    
    def _save_initialization_state(self):
        """保存初始化状态"""
        state_path = os.path.join(self.cache_dir, "initialization_state.json")
        try:
            with open(state_path, "w", encoding="utf-8") as f:
                json.dump(self.initialization_state, f, ensure_ascii=False, indent=2)
            logger.info(f"Saved initialization state to {state_path}")
        except Exception as e:
            logger.error(f"Failed to save initialization state: {str(e)}")
    
    def get_initialization_state(self) -> Dict[str, Any]:
        """
        获取初始化状态
        
        Returns:
            初始化状态
        """
        return self.initialization_state


def main():
    """主入口函数"""
    parser = argparse.ArgumentParser(description="Initialize RAG system")
    parser.add_argument("--data_path", type=str, required=True, help="Path to the data file")
    parser.add_argument("--force_reindex", action="store_true", help="Force reindexing even if vector store exists")
    parser.add_argument("--test_query", type=str, help="Test query to run after initialization")
    args = parser.parse_args()
    
    initializer = RAGInitializer()
    success = initializer.initialize(args.data_path, args.force_reindex)
    
    if success and args.test_query:
        results = initializer.test_search(args.test_query)
        if results:
            print(f"\nTest query: {args.test_query}")
            print("\nResults:")
            for i, result in enumerate(results["results"]):
                print(f"\n{i+1}. {result.get('brand', '')} {result.get('model', '')} - {result.get('category', '')}")
                if "price" in result:
                    print(f"   Price: ${result['price']:,.2f}" if isinstance(result['price'], (int, float)) else f"   Price: {result['price']}")
                if "description" in result:
                    desc = result["description"]
                    if len(desc) > 100:
                        desc = desc[:97] + "..."
                    print(f"   Description: {desc}")
    
    return 0 if success else 1


if __name__ == "__main__":
    exit(main()) 