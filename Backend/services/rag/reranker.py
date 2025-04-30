"""
重排序器模块
提供检索结果重排序功能，优化相关性
"""

import logging
import numpy as np
from typing import List, Dict, Any, Optional, Tuple, Union, Callable
import time

from services.rag.text_embedder import TextEmbedder, get_embedder

# Setup logging
logger = logging.getLogger(__name__)

class Reranker:
    """结果重排序器基类"""
    
    def __init__(self):
        """初始化重排序器"""
        pass
    
    def rerank(self, 
              query: str, 
              results: List[Dict[str, Any]], 
              top_k: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        重排序搜索结果
        
        Args:
            query: 用户查询
            results: 初始搜索结果
            top_k: 返回结果数量
            
        Returns:
            重排序后的结果
        """
        raise NotImplementedError("Subclasses must implement rerank method")


class KeywordMatchReranker(Reranker):
    """基于关键词匹配的重排序器"""
    
    def __init__(self, 
                brand_boost: float = 0.2,
                model_boost: float = 0.15,
                material_boost: float = 0.1):
        """
        初始化关键词匹配重排序器
        
        Args:
            brand_boost: 品牌匹配提升权重
            model_boost: 型号匹配提升权重
            material_boost: 材质匹配提升权重
        """
        super().__init__()
        self.brand_boost = brand_boost
        self.model_boost = model_boost
        self.material_boost = material_boost
        
        logger.info(f"Initialized KeywordMatchReranker with boosts: brand={brand_boost}, model={model_boost}, material={material_boost}")
    
    def rerank(self, 
              query: str, 
              results: List[Dict[str, Any]], 
              top_k: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        基于关键词匹配重排序结果
        
        Args:
            query: 用户查询
            results: 初始搜索结果
            top_k: 返回结果数量，默认为None（返回所有结果）
            
        Returns:
            重排序后的结果
        """
        start_time = time.time()
        
        if not results:
            return []
        
        # 复制结果以避免修改原始数据
        reranked_results = [item.copy() for item in results]
        
        # 提取查询中的关键词
        query_words = query.lower().split()
        
        # 为每个结果计算新的分数
        for item in reranked_results:
            boost = 0
            
            # 检查品牌匹配
            if "brand" in item and item["brand"]:
                brand = item["brand"].lower()
                if brand in query.lower():
                    boost += self.brand_boost
                    # 精确品牌匹配更好
                    if brand in query_words:
                        boost += self.brand_boost / 2
            
            # 检查型号匹配
            if "model" in item and item["model"]:
                model = item["model"].lower()
                if model in query.lower():
                    boost += self.model_boost
                    # 精确型号匹配
                    model_words = model.split()
                    matched_words = [word for word in model_words if word in query_words]
                    if matched_words:
                        boost += self.model_boost * (len(matched_words) / len(model_words))
            
            # 检查材质匹配
            if "materials" in item and item["materials"]:
                for material in item["materials"]:
                    if material.lower() in query.lower():
                        boost += self.material_boost
                        break
            
            # 提高分数
            item["score"] = item.get("score", 0) + boost
            # 添加boost值到元数据中，用于调试
            if "metadata" not in item:
                item["metadata"] = {}
            item["metadata"]["keyword_boost"] = boost
        
        # 根据分数重新排序
        reranked_results.sort(key=lambda x: x.get("score", 0), reverse=True)
        
        # 限制结果数量
        if top_k is not None:
            reranked_results = reranked_results[:top_k]
        
        # 记录性能
        elapsed_time = time.time() - start_time
        logger.debug(f"KeywordMatchReranker completed in {elapsed_time:.3f}s for query: {query}")
        
        return reranked_results


class SemanticReranker(Reranker):
    """基于语义相似度的重排序器"""
    
    def __init__(self, embedder: Optional[TextEmbedder] = None):
        """
        初始化语义重排序器
        
        Args:
            embedder: 文本嵌入器，如果为None则自动创建
        """
        super().__init__()
        self.embedder = embedder or get_embedder()
        logger.info("Initialized SemanticReranker")
    
    def rerank(self, 
              query: str, 
              results: List[Dict[str, Any]], 
              top_k: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        基于语义相似度重排序结果
        
        Args:
            query: 用户查询
            results: 初始搜索结果
            top_k: 返回结果数量，默认为None（返回所有结果）
            
        Returns:
            重排序后的结果
        """
        start_time = time.time()
        
        if not results:
            return []
        
        # 复制结果以避免修改原始数据
        reranked_results = [item.copy() for item in results]
        
        try:
            # 获取查询的嵌入向量
            query_embedding = self.embedder.get_embedding(query)
            
            if query_embedding is None:
                logger.warning(f"Failed to get embedding for query: {query}")
                return reranked_results
            
            # 为每个结果计算语义相似度
            for item in reranked_results:
                # 构建项目表示文本
                item_text = ""
                if "brand" in item and item["brand"]:
                    item_text += f"Brand: {item['brand']} "
                if "model" in item and item["model"]:
                    item_text += f"Model: {item['model']} "
                if "description" in item and item["description"]:
                    item_text += f"Description: {item['description']} "
                
                if not item_text:
                    continue
                
                # 获取项目文本的嵌入向量
                item_embedding = self.embedder.get_embedding(item_text)
                
                if item_embedding is not None:
                    # 计算余弦相似度
                    similarity = self._cosine_similarity(query_embedding, item_embedding)
                    
                    # 更新分数
                    semantic_score = similarity * 0.5  # 权重因子
                    item["score"] = item.get("score", 0) + semantic_score
                    
                    # 添加语义分数到元数据中，用于调试
                    if "metadata" not in item:
                        item["metadata"] = {}
                    item["metadata"]["semantic_score"] = semantic_score
            
            # 根据分数重新排序
            reranked_results.sort(key=lambda x: x.get("score", 0), reverse=True)
            
            # 限制结果数量
            if top_k is not None:
                reranked_results = reranked_results[:top_k]
            
        except Exception as e:
            logger.error(f"Error in semantic reranking: {str(e)}", exc_info=True)
        
        # 记录性能
        elapsed_time = time.time() - start_time
        logger.debug(f"SemanticReranker completed in {elapsed_time:.3f}s for query: {query}")
        
        return reranked_results
    
    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """
        计算两个向量的余弦相似度
        
        Args:
            vec1: 第一个向量
            vec2: 第二个向量
            
        Returns:
            余弦相似度
        """
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return np.dot(vec1, vec2) / (norm1 * norm2)


class EnsembleReranker(Reranker):
    """集成多种重排序策略的重排序器"""
    
    def __init__(self, 
                rerankers: List[Reranker] = None,
                weights: List[float] = None):
        """
        初始化集成重排序器
        
        Args:
            rerankers: 重排序器列表
            weights: 各重排序器权重列表
        """
        super().__init__()
        
        # 默认使用关键词匹配和语义重排序
        if rerankers is None:
            self.rerankers = [KeywordMatchReranker(), SemanticReranker()]
        else:
            self.rerankers = rerankers
        
        # 默认权重均等分配
        if weights is None:
            self.weights = [1.0 / len(self.rerankers)] * len(self.rerankers)
        else:
            # 确保权重数量与重排序器数量匹配
            if len(weights) != len(self.rerankers):
                raise ValueError("Number of weights must match number of rerankers")
            # 归一化权重
            total = sum(weights)
            self.weights = [w / total for w in weights]
        
        logger.info(f"Initialized EnsembleReranker with {len(self.rerankers)} rerankers")
    
    def rerank(self, 
              query: str, 
              results: List[Dict[str, Any]], 
              top_k: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        使用多种重排序策略集成重排序结果
        
        Args:
            query: 用户查询
            results: 初始搜索结果
            top_k: 返回结果数量，默认为None（返回所有结果）
            
        Returns:
            重排序后的结果
        """
        start_time = time.time()
        
        if not results:
            return []
        
        # 复制结果以避免修改原始数据
        ensemble_results = [item.copy() for item in results]
        
        # 记录原始分数
        for item in ensemble_results:
            if "metadata" not in item:
                item["metadata"] = {}
            item["metadata"]["original_score"] = item.get("score", 0)
            item["score"] = 0  # 重置分数
        
        # 应用每个重排序器并结合分数
        for i, reranker in enumerate(self.rerankers):
            try:
                # 获取当前重排序器的结果
                reranker_results = reranker.rerank(query, ensemble_results)
                
                # 创建ID到结果的映射
                result_map = {}
                for r in reranker_results:
                    if "id" in r:
                        result_map[str(r["id"])] = r
                
                # 结合分数
                for item in ensemble_results:
                    if "id" in item:
                        reranked_item = result_map.get(str(item["id"]))
                        if reranked_item and "score" in reranked_item:
                            # 应用权重并累加分数
                            item["score"] += reranked_item["score"] * self.weights[i]
            except Exception as e:
                logger.error(f"Error applying reranker {type(reranker).__name__}: {str(e)}", exc_info=True)
        
        # 恢复原始分数的一部分（原始分数可能包含匹配质量信息）
        for item in ensemble_results:
            if "metadata" in item and "original_score" in item["metadata"]:
                item["score"] += item["metadata"]["original_score"] * 0.2  # 保留20%的原始分数
        
        # 根据分数重新排序
        ensemble_results.sort(key=lambda x: x.get("score", 0), reverse=True)
        
        # 限制结果数量
        if top_k is not None:
            ensemble_results = ensemble_results[:top_k]
        
        # 记录性能
        elapsed_time = time.time() - start_time
        logger.debug(f"EnsembleReranker completed in {elapsed_time:.3f}s for query: {query}")
        
        return ensemble_results


def get_reranker(reranker_type: str = "ensemble") -> Reranker:
    """
    获取指定类型的重排序器
    
    Args:
        reranker_type: 重排序器类型，可选 'keyword', 'semantic', 'ensemble'
        
    Returns:
        Reranker实例
    """
    if reranker_type.lower() == "keyword":
        return KeywordMatchReranker()
    elif reranker_type.lower() == "semantic":
        return SemanticReranker()
    elif reranker_type.lower() == "ensemble":
        return EnsembleReranker()
    else:
        logger.warning(f"Unknown reranker type: {reranker_type}, using ensemble reranker")
        return EnsembleReranker() 