import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

export interface AppraisalRequest {
  query: string;
}

export interface AppraisalResponse {
  report: string;
  debug_info: {
    planner_output: {
      extracted_details: any;
      tool_calls: Array<{
        tool_name: string;
        parameters: any;
      }>;
    };
    tool_results: Record<string, any>;
  };
}

@Injectable({
  providedIn: 'root'
})
export class ApiService {
  // Base API URL - in a real app, this would come from environment config
  private apiUrl = environment.apiUrl;

  constructor(private http: HttpClient) { }

  /**
   * Send appraisal request to the API
   * @param query The user's query text
   * @returns Observable of the API response
   */
  appraise(query: string): Observable<AppraisalResponse> {
    const request: AppraisalRequest = { query };
    return this.http.post<AppraisalResponse>(`${this.apiUrl}/agent/appraise`, request);
  }
  
  /**
   * Send appraisal request with image to the API
   * @param query The user's query text
   * @param image The image file to upload
   * @returns Observable of the API response
   */
  appraiseWithImage(query: string, image: File): Observable<AppraisalResponse> {
    // Create FormData to send multipart/form-data request
    const formData = new FormData();
    formData.append('query', query);
    formData.append('image', image);
    
    return this.http.post<AppraisalResponse>(`${this.apiUrl}/agent/appraise/image`, formData);
  }
} 