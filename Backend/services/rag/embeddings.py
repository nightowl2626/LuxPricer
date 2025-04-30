"""
嵌入模型模块
提供不同的嵌入模型实现，用于生成文本的向量表示
"""

import os
import logging
from typing import List, Union, Dict, Any, Optional
import numpy as np

# 设置日志
logger = logging.getLogger(__name__)

class EmbeddingModel:
    """
    嵌入模型基类
    """
    def __init__(self):
        pass
    
    def encode(self, texts: Union[str, List[str]]) -> List[List[float]]:
        """
        将文本编码为向量
        
        Args:
            texts: 单个文本或文本列表
            
        Returns:
            向量表示列表
        """
        raise NotImplementedError("Subclasses must implement this method")


class OpenAIEmbedding(EmbeddingModel):
    """
    OpenAI嵌入模型
    """
    def __init__(self, model: str = "text-embedding-3-small"):
        """
        初始化OpenAI嵌入模型
        
        Args:
            model: 模型名称，默认为text-embedding-3-small
        """
        super().__init__()
        self.model = model
        
        # 导入必要的模块
        try:
            import openai
            from openai import OpenAI
            self.openai = openai
            self.client = OpenAI()
            logger.info(f"Initialized OpenAI embedding model: {model}")
        except ImportError:
            logger.error("OpenAI package not installed. Please install it with: pip install openai")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {e}")
            raise
    
    def encode(self, texts: Union[str, List[str]]) -> List[List[float]]:
        """
        使用OpenAI API将文本编码为向量
        
        Args:
            texts: 单个文本或文本列表
            
        Returns:
            向量表示列表
        """
        # 确保texts是列表
        if isinstance(texts, str):
            texts = [texts]
        
        try:
            # 调用OpenAI API
            response = self.client.embeddings.create(
                model=self.model,
                input=texts,
                encoding_format="float"
            )
            
            # 提取向量
            embeddings = [item.embedding for item in response.data]
            
            logger.debug(f"Generated {len(embeddings)} embeddings using OpenAI model: {self.model}")
            return embeddings
        except Exception as e:
            logger.error(f"Error generating OpenAI embeddings: {e}")
            # 返回零向量作为后备
            dim = 1536 if "text-embedding-3" in self.model else 1024  # OpenAI模型维度
            return [[0.0] * dim] * len(texts)


class HuggingFaceEmbedding(EmbeddingModel):
    """
    基于HuggingFace模型的嵌入实现
    """
    def __init__(self, model: str = "BAAI/bge-small-en-v1.5"):
        """
        初始化HuggingFace嵌入模型
        
        Args:
            model: 模型名称，默认为BAAI/bge-small-en-v1.5
        """
        super().__init__()
        self.model_name = model
        
        # 导入必要的模块
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(model)
            logger.info(f"Initialized HuggingFace embedding model: {model}")
        except ImportError:
            logger.error("sentence-transformers package not installed. Please install it with: pip install sentence-transformers")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize HuggingFace model {model}: {e}")
            raise
    
    def encode(self, texts: Union[str, List[str]]) -> List[List[float]]:
        """
        使用HuggingFace模型将文本编码为向量
        
        Args:
            texts: 单个文本或文本列表
            
        Returns:
            向量表示列表
        """
        # 确保texts是列表
        if isinstance(texts, str):
            texts = [texts]
        
        try:
            # 使用SentenceTransformer模型生成嵌入
            embeddings = self.model.encode(texts, convert_to_numpy=True)
            
            # 转换为列表
            if isinstance(embeddings, np.ndarray):
                embeddings = embeddings.tolist()
            
            logger.debug(f"Generated {len(embeddings)} embeddings using HuggingFace model: {self.model_name}")
            return embeddings
        except Exception as e:
            logger.error(f"Error generating HuggingFace embeddings: {e}")
            # 返回零向量作为后备
            dim = 384  # BGE模型默认维度
            return [[0.0] * dim] * len(texts)


def get_embedding_model(provider: str = "openai", model: Optional[str] = None) -> EmbeddingModel:
    """
    根据提供者和模型名获取嵌入模型实例
    
    Args:
        provider: 模型提供者，支持"openai"和"huggingface"
        model: 模型名称，默认为None（使用提供者默认模型）
        
    Returns:
        EmbeddingModel实例
        
    Raises:
        ValueError: 如果提供者不支持
    """
    provider = provider.lower()
    
    if provider == "openai":
        if model is None:
            model = "text-embedding-3-small"
        return OpenAIEmbedding(model=model)
    elif provider == "huggingface":
        if model is None:
            model = "BAAI/bge-small-en-v1.5"
        return HuggingFaceEmbedding(model=model)
    else:
        raise ValueError(f"Unsupported embedding provider: {provider}. "
                         f"Supported providers are: openai, huggingface") 