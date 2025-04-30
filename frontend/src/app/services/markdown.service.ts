import { Injectable } from '@angular/core';
import { marked } from 'marked';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';

@Injectable({
  providedIn: 'root'
})
export class MarkdownService {
  constructor(private sanitizer: DomSanitizer) {
    // Set default options for marked
    marked.setOptions({
      breaks: true,        // Add 'br' on single line breaks
      gfm: true            // GitHub Flavored Markdown
    });
  }

  /**
   * Parse markdown string to HTML and sanitize the output
   */
  parse(markdown: string): SafeHtml {
    if (!markdown) {
      return '';
    }
    
    try {
      // Convert markdown to HTML
      const html = marked.parse(markdown);
      
      // Sanitize the HTML to prevent XSS attacks
      return this.sanitizer.bypassSecurityTrustHtml(html as string);
    } catch (error) {
      console.error('Error parsing markdown:', error);
      return this.sanitizer.bypassSecurityTrustHtml(`<p>Error parsing content: ${error}</p>`);
    }
  }
} 