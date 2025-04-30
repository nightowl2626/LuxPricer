"""
文本嵌入器模块
负责生成文本的嵌入向量，支持多种嵌入模型提供商
"""

import os
import logging
import numpy as np
from typing import Optional, Dict, Any, List, Union

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TextEmbedder:
    """文本嵌入器类，支持多种嵌入模型"""
    
    def __init__(self, provider: str = "openai", model: Optional[str] = None):
        """
        初始化文本嵌入器
        
        Args:
            provider: 嵌入模型提供商，支持 "openai", "azure", "local"
            model: 嵌入模型名称，如果为None则使用提供商默认模型
        """
        self.provider = provider.lower()
        self.model = model
        self.client = None
        self.embedding_dim = 1536  # 默认维度，可能会根据模型变化
        
        # 初始化客户端
        self._init_client()
        
        logger.info(f"Initialized TextEmbedder with provider: {provider}")
    
    def _init_client(self):
        """初始化嵌入模型客户端"""
        try:
            if self.provider == "openai":
                import openai
                api_key = os.environ.get("OPENAI_API_KEY")
                if not api_key:
                    logger.warning("OPENAI_API_KEY not found in environment variables")
                
                self.client = openai.OpenAI(api_key=api_key)
                self.model = self.model or "text-embedding-3-small"
                
                # 更新维度
                if self.model == "text-embedding-3-small":
                    self.embedding_dim = 1536
                elif self.model == "text-embedding-3-large":
                    self.embedding_dim = 3072
                elif self.model == "text-embedding-ada-002":
                    self.embedding_dim = 1536
                
            elif self.provider == "azure":
                import openai
                api_key = os.environ.get("AZURE_OPENAI_API_KEY")
                api_base = os.environ.get("AZURE_OPENAI_API_BASE")
                api_version = os.environ.get("AZURE_OPENAI_API_VERSION", "2023-05-15")
                api_type = "azure"
                
                if not api_key or not api_base:
                    logger.warning("Azure OpenAI credentials not found in environment variables")
                
                self.client = openai.AzureOpenAI(
                    api_key=api_key,
                    api_version=api_version,
                    azure_endpoint=api_base
                )
                
                # 使用部署名称作为模型
                self.model = self.model or os.environ.get("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-ada-002")
                self.embedding_dim = 1536  # Azure OpenAI 嵌入模型维度
                
            elif self.provider == "local":
                # 本地嵌入模型，例如使用sentence-transformers
                try:
                    from sentence_transformers import SentenceTransformer
                    self.model = self.model or "all-MiniLM-L6-v2"
                    self.client = SentenceTransformer(self.model)
                    
                    # 获取模型维度
                    self.embedding_dim = self.client.get_sentence_embedding_dimension()
                    
                except ImportError:
                    logger.error("sentence-transformers package not installed. Please install it with `pip install sentence-transformers`")
                    raise
            else:
                logger.warning(f"Unsupported provider: {self.provider}, falling back to OpenAI")
                self._fallback_to_openai()
                
        except Exception as e:
            logger.error(f"Error initializing client for provider {self.provider}: {str(e)}", exc_info=True)
            self._fallback_to_openai()
    
    def _fallback_to_openai(self):
        """当主要提供商失败时，回退到OpenAI"""
        try:
            import openai
            api_key = os.environ.get("OPENAI_API_KEY")
            if not api_key:
                logger.warning("OPENAI_API_KEY not found in environment variables")
            
            self.provider = "openai"
            self.model = "text-embedding-3-small"
            self.client = openai.OpenAI(api_key=api_key)
            self.embedding_dim = 1536
            
            logger.info("Fallback to OpenAI embedding model")
            
        except Exception as e:
            logger.error(f"Failed to fallback to OpenAI: {str(e)}", exc_info=True)
            self.client = None
    
    def get_embedding(self, text: str) -> Optional[np.ndarray]:
        """
        获取文本的嵌入向量
        
        Args:
            text: 输入文本
            
        Returns:
            嵌入向量，如果失败则返回None
        """
        if not text:
            logger.warning("Empty text provided for embedding")
            return None
        
        if not self.client:
            logger.error("No embedding client available")
            return None
        
        try:
            if self.provider == "openai":
                response = self.client.embeddings.create(
                    model=self.model,
                    input=text
                )
                embedding = response.data[0].embedding
                return np.array(embedding, dtype=np.float32)
                
            elif self.provider == "azure":
                response = self.client.embeddings.create(
                    model=self.model,
                    input=text
                )
                embedding = response.data[0].embedding
                return np.array(embedding, dtype=np.float32)
                
            elif self.provider == "local":
                embedding = self.client.encode(text)
                return np.array(embedding, dtype=np.float32)
                
            else:
                logger.error(f"Unsupported provider: {self.provider}")
                return None
                
        except Exception as e:
            logger.error(f"Error generating embedding: {str(e)}", exc_info=True)
            return None
    
    def get_embeddings(self, texts: List[str]) -> Optional[np.ndarray]:
        """
        批量获取多个文本的嵌入向量
        
        Args:
            texts: 输入文本列表
            
        Returns:
            嵌入向量列表，如果失败则返回None
        """
        if not texts:
            logger.warning("Empty texts list provided for embeddings")
            return None
        
        if not self.client:
            logger.error("No embedding client available")
            return None
        
        try:
            if self.provider == "openai":
                response = self.client.embeddings.create(
                    model=self.model,
                    input=texts
                )
                embeddings = [data.embedding for data in response.data]
                return np.array(embeddings, dtype=np.float32)
                
            elif self.provider == "azure":
                response = self.client.embeddings.create(
                    model=self.model,
                    input=texts
                )
                embeddings = [data.embedding for data in response.data]
                return np.array(embeddings, dtype=np.float32)
                
            elif self.provider == "local":
                embeddings = self.client.encode(texts)
                return np.array(embeddings, dtype=np.float32)
                
            else:
                logger.error(f"Unsupported provider: {self.provider}")
                return None
                
        except Exception as e:
            logger.error(f"Error generating embeddings: {str(e)}", exc_info=True)
            return None
    
    def get_embedding_dimension(self) -> int:
        """
        获取嵌入向量维度
        
        Returns:
            嵌入向量维度
        """
        return self.embedding_dim


def get_embedder(provider: str = "openai", model: Optional[str] = None) -> TextEmbedder:
    """
    获取文本嵌入器实例
    
    Args:
        provider: 嵌入模型提供商
        model: 嵌入模型名称
        
    Returns:
        TextEmbedder实例
    """
    return TextEmbedder(provider=provider, model=model) 