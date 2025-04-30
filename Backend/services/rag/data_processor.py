"""
数据处理模块
用于加载和预处理奢侈品相关数据
"""

import os
import json
import logging
from typing import List, Dict, Any, Optional, Union
import re
from datetime import datetime

# 设置日志
logger = logging.getLogger(__name__)

class LuxuryDataProcessor:
    """
    奢侈品数据处理类
    用于加载、清洗和标准化奢侈品数据
    """
    
    def __init__(self):
        """初始化数据处理器"""
        self.raw_data = []
        self.processed_data = []
        self.stats = {
            "total_items": 0,
            "items_with_price": 0,
            "items_with_brand": 0,
            "items_with_model": 0,
            "items_with_category": 0,
            "brands": set(),
            "categories": set(),
            "processed_at": None
        }
    
    def load_json_data(self, file_path: str) -> bool:
        """
        从JSON文件加载数据
        
        Args:
            file_path: JSON文件路径
            
        Returns:
            是否加载成功
        """
        try:
            if not os.path.exists(file_path):
                logger.error(f"File not found: {file_path}")
                return False
                
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            if isinstance(data, list):
                self.raw_data = data
            elif isinstance(data, dict) and "items" in data:
                self.raw_data = data["items"]
            else:
                logger.error(f"Unexpected data format in {file_path}")
                return False
                
            logger.info(f"Loaded {len(self.raw_data)} items from {file_path}")
            return True
        except Exception as e:
            logger.error(f"Error loading data from {file_path}: {e}")
            return False
    
    def process_data(self) -> List[Dict[str, Any]]:
        """
        处理和标准化数据
        
        Returns:
            处理后的数据列表
        """
        if not self.raw_data:
            logger.warning("No data to process")
            return []
            
        self.processed_data = []
        self.stats = {
            "total_items": 0,
            "items_with_price": 0,
            "items_with_brand": 0,
            "items_with_model": 0,
            "items_with_category": 0,
            "brands": set(),
            "categories": set(),
            "processed_at": datetime.now().isoformat()
        }
        
        for item in self.raw_data:
            processed_item = self._process_item(item)
            if processed_item:
                self.processed_data.append(processed_item)
                
                # 更新统计信息
                self.stats["total_items"] += 1
                if "price" in processed_item:
                    self.stats["items_with_price"] += 1
                if "brand" in processed_item:
                    self.stats["items_with_brand"] += 1
                    self.stats["brands"].add(processed_item["brand"])
                if "model" in processed_item:
                    self.stats["items_with_model"] += 1
                if "category" in processed_item:
                    self.stats["items_with_category"] += 1
                    self.stats["categories"].add(processed_item["category"])
        
        # 转换集合为列表，以便JSON序列化
        self.stats["brands"] = list(self.stats["brands"])
        self.stats["categories"] = list(self.stats["categories"])
        
        logger.info(f"Processed {len(self.processed_data)} items")
        return self.processed_data
    
    def _process_item(self, item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        处理单个商品数据
        
        Args:
            item: 原始商品数据
            
        Returns:
            处理后的商品数据，如果无效则返回None
        """
        # 创建新的商品数据对象
        processed = {}
        
        # 基本信息处理
        # 品牌处理
        brand = self._extract_brand(item)
        if brand:
            processed["brand"] = brand
        
        # 型号处理
        model = self._extract_model(item)
        if model:
            processed["model"] = model
            
        # 分类处理
        category = self._extract_category(item)
        if category:
            processed["category"] = category
            
        # 价格处理
        price = self._extract_price(item)
        if price:
            processed["price"] = price
            
        # 描述处理
        description = self._extract_description(item)
        if description:
            processed["description"] = description
            
        # 材质处理
        materials = self._extract_materials(item)
        if materials:
            processed["materials"] = materials
            
        # 特性处理
        features = self._extract_features(item)
        if features:
            processed["features"] = features
            
        # 关键词处理
        keywords = self._extract_keywords(item)
        if keywords:
            processed["keywords"] = keywords
            
        # 图片URL处理
        image_url = item.get("image_url") or item.get("image") or item.get("imageUrl")
        if image_url:
            processed["image_url"] = image_url
            
        # 如果处理后的商品至少包含品牌或型号或类别，则认为有效
        if "brand" in processed or "model" in processed or "category" in processed:
            # 添加原始ID（如果有）
            if "id" in item:
                processed["id"] = item["id"]
            # 添加原始URL（如果有）
            if "url" in item:
                processed["url"] = item["url"]
            return processed
        else:
            return None
    
    def _extract_brand(self, item: Dict[str, Any]) -> Optional[str]:
        """提取品牌信息"""
        # 直接从品牌字段提取
        brand = item.get("brand") or item.get("brand_name") or item.get("brandName")
        
        # 如果没有品牌字段，尝试从标题或描述中提取
        if not brand:
            title = item.get("title") or item.get("name") or ""
            desc = item.get("description") or ""
            
            # 常见奢侈品牌列表
            luxury_brands = [
                "Chanel", "Louis Vuitton", "Gucci", "Hermes", "Hermès", "Prada", "Dior", 
                "Balenciaga", "Fendi", "Celine", "Céline", "Burberry", "Valentino",
                "Bottega Veneta", "Saint Laurent", "Yves Saint Laurent", "YSL",
                "Givenchy", "Versace", "Jimmy Choo", "Alexander McQueen",
                "Loewe", "Christian Louboutin", "Miu Miu", "Tiffany", "Cartier",
                "Rolex", "Omega", "Patek Philippe", "Audemars Piguet", "TAG Heuer",
                "Breitling", "Hublot", "IWC", "Jaeger-LeCoultre", "Longines",
                "Montblanc", "Bvlgari", "Bulgari", "Van Cleef & Arpels", "Chopard"
            ]
            
            # 检查标题和描述中是否包含奢侈品牌
            combined_text = f"{title} {desc}".lower()
            for b in luxury_brands:
                if b.lower() in combined_text:
                    brand = b
                    break
        
        if brand and isinstance(brand, str):
            # 标准化品牌名称
            brand = brand.strip()
            
            # 特定品牌的标准化
            brand_map = {
                "lv": "Louis Vuitton",
                "ysl": "Saint Laurent",
                "cdg": "Comme des Garçons",
                "vca": "Van Cleef & Arpels"
            }
            
            return brand_map.get(brand.lower(), brand)
        
        return None
    
    def _extract_model(self, item: Dict[str, Any]) -> Optional[str]:
        """提取型号信息"""
        # 直接从型号字段提取
        model = item.get("model") or item.get("model_name") or item.get("modelName")
        
        # 如果没有型号字段，尝试从标题中提取
        if not model:
            title = item.get("title") or item.get("name") or ""
            
            # 尝试识别常见的型号格式，如：
            # - Chanel Classic Flap
            # - Louis Vuitton Neverfull
            # - Gucci Marmont
            
            if "brand" in item:
                # 移除标题中的品牌名称，剩下的可能是型号
                brand = item["brand"]
                if brand and brand in title:
                    model_candidate = title.replace(brand, "").strip()
                    if model_candidate:
                        model = model_candidate
        
        if model and isinstance(model, str):
            return model.strip()
        
        return None
    
    def _extract_category(self, item: Dict[str, Any]) -> Optional[str]:
        """提取类别信息"""
        # 直接从类别字段提取
        category = item.get("category") or item.get("type") or item.get("item_type")
        
        # 如果没有类别字段，尝试从标题或描述中识别
        if not category:
            title = item.get("title") or item.get("name") or ""
            desc = item.get("description") or ""
            
            # 常见奢侈品类别
            categories = {
                "bag": ["bag", "handbag", "purse", "tote", "clutch", "backpack", "satchel", "crossbody"],
                "wallet": ["wallet", "cardholder", "card case", "purse", "coin purse"],
                "watch": ["watch", "timepiece", "chronograph", "wristwatch"],
                "jewelry": ["jewelry", "jewellery", "necklace", "bracelet", "ring", "earring", "brooch"],
                "shoes": ["shoes", "sneakers", "heels", "boots", "sandals", "loafers", "pumps"],
                "clothing": ["clothing", "dress", "jacket", "coat", "shirt", "blouse", "sweater", "t-shirt", "jeans", "pants", "skirt"],
                "accessory": ["accessory", "scarf", "belt", "sunglasses", "glasses", "hat", "gloves", "keychain"]
            }
            
            combined_text = f"{title} {desc}".lower()
            for cat, keywords in categories.items():
                for kw in keywords:
                    if kw in combined_text:
                        category = cat
                        break
                if category:
                    break
        
        if category and isinstance(category, str):
            # 标准化类别名称
            category = category.strip().lower()
            
            # 将复数形式转换为单数
            if category.endswith('s') and not category.endswith('ss'):
                category = category[:-1]
                
            # 映射类别别名
            category_map = {
                "purse": "bag",
                "handbag": "bag",
                "satchel": "bag",
                "tote": "bag",
                "clutch": "bag",
                "crossbody": "bag",
                "cardholder": "wallet",
                "card case": "wallet",
                "sneaker": "shoes",
                "boot": "shoes",
                "heel": "shoes",
                "loafer": "shoes",
                "sandal": "shoes",
                "pump": "shoes",
                "necklace": "jewelry",
                "bracelet": "jewelry",
                "ring": "jewelry",
                "earring": "jewelry",
                "brooch": "jewelry",
                "dress": "clothing",
                "jacket": "clothing",
                "coat": "clothing",
                "shirt": "clothing",
                "blouse": "clothing",
                "sweater": "clothing",
                "t-shirt": "clothing",
                "jeans": "clothing",
                "pant": "clothing",
                "skirt": "clothing",
                "scarf": "accessory",
                "belt": "accessory",
                "sunglasses": "accessory",
                "glasses": "accessory",
                "hat": "accessory",
                "gloves": "accessory",
                "keychain": "accessory"
            }
            
            return category_map.get(category, category)
        
        return None
    
    def _extract_price(self, item: Dict[str, Any]) -> Optional[Union[float, str]]:
        """提取价格信息"""
        # 直接从价格字段提取
        price = item.get("price") or item.get("current_price") or item.get("currentPrice")
        
        if not price:
            return None
            
        if isinstance(price, (int, float)):
            return price
            
        if isinstance(price, str):
            # 尝试提取数字
            try:
                # 去除货币符号和逗号等
                price_clean = re.sub(r'[^\d.]', '', price)
                return float(price_clean)
            except:
                # 如果无法转换为浮点数，返回原始字符串
                return price.strip()
        
        return None
    
    def _extract_description(self, item: Dict[str, Any]) -> Optional[str]:
        """提取描述信息"""
        description = item.get("description") or item.get("desc") or item.get("details")
        
        if not description:
            # 尝试使用标题作为描述
            description = item.get("title") or item.get("name")
            
        if description and isinstance(description, str):
            return description.strip()
            
        return None
    
    def _extract_materials(self, item: Dict[str, Any]) -> Optional[Union[str, List[str]]]:
        """提取材质信息"""
        materials = item.get("materials") or item.get("material")
        
        if not materials:
            # 尝试从描述中提取材质信息
            desc = item.get("description") or ""
            
            # 常见奢侈品材质
            common_materials = [
                "leather", "calfskin", "lambskin", "caviar", "patent leather",
                "canvas", "denim", "silk", "cotton", "wool", "cashmere",
                "gold", "silver", "platinum", "diamond", "ruby", "sapphire",
                "stainless steel", "titanium", "ceramic", "rose gold", "white gold",
                "tweed", "nylon", "suede", "satin", "velvet", "python", "crocodile", "alligator"
            ]
            
            found_materials = []
            for material in common_materials:
                if material.lower() in desc.lower():
                    found_materials.append(material)
                    
            if found_materials:
                materials = found_materials
        
        if isinstance(materials, list):
            return [m.strip() for m in materials if m and isinstance(m, str)]
        elif materials and isinstance(materials, str):
            return materials.strip()
            
        return None
    
    def _extract_features(self, item: Dict[str, Any]) -> Optional[Union[str, List[str]]]:
        """提取特性信息"""
        features = item.get("features") or item.get("specifications") or item.get("specs")
        
        if features and isinstance(features, list):
            return [f.strip() for f in features if f and isinstance(f, str)]
        elif features and isinstance(features, str):
            return features.strip()
            
        return None
    
    def _extract_keywords(self, item: Dict[str, Any]) -> Optional[List[str]]:
        """提取关键词"""
        keywords = item.get("keywords") or item.get("tags")
        
        if not keywords:
            # 生成基于已有信息的关键词
            generated_keywords = []
            
            # 添加品牌作为关键词
            if "brand" in item and item["brand"]:
                generated_keywords.append(item["brand"])
                
            # 添加类别作为关键词
            if "category" in item and item["category"]:
                generated_keywords.append(item["category"])
                
            # 添加材质作为关键词
            materials = item.get("materials")
            if materials:
                if isinstance(materials, list):
                    generated_keywords.extend(materials)
                elif isinstance(materials, str):
                    generated_keywords.append(materials)
                    
            if generated_keywords:
                keywords = generated_keywords
        
        if isinstance(keywords, list):
            return [k.strip() for k in keywords if k and isinstance(k, str)]
            
        return None
    
    def save_processed_data(self, output_path: str) -> bool:
        """
        保存处理后的数据到JSON文件
        
        Args:
            output_path: 输出文件路径
            
        Returns:
            是否保存成功
        """
        if not self.processed_data:
            logger.warning("No processed data to save")
            return False
            
        try:
            # 确保输出目录存在
            output_dir = os.path.dirname(output_path)
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)
                
            # 保存数据
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(self.processed_data, f, ensure_ascii=False, indent=2)
                
            logger.info(f"Saved {len(self.processed_data)} processed items to {output_path}")
            
            # 保存统计信息
            stats_path = os.path.splitext(output_path)[0] + "_stats.json"
            with open(stats_path, "w", encoding="utf-8") as f:
                json.dump(self.stats, f, ensure_ascii=False, indent=2)
                
            logger.info(f"Saved processing statistics to {stats_path}")
            return True
        except Exception as e:
            logger.error(f"Error saving processed data: {e}")
            return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取数据处理统计信息
        
        Returns:
            统计信息字典
        """
        return self.stats 