"""
向量存储模块
使用FAISS管理奢侈品数据的向量索引和搜索
"""

import os
import json
import logging
import pickle
from typing import List, Dict, Any, Optional, Tuple, Union
import numpy as np

try:
    import faiss
except ImportError:
    logging.error("FAISS is not installed. Please install it with `pip install faiss-cpu` or `pip install faiss-gpu`")
    raise

from services.rag.text_embedder import TextEmbedder

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class VectorStore:
    """使用FAISS的向量存储类"""
    
    def __init__(self, embedding_dim: int = 1536):
        """
        初始化向量存储
        
        Args:
            embedding_dim: 嵌入向量维度
        """
        self.embedding_dim = embedding_dim
        self.index = None
        self.items = []
        self.embedder = TextEmbedder()
        
        # 初始化FAISS索引
        self._init_index()
    
    def _init_index(self):
        """初始化FAISS索引"""
        try:
            self.index = faiss.IndexFlatL2(self.embedding_dim)
            logger.info(f"Initialized FAISS index with dimension {self.embedding_dim}")
        except Exception as e:
            logger.error(f"Failed to initialize FAISS index: {str(e)}", exc_info=True)
            raise
    
    def _get_item_text(self, item: Dict[str, Any]) -> str:
        """
        从项目中提取文本用于嵌入 - 支持原始cleaned_listings.json格式
        
        Args:
            item: 奢侈品项目字典
            
        Returns:
            用于嵌入的文本表示
        """
        texts = []
        
        # 提取基本信息
        listing_name = item.get('listing_name', '')
        if listing_name:
            texts.append(f"Listing: {listing_name}")
        
        # 提取物品详情
        item_details = item.get('item_details', {})
        if isinstance(item_details, dict):
            # 添加设计师/品牌
            designer = item_details.get('designer', '')
            if designer:
                texts.append(f"Designer: {designer}")
            
            # 添加型号
            model = item_details.get('model', '')
            if model:
                texts.append(f"Model: {model}")
            
            # 添加类别
            category = item_details.get('category', '')
            if category:
                texts.append(f"Category: {category}")
            
            # 添加材质
            material = item_details.get('material', '')
            if material:
                texts.append(f"Material: {material}")
            
            # 添加颜色
            color = item_details.get('color', '')
            if color:
                texts.append(f"Color: {color}")
            
            # 添加描述
            description = item_details.get('item_description', '')
            if description:
                texts.append(f"Description: {description}")
            
            # 添加尺寸
            size = item_details.get('size', '')
            if size:
                texts.append(f"Size: {size}")
        
        # 添加价格信息
        price = item.get('listing_price')
        if price is not None:
            texts.append(f"Price: {price}")
        
        # 添加状态信息
        condition = item.get('condition_description', '')
        if condition:
            if isinstance(condition, list):
                condition = ', '.join(condition)
            texts.append(f"Condition: {condition}")
        
        # 添加平台
        platform = item.get('source_platform', '')
        if platform:
            texts.append(f"Platform: {platform}")
        
        # 添加包含物品
        inclusions = item.get('inclusions', [])
        if inclusions and isinstance(inclusions, list):
            inclusions_text = ', '.join(inclusions)
            texts.append(f"Inclusions: {inclusions_text}")
        
        # 如果没有足够文本，使用所有非空字段
        if len(texts) < 3:
            for key, value in item.items():
                if value and key not in ['id', 'listing_id'] and isinstance(value, (str, int, float)):
                    texts.append(f"{key}: {value}")
        
        # 如果仍然没有文本，使用简单的标识符
        if not texts:
            texts.append(f"Item ID: {item.get('id', '') or item.get('listing_id', 'unknown')}")
        
        return ' '.join(texts)
    
    def _get_embedding(self, text: str) -> np.ndarray:
        """
        获取文本的嵌入向量
        
        Args:
            text: 输入文本
            
        Returns:
            嵌入向量
        """
        return self.embedder.get_embedding(text)
    
    def add_item(self, item: Dict[str, Any]) -> bool:
        """
        添加单个项目到向量存储
        
        Args:
            item: 奢侈品项目字典
            
        Returns:
            是否成功添加
        """
        try:
            # 获取项目文本
            item_text = self._get_item_text(item)
            
            # 获取嵌入向量
            embedding = self._get_embedding(item_text)
            if embedding is None:
                logger.error(f"Failed to get embedding for item: {item.get('brand', '')} {item.get('model', '')}")
                return False
            
            # 将向量添加到FAISS索引
            embedding_np = np.array([embedding], dtype=np.float32)
            self.index.add(embedding_np)
            
            # 保存项目
            self.items.append(item)
            
            logger.debug(f"Added item to vector store: {item.get('brand', '')} {item.get('model', '')}")
            return True
        except Exception as e:
            logger.error(f"Error adding item to vector store: {str(e)}", exc_info=True)
            return False
    
    def add_items(self, items: List[Dict[str, Any]]) -> Tuple[int, int]:
        """
        批量添加项目到向量存储
        
        Args:
            items: 奢侈品项目字典列表
            
        Returns:
            成功添加的项目数量和总项目数量的元组
        """
        if not items:
            logger.warning("No items to add to vector store")
            return 0, 0
        
        successful_additions = 0
        total_items = len(items)
        
        # 收集所有嵌入向量
        all_embeddings = []
        items_to_add = []
        
        logger.info(f"Adding {total_items} items to vector store")
        
        for item in items:
            try:
                # 获取项目文本
                item_text = self._get_item_text(item)
                
                # 获取嵌入向量
                embedding = self._get_embedding(item_text)
                if embedding is not None:
                    all_embeddings.append(embedding)
                    items_to_add.append(item)
                    successful_additions += 1
                else:
                    logger.warning(f"Failed to get embedding for item: {item.get('brand', '')} {item.get('model', '')}")
            except Exception as e:
                logger.error(f"Error processing item: {str(e)}", exc_info=True)
        
        # 批量添加到FAISS索引
        if all_embeddings:
            try:
                embeddings_np = np.array(all_embeddings, dtype=np.float32)
                self.index.add(embeddings_np)
                self.items.extend(items_to_add)
                logger.info(f"Successfully added {successful_additions} items to vector store")
            except Exception as e:
                logger.error(f"Error adding embeddings to FAISS index: {str(e)}", exc_info=True)
                return 0, total_items
        
        return successful_additions, total_items
    
    def search(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """
        Search for items related to the query
        
        Args:
            query: Search query
            k: Number of results to return
            
        Returns:
            List of related items
        """
        if not self.index or self.index.ntotal == 0:
            logger.warning("Index is empty, cannot perform search")
            return []
        
        if not query:
            logger.warning("Empty query, cannot perform search")
            return []
        
        logger.info(f"Vector search - Query: '{query}', Requested results: {k}, Total items in index: {self.index.ntotal}")
        
        # Get embedding vector for the query
        query_embedding = self._get_embedding(query)
        if query_embedding is None:
            logger.error("Failed to get embedding for query")
            return []
        
        logger.info(f"Vector search - Obtained embedding vector for query (dimension: {len(query_embedding)})")
        
        # Execute search
        query_embedding_np = np.array([query_embedding], dtype=np.float32)
        k_search = min(k, len(self.items))
        logger.info(f"Vector search - Executing FAISS search, result count: {k_search}")
        
        distances, indices = self.index.search(query_embedding_np, k_search)
        
        # Output raw results
        logger.info(f"Vector search - Raw search results:")
        for i, (idx, distance) in enumerate(zip(indices[0], distances[0])):
            if idx >= 0 and idx < len(self.items):
                item = self.items[idx]
                item_name = item.get('listing_name') or item.get('item_details', {}).get('model') or f"Item #{idx}"
                logger.info(f"  [{i+1}] Index: {idx}, Distance: {distance:.4f}, Item: {item_name}")
        
        # Build results
        results = []
        for i, idx in enumerate(indices[0]):
            if idx >= 0 and idx < len(self.items):  # Ensure valid index
                item = self.items[idx].copy()
                distance = distances[0][i]
                similarity_score = float(1.0 / (1.0 + distance))  # Convert distance to similarity score
                item['score'] = similarity_score
                results.append(item)
                logger.info(f"  Result[{i+1}] Distance: {distance:.4f}, Similarity: {similarity_score:.4f}")
        
        logger.info(f"Vector search - Returning {len(results)} results")
            
        return results
    
    def save(self, directory: str) -> bool:
        """
        保存向量存储到文件
        
        Args:
            directory: 目录路径
            
        Returns:
            是否成功保存
        """
        try:
            os.makedirs(directory, exist_ok=True)
            
            # 保存FAISS索引
            index_path = os.path.join(directory, "index.faiss")
            faiss.write_index(self.index, index_path)
            
            # 保存项目数据
            items_path = os.path.join(directory, "items.json")
            with open(items_path, "w", encoding="utf-8") as f:
                json.dump(self.items, f, ensure_ascii=False, indent=2)
            
            # 保存元数据
            metadata = {
                "embedding_dim": self.embedding_dim,
                "num_items": len(self.items)
            }
            metadata_path = os.path.join(directory, "metadata.json")
            with open(metadata_path, "w", encoding="utf-8") as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Successfully saved vector store to {directory}")
            return True
        except Exception as e:
            logger.error(f"Error saving vector store: {str(e)}", exc_info=True)
            return False
    
    def load(self, directory: str) -> bool:
        """
        从文件加载向量存储
        
        Args:
            directory: 目录路径
            
        Returns:
            是否成功加载
        """
        try:
            # 检查目录和文件是否存在
            if not os.path.exists(directory):
                logger.error(f"Directory does not exist: {directory}")
                return False
            
            index_path = os.path.join(directory, "index.faiss")
            items_path = os.path.join(directory, "items.json")
            metadata_path = os.path.join(directory, "metadata.json")
            
            for path in [index_path, items_path, metadata_path]:
                if not os.path.exists(path):
                    logger.error(f"Required file does not exist: {path}")
                    return False
            
            # 加载元数据
            with open(metadata_path, "r", encoding="utf-8") as f:
                metadata = json.load(f)
            
            # 更新嵌入维度
            self.embedding_dim = metadata.get("embedding_dim", 1536)
            
            # 加载FAISS索引
            self.index = faiss.read_index(index_path)
            
            # 加载项目数据
            with open(items_path, "r", encoding="utf-8") as f:
                self.items = json.load(f)
            
            logger.info(f"Successfully loaded vector store from {directory} with {len(self.items)} items")
            return True
        except Exception as e:
            logger.error(f"Error loading vector store: {str(e)}", exc_info=True)
            return False
    
    def get_all_items(self) -> List[Dict[str, Any]]:
        """
        获取所有项目
        
        Returns:
            所有项目列表
        """
        return self.items.copy()
    
    def get_item_by_index(self, index: int) -> Optional[Dict[str, Any]]:
        """
        根据索引获取项目
        
        Args:
            index: 项目索引
            
        Returns:
            项目字典或None
        """
        if 0 <= index < len(self.items):
            return self.items[index].copy()
        return None
    
    def get_index_stats(self) -> Dict[str, Any]:
        """
        获取索引统计信息
        
        Returns:
            索引统计信息
        """
        if not self.index:
            return {
                "status": "not_initialized",
                "num_items": 0,
                "embedding_dim": self.embedding_dim
            }
        
        return {
            "status": "initialized",
            "num_items": self.index.ntotal,
            "embedding_dim": self.embedding_dim
        }


def get_vector_store(embedding_dim: int = 1536) -> VectorStore:
    """
    获取向量存储实例
    
    Args:
        embedding_dim: 嵌入向量维度
        
    Returns:
        VectorStore实例
    """
    return VectorStore(embedding_dim=embedding_dim)


def load_vector_store(directory: str) -> Optional[VectorStore]:
    """
    从目录加载向量存储
    
    Args:
        directory: 加载目录
        
    Returns:
        VectorStore实例，如果加载失败则返回None
    """
    try:
        store = VectorStore()
        if store.load(directory):
            return store
        else:
            logger.error(f"Failed to load vector store from {directory}")
            return None
    except Exception as e:
        logger.error(f"Failed to load vector store from {directory}: {e}")
        return None
        
        
def save_vector_store(store: VectorStore, directory: str) -> bool:
    """
    保存向量存储到目录
    
    Args:
        store: VectorStore实例
        directory: 保存目录
        
    Returns:
        保存成功返回True，否则返回False
    """
    try:
        store.save(directory)
        return True
    except Exception as e:
        logger.error(f"Failed to save vector store to {directory}: {e}")
        return False 