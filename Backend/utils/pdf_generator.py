"""
PDF Generator for Luxury Appraisal Reports

This module converts markdown appraisal reports to professionally formatted PDF documents.
"""

import os
import re
import logging
import datetime
import tempfile
import io
from typing import Dict, Any, Optional, Union

# 使用reportlab代替weasyprint
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib.units import inch

# 使用markdown库解析markdown内容
import markdown
from bs4 import BeautifulSoup

# Configure logging
logger = logging.getLogger(__name__)

class AppraisalPDFGenerator:
    """
    Generates professionally formatted PDF documents from markdown appraisal reports.
    Includes styling, branding, and layout optimizations for luxury item reports.
    """
    
    def __init__(self):
        """
        Initialize PDF generator with styling and branding options.
        """
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
        
    def _setup_custom_styles(self):
        """
        Set up custom styles for the PDF.
        """
        # 添加标题样式
        self.styles.add(ParagraphStyle(
            name='Title',
            parent=self.styles['Heading1'],
            fontSize=18,
            alignment=1,  # 居中对齐
            spaceAfter=12
        ))
        
        # 添加小标题样式
        self.styles.add(ParagraphStyle(
            name='Heading2',
            parent=self.styles['Heading2'],
            fontSize=14,
            spaceBefore=10,
            spaceAfter=8
        ))
        
        # 添加正文样式
        self.styles.add(ParagraphStyle(
            name='BodyText',
            parent=self.styles['Normal'],
            fontSize=10,
            spaceBefore=6,
            spaceAfter=6
        ))
    
    def _markdown_to_html(self, markdown_text: str) -> str:
        """
        Convert markdown text to HTML.
        
        Args:
            markdown_text: Markdown text to convert
            
        Returns:
            Converted HTML content
        """
        return markdown.markdown(markdown_text, extensions=['tables', 'fenced_code'])
    
    def _html_to_elements(self, html_content: str) -> list:
        """
        Convert HTML content to a list of ReportLab elements.
        
        Args:
            html_content: HTML content to convert
            
        Returns:
            List of ReportLab elements
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        elements = []
        
        # 添加标志和标题
        logo_path = os.path.join(os.path.dirname(__file__), '..', 'static', 'logo.png')
        if os.path.exists(logo_path):
            img = Image(logo_path, width=1.5*inch, height=1.5*inch)
            elements.append(img)
        
        # 处理标题和内容
        for tag in soup.find_all(['h1', 'h2', 'h3', 'p', 'ul', 'ol', 'table']):
            if tag.name == 'h1':
                elements.append(Paragraph(tag.text, self.styles['Title']))
                elements.append(Spacer(1, 12))
            elif tag.name == 'h2':
                elements.append(Paragraph(tag.text, self.styles['Heading2']))
                elements.append(Spacer(1, 8))
            elif tag.name == 'h3':
                elements.append(Paragraph(tag.text, self.styles['Heading3']))
                elements.append(Spacer(1, 6))
            elif tag.name == 'p':
                elements.append(Paragraph(tag.text, self.styles['BodyText']))
                elements.append(Spacer(1, 6))
            elif tag.name in ['ul', 'ol']:
                for li in tag.find_all('li'):
                    bullet = "• " if tag.name == 'ul' else f"{tag.find_all('li').index(li) + 1}. "
                    elements.append(Paragraph(f"{bullet}{li.text}", self.styles['BodyText']))
                elements.append(Spacer(1, 6))
            elif tag.name == 'table':
                # 简单表格处理
                table_data = []
                # 表头
                if tag.find('thead'):
                    header_row = []
                    for th in tag.find('thead').find_all('th'):
                        header_row.append(th.text)
                    table_data.append(header_row)
                
                # 表体
                for tr in tag.find_all('tr'):
                    if tr.parent.name != 'thead':  # 排除表头行
                        row = []
                        for td in tr.find_all('td'):
                            row.append(td.text)
                        if row:  # 确保行不为空
                            table_data.append(row)
                
                if table_data:
                    # 创建表格
                    table = Table(table_data)
                    table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                        ('GRID', (0, 0), (-1, -1), 1, colors.black)
                    ]))
                    elements.append(table)
                    elements.append(Spacer(1, 12))
                
        return elements
    
    def generate_pdf(self, markdown_content: str, output_path: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Generate PDF from markdown content.
        
        Args:
            markdown_content: Markdown content to convert
            output_path: Path to save the PDF
            metadata: Additional metadata for the report
            
        Returns:
            Path to saved PDF
        """
        try:
            # 默认元数据
            if metadata is None:
                metadata = {
                    'title': '奢侈品估值报告',
                    'author': 'Luxury Expert System',
                    'subject': '奢侈品估值',
                    'keywords': '奢侈品,估值,报告'
                }
            
            # 转换Markdown为HTML
            html_content = self._markdown_to_html(markdown_content)
            
            # 转换HTML为ReportLab元素
            elements = self._html_to_elements(html_content)
            
            # 创建PDF文档
            doc = SimpleDocTemplate(
                output_path,
                pagesize=A4,
                title=metadata.get('title', '奢侈品估值报告'),
                author=metadata.get('author', 'Luxury Expert System'),
                subject=metadata.get('subject', '奢侈品估值'),
                keywords=metadata.get('keywords', '奢侈品,估值,报告')
            )
            
            # 构建PDF
            doc.build(elements)
            
            logger.info(f"PDF report generated successfully at {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Error generating PDF: {str(e)}")
            raise

# Convenience function to generate PDF from markdown content
def generate_appraisal_pdf(content: str, output_path: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> Union[str, bytes]:
    """
    Generate a luxury appraisal PDF from markdown content.
    
    Args:
        content: Markdown content to convert
        output_path: Path to save the PDF. If None, returns bytes instead of file path.
        metadata: Additional metadata for the report
        
    Returns:
        Path to saved PDF (if output_path is provided) or PDF content as bytes (if output_path is None)
    """
    if output_path is None:
        return generate_appraisal_pdf_to_bytes(content, metadata)
    
    generator = AppraisalPDFGenerator()
    return generator.generate_pdf(content, output_path, metadata)

# Function to generate PDF to memory buffer instead of file
def generate_appraisal_pdf_to_bytes(content: str, metadata: Optional[Dict[str, Any]] = None) -> bytes:
    """
    Generate a luxury appraisal PDF from markdown content and return as bytes.
    
    Args:
        content: Markdown content to convert
        metadata: Additional metadata for the report
        
    Returns:
        PDF content as bytes
    """
    try:
        # 创建一个临时的内存缓冲区
        buffer = io.BytesIO()
        
        # 默认元数据
        if metadata is None:
            metadata = {
                'title': '奢侈品估值报告',
                'author': 'Luxury Expert System',
                'subject': '奢侈品估值',
                'keywords': '奢侈品,估值,报告'
            }
        
        # 初始化生成器
        generator = AppraisalPDFGenerator()
        
        # 转换Markdown为HTML
        html_content = generator._markdown_to_html(content)
        
        # 转换HTML为ReportLab元素
        elements = generator._html_to_elements(html_content)
        
        # 创建PDF文档
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            title=metadata.get('title', '奢侈品估值报告'),
            author=metadata.get('author', 'Luxury Expert System'),
            subject=metadata.get('subject', '奢侈品估值'),
            keywords=metadata.get('keywords', '奢侈品,估值,报告')
        )
        
        # 构建PDF
        doc.build(elements)
        
        # 获取缓冲区内容
        pdf_bytes = buffer.getvalue()
        buffer.close()
        
        logger.info(f"PDF report generated successfully in memory ({len(pdf_bytes)} bytes)")
        return pdf_bytes
            
    except Exception as e:
        logger.error(f"Error generating PDF in memory: {str(e)}")
        raise

# Convenience function to generate PDF from a markdown file
def generate_appraisal_pdf_from_file(markdown_file: str, output_path: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> str:
    """
    Generate a luxury appraisal PDF from a markdown file.
    
    Args:
        markdown_file: Path to markdown file
        output_path: Optional path to save the PDF
        metadata: Additional metadata for the report
        
    Returns:
        Path to saved PDF
    """
    try:
        # 读取Markdown文件
        with open(markdown_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # 如果未指定输出路径，则使用输入文件名+.pdf
        if output_path is None:
            output_path = os.path.splitext(markdown_file)[0] + '.pdf'
            
        # 生成PDF
        return generate_appraisal_pdf(content, output_path, metadata)
        
    except Exception as e:
        logger.error(f"Error generating PDF from file {markdown_file}: {str(e)}")
        raise

def sanitize_filename(filename: str) -> str:
    """
    Clean up filename by removing unsafe characters and limiting length.
    
    Args:
        filename: Input filename
        
    Returns:
        Cleaned filename
    """
    # Remove unsafe characters
    sanitized = re.sub(r'[\\/*?:"<>|]', "", filename)
    # Replace spaces with underscores
    sanitized = sanitized.replace(" ", "_")
    # Limit length
    if len(sanitized) > 50:
        sanitized = sanitized[:50]
    return sanitized 