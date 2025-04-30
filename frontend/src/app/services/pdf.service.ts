import { Injectable } from '@angular/core';
import { MarkdownService } from './markdown.service';
import { HttpClient, HttpErrorResponse, HttpHeaders } from '@angular/common/http';
import { environment } from '../../environments/environment';
import jsPDF from 'jspdf';
import html2canvas from 'html2canvas';
import { BehaviorSubject } from 'rxjs';
import { firstValueFrom } from 'rxjs';

// Define response type interface
interface BlobHttpResponse {
  body: Blob;
  headers: HttpHeaders;
  status: number;
  statusText: string;
  url: string;
  type: number;
  ok: boolean;
}

@Injectable({
  providedIn: 'root'
})
export class PdfService {
  private apiUrl = environment.apiUrl;
  private _isGenerating = new BehaviorSubject<boolean>(false);
  
  // Public observable for loading state
  public isGenerating$ = this._isGenerating.asObservable();

  constructor(
    private markdownService: MarkdownService,
    private http: HttpClient
  ) {}
  
  /**
   * Export report as PDF - calls the backend API to generate a high-quality PDF
   * @param reportContent Markdown report content
   * @param title PDF file title
   */
  async exportReportToPdf(reportContent: string, title: string = 'Luxury Item Appraisal Report'): Promise<void> {
    try {
      this._isGenerating.next(true);
      
      // First attempt to use the backend API to generate a high-quality PDF
      await this.exportReportToPdfUsingApi(reportContent, title);
    } catch (error) {
      // Log detailed error information for diagnostics
      if (error instanceof HttpErrorResponse) {
        console.warn(`Failed to generate PDF using backend API (${error.status}): ${error.message}`, error);
      } else {
        console.warn('Failed to generate PDF using backend API:', error);
      }
      
      try {
        // If the backend API call fails, fall back to local PDF generation
        console.log('Falling back to local PDF generation...');
        await this.exportReportToPdfLocally(reportContent, title);
      } catch (localError) {
        console.error('Local PDF generation also failed:', localError);
        // Show user-friendly error message
        this.showErrorToast('PDF generation failed. Please try again later or contact support.');
        throw localError;
      }
    } finally {
      this._isGenerating.next(false);
    }
  }
  
  /**
   * Use the backend API to generate high-quality PDF
   * @param reportContent Markdown report content
   * @param title PDF file title
   */
  private async exportReportToPdfUsingApi(reportContent: string, title: string): Promise<void> {
    // Build API endpoint URL - 修复URL构建
    const endpoint = 'agent/appraise/pdf';
    const url = `${this.apiUrl}/${endpoint}`.replace(/([^:]\/)\/+/g, '$1'); // 确保没有多余的斜杠
    
    // 记录请求URL便于调试
    console.log(`Sending PDF request to: ${url}`);
    
    // Prepare API request data
    const requestData = {
      query: title, // Use title as query parameter
      report_content: reportContent // Pass report content
    };
    
    // Show loading hint
    this.showInfoToast('Generating PDF, please wait...');
    
    // Set timeout control
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 30000); // 30 second timeout
    
    try {
      // Use native fetch API instead of HttpClient to avoid type issues
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/pdf'
        },
        body: JSON.stringify(requestData),
        signal: controller.signal
      });
      
      // 记录响应状态
      console.log(`PDF API response status: ${response.status}`);
      
      if (!response.ok) {
        // 尝试获取错误详情
        let errorDetails = '';
        try {
          const errorResponse = await response.json();
          errorDetails = JSON.stringify(errorResponse);
        } catch (e) {
          errorDetails = await response.text();
        }
        throw new Error(`HTTP error! status: ${response.status}, details: ${errorDetails}`);
      }
      
      // 确认响应类型
      const contentType = response.headers.get('Content-Type');
      console.log(`Response Content-Type: ${contentType}`);
      
      if (!contentType || !contentType.includes('application/pdf')) {
        console.warn(`Unexpected content type: ${contentType}, proceeding anyway...`);
      }
      
      // Get PDF blob from response
      const pdfBlob = await response.blob();
      
      // Create filename, use let instead of const to allow reassignment
      const now = new Date();
      let fileName = `${title.replace(/\s+/g, '_')}_${now.toISOString().split('T')[0]}.pdf`;
      
      // Get filename from Content-Disposition header if available
      const contentDisposition = response.headers.get('Content-Disposition');
      if (contentDisposition) {
        const fileNameMatch = contentDisposition.match(/filename="?([^"]+)"?/);
        if (fileNameMatch && fileNameMatch[1]) {
          fileName = fileNameMatch[1];
        }
      }
      
      // Trigger file download
      this.downloadBlob(pdfBlob, fileName);
      this.showSuccessToast('PDF generated successfully!');
    } catch (error) {
      console.error('Failed to fetch PDF:', error);
      throw error;
    } finally {
      clearTimeout(timeoutId);
    }
  }
  
  /**
   * Generate PDF locally in the browser (fallback method)
   * @param reportContent Markdown report content
   * @param title PDF file title
   */
  private async exportReportToPdfLocally(reportContent: string, title: string): Promise<void> {
    this.showInfoToast('Generating PDF locally, this may take a moment...');
    
    try {
      // Create a temporary div element to render markdown content
      const tempDiv = document.createElement('div');
      tempDiv.className = 'pdf-content';
      tempDiv.style.width = '800px'; // Fixed width for consistent rendering
      tempDiv.style.padding = '40px';
      tempDiv.style.position = 'absolute';
      tempDiv.style.left = '-9999px';
      tempDiv.style.background = 'white';
      tempDiv.style.fontFamily = 'Arial, Helvetica, sans-serif';
      
      // Parse and render markdown content
      tempDiv.innerHTML = this.markdownService.parse(reportContent).toString();
      
      // Apply basic styling directly to elements
      const style = document.createElement('style');
      style.textContent = `
        .pdf-content h1 {
          font-size: 24px;
          color: #4F3E9C;
          padding-bottom: 10px;
          margin-bottom: 20px;
          border-bottom: 1px solid #ddd;
        }
        .pdf-content h2 {
          font-size: 18px;
          color: #9B573B;
          margin-top: 20px;
          margin-bottom: 10px;
        }
        .pdf-content p, .pdf-content li {
          font-size: 12px;
          line-height: 1.5;
          margin-bottom: 8px;
        }
        .pdf-content ul, .pdf-content ol {
          padding-left: 20px;
          margin-bottom: 15px;
        }
      `;
      document.head.appendChild(style);
      
      // Add to document for rendering
      document.body.appendChild(tempDiv);
      
      // Create PDF
      const pdf = new jsPDF({
        orientation: 'portrait',
        unit: 'mm',
        format: 'a4'
      });
      
      // Add header information
      pdf.setFontSize(14);
      pdf.setTextColor(79, 62, 156); // Purple
      pdf.text('LuxPricer Appraisal Report', 20, 15);
      
      // Add title
      pdf.setFontSize(12);
      pdf.setTextColor(0, 0, 0);
      pdf.text(`${title}`, 20, 25);
      
      // Add horizontal line
      pdf.setDrawColor(200, 200, 200);
      pdf.line(20, 30, 190, 30);
      
      // Use a div-to-PDF conversion that works directly, without creating an image first
      // This prevents the skewing/rotation issues
      
      // Create the raw content string
      let rawContent = '';
      
      // Add each heading and text paragraph from the content
      const headings = tempDiv.querySelectorAll('h1, h2, h3, h4, h5, h6');
      const paragraphs = tempDiv.querySelectorAll('p');
      const lists = tempDiv.querySelectorAll('ul, ol');
      
      headings.forEach(heading => {
        rawContent += heading.textContent + '\n\n';
      });
      
      paragraphs.forEach(paragraph => {
        rawContent += paragraph.textContent + '\n\n';
      });
      
      lists.forEach(list => {
        const items = list.querySelectorAll('li');
        items.forEach(item => {
          rawContent += '• ' + item.textContent + '\n';
        });
        rawContent += '\n';
      });
      
      // Split the text into pages
      const textLines = pdf.splitTextToSize(rawContent, 170); // Width with margins
      const linesPerPage = 60; // Approximate number of lines per page
      
      // Add text to PDF, creating new pages as needed
      let curPage = 1;
      
      for (let i = 0; i < textLines.length; i += linesPerPage) {
        if (i > 0) {
          pdf.addPage(); // Add a new page
          curPage++;
          
          // Add header to new page
          pdf.setFontSize(10);
          pdf.setTextColor(100, 100, 100);
          pdf.text('LuxPricer Appraisal Report', 20, 15);
          pdf.text(`Page ${curPage}`, 180, 15);
          pdf.line(20, 20, 190, 20);
        }
        
        // Add content for this page
        const pageLines = textLines.slice(i, i + linesPerPage);
        pdf.setFontSize(10);
        pdf.setTextColor(0, 0, 0);
        pdf.text(pageLines, 20, 40);
        
        // Add footer
        pdf.setFontSize(8);
        pdf.setTextColor(150, 150, 150);
        pdf.text(`© LuxPricer - Professional Luxury Item Appraisal`, 20, 285);
        pdf.text(`Page ${curPage}`, 180, 285);
      }
      
      // Clean up
      document.head.removeChild(style);
      document.body.removeChild(tempDiv);
      
      // Save the PDF
      const fileName = `${title.replace(/\s+/g, '_')}_${new Date().toISOString().split('T')[0]}.pdf`;
      pdf.save(fileName);
      this.showSuccessToast('PDF generated successfully!');
    } catch (error) {
      console.error('Error generating PDF locally:', error);
      this.showErrorToast('Local PDF generation failed, please try again later.');
      throw error;
    }
  }
  
  /**
   * Strip HTML tags from content
   */
  private stripHtml(html: string): string {
    const tmp = document.createElement('DIV');
    tmp.innerHTML = html;
    return tmp.textContent || tmp.innerText || '';
  }
  
  /**
   * Parse content into sections based on markdown headers
   */
  private parseContentSections(content: string): {title: string, content: string}[] {
    const lines = content.split('\n');
    const sections: {title: string, content: string}[] = [];
    
    let currentTitle = '';
    let currentContent: string[] = [];
    
    for (const line of lines) {
      // Check if line is a header (starts with # or ##)
      if (line.match(/^#{1,2}\s+/)) {
        // If we've been building a section, save it
        if (currentTitle && currentContent.length > 0) {
          sections.push({
            title: currentTitle,
            content: currentContent.join('\n')
          });
        }
        
        // Start a new section
        currentTitle = line.replace(/^#{1,2}\s+/, '');
        currentContent = [];
      } else if (line.trim() !== '') {
        // Add non-empty content lines to current section
        currentContent.push(line);
      }
    }
    
    // Add the last section
    if (currentTitle && currentContent.length > 0) {
      sections.push({
        title: currentTitle,
        content: currentContent.join('\n')
      });
    }
    
    return sections;
  }
  
  /**
   * Download Blob data as file
   */
  private downloadBlob(blob: Blob, fileName: string): void {
    // Create URL object
    const url = window.URL.createObjectURL(blob);
    
    // Create download link
    const a = document.createElement('a');
    a.href = url;
    a.download = fileName;
    a.style.display = 'none';
    
    // Add to document and trigger click
    document.body.appendChild(a);
    a.click();
    
    // Clean up
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
  }
  
  /**
   * Show success toast
   */
  private showSuccessToast(message: string): void {
    // Can use app's Toast component here
    // If none exists, use simple alert
    console.log('Success:', message);
    // Can be replaced with better UI notification
    this.showToast(message, 'success');
  }
  
  /**
   * Show error toast
   */
  private showErrorToast(message: string): void {
    console.error('Error:', message);
    this.showToast(message, 'error');
  }
  
  /**
   * Show info toast
   */
  private showInfoToast(message: string): void {
    console.info('Info:', message);
    this.showToast(message, 'info');
  }
  
  /**
   * Show Toast message
   * Simple implementation, can be replaced with more sophisticated UI component
   */
  private showToast(message: string, type: 'success' | 'error' | 'info'): void {
    // Check if toast element already exists
    let toast = document.getElementById('pdf-toast');
    if (!toast) {
      toast = document.createElement('div');
      toast.id = 'pdf-toast';
      toast.style.position = 'fixed';
      toast.style.bottom = '20px';
      toast.style.right = '20px';
      toast.style.padding = '12px 20px';
      toast.style.borderRadius = '4px';
      toast.style.zIndex = '9999';
      toast.style.minWidth = '250px';
      toast.style.boxShadow = '0 4px 12px rgba(0,0,0,0.15)';
      toast.style.transition = 'opacity 0.3s ease';
      toast.style.fontSize = '14px';
      document.body.appendChild(toast);
    }
    
    // Set style and text
    switch (type) {
      case 'success':
        toast.style.backgroundColor = '#4caf50';
        toast.style.color = 'white';
        break;
      case 'error':
        toast.style.backgroundColor = '#f44336';
        toast.style.color = 'white';
        break;
      case 'info':
        toast.style.backgroundColor = '#2196f3';
        toast.style.color = 'white';
        break;
    }
    
    toast.textContent = message;
    toast.style.opacity = '1';
    
    // Hide after 3 seconds
    setTimeout(() => {
      // Fix potential null reference
      const toastElement = document.getElementById('pdf-toast');
      if (toastElement) {
        toastElement.style.opacity = '0';
        setTimeout(() => {
          // Check again if element exists
          const toastToRemove = document.getElementById('pdf-toast');
          if (toastToRemove && document.body.contains(toastToRemove)) {
            document.body.removeChild(toastToRemove);
          }
        }, 300);
      }
    }, 3000);
  }
} 