import { Component, ViewChild, ElementRef, AfterViewChecked } from '@angular/core';
import { AppraisalService, AppraisalResponse } from '../services/appraisal.service';
import { MarkdownService } from '../services/markdown.service';
import { PdfService } from '../services/pdf.service';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';
import { NavigationService } from '../services/navigation.service';

interface ChatMessage {
  content: string;
  type: 'user' | 'assistant';
  isMarkdown?: boolean;
  isLoading?: boolean;
  timestamp?: Date;
  details?: {
    extracted_details?: any;
    tool_calls?: any[];
    tool_results?: any;
  };
}

@Component({
  selector: 'app-chat',
  templateUrl: './chat.component.html',
  styleUrls: ['./chat.component.scss']
})
export class ChatComponent implements AfterViewChecked {
  @ViewChild('messagesContainer') private messagesContainer!: ElementRef;

  welcomeActive = true;
  userQuery = '';
  messages: ChatMessage[] = [];
  isProcessing = false;
  selectedFile: File | null = null;
  selectedFilePreview: string | null = null;
  currentResponseDetails: any = null;
  isExportingPdf = false;

  constructor(
    private appraisalService: AppraisalService,
    private markdownService: MarkdownService,
    private pdfService: PdfService,
    private navigationService: NavigationService,
    private sanitizer: DomSanitizer
  ) {
    this.navigationService.welcomeActive$.subscribe(active => {
      this.welcomeActive = active;
    });
    
    // 订阅PDF生成状态
    this.pdfService.isGenerating$.subscribe(isGenerating => {
      this.isExportingPdf = isGenerating;
    });
  }

  ngAfterViewChecked() {
    this.scrollToBottom();
  }

  scrollToBottom(): void {
    try {
      this.messagesContainer.nativeElement.scrollTop = this.messagesContainer.nativeElement.scrollHeight;
    } catch (err) {}
  }

  handleUserInput() {
    if (!this.userQuery.trim() && !this.selectedFile) return;

    if (this.welcomeActive) {
      this.navigationService.goToChat();
    }

    // Add user message
    this.messages.push({
      content: this.selectedFile 
        ? `${this.userQuery} [Image uploaded: ${this.selectedFile.name}]` 
        : this.userQuery,
      type: 'user',
      timestamp: new Date()
    });

    // Add loading message
    const loadingMsgIndex = this.messages.length;
    this.messages.push({
      content: 'Analyzing your query, please wait...',
      type: 'assistant',
      isLoading: true,
      timestamp: new Date()
    });

    // Prepare request data
    const formData = new FormData();
    formData.append('query', this.userQuery);
    if (this.selectedFile) {
      formData.append('image', this.selectedFile);
    }

    this.isProcessing = true;

    // Send appraisal request
    this.appraisalService.sendAppraisalRequest(formData).subscribe({
      next: (response: AppraisalResponse) => {
        // Replace loading message
        this.messages[loadingMsgIndex] = {
          content: response.report,
          type: 'assistant',
          isMarkdown: true,
          timestamp: new Date(),
          details: {
            extracted_details: response.debug_info?.planner_output?.extracted_details,
            tool_calls: response.debug_info?.planner_output?.tool_calls,
            tool_results: response.debug_info?.tool_results
          }
        };
        
        // Reset state
        this.isProcessing = false;
      },
      error: (error) => {
        console.error('Appraisal request failed', error);
        // Replace loading message with error
        this.messages[loadingMsgIndex] = {
          content: 'Sorry, an error occurred during the appraisal. Please try again later or contact support.',
          type: 'assistant',
          timestamp: new Date()
        };
        this.isProcessing = false;
      }
    });

    // Reset input
    this.userQuery = '';
    this.selectedFile = null;
    this.selectedFilePreview = null;
  }

  handleFileSelect(event: any) {
    const files = event.target.files;
    if (files.length > 0) {
      this.selectedFile = files[0];
      
      // Generate image preview
      const reader = new FileReader();
      reader.onload = (e: any) => {
        this.selectedFilePreview = e.target.result;
      };
      if (this.selectedFile) {
        reader.readAsDataURL(this.selectedFile);
      }
    }
  }

  removeSelectedFile() {
    this.selectedFile = null;
    this.selectedFilePreview = null;
  }

  showDetails(details: any) {
    this.currentResponseDetails = details;
    // Modal functionality will be handled using a different approach
    console.log('Showing details:', details);
  }

  parseMarkdown(markdown: string): SafeHtml {
    return this.markdownService.parse(markdown);
  }
  
  /**
   * Export report as PDF
   * @param content Report content (Markdown format)
   */
  async exportToPdf(content: string): Promise<void> {
    if (!content || this.isExportingPdf) return;
    
    try {
      // Extract title from content (assuming title is the first line starting with #)
      const titleMatch = content.match(/^#\s+(.+)$/m);
      const title = titleMatch ? titleMatch[1] : 'Luxury Item Appraisal Report';
      
      await this.pdfService.exportReportToPdf(content, title);
    } catch (error) {
      console.error('Error exporting to PDF:', error);
      // Error handling is now done inside the PdfService
    }
  }

  /**
   * Start chat, enter chat interface
   */
  startChat(): void {
    this.navigationService.goToChat();
  }
} 