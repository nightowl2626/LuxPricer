import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

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
    timestamps?: any;
    raw_responses?: any;
  };
}

@Injectable({
  providedIn: 'root'
})
export class AppraisalService {
  private apiUrl = environment.apiUrl;

  constructor(private http: HttpClient) { }

  /**
   * 发送奢侈品鉴定请求
   * @param formData 包含查询和可选图像的FormData对象
   * @returns 鉴定响应的Observable
   */
  sendAppraisalRequest(formData: FormData): Observable<AppraisalResponse> {
    // 确定是否包含图像
    const hasImage = formData.has('image');
    const endpoint = hasImage ? 'agent/appraise/image' : 'agent/appraise';
    
    // 使用URL构建，避免双斜杠问题
    const url = new URL(endpoint, this.apiUrl).toString();
    
    // 如果没有图片，使用JSON格式；有图片，继续使用FormData
    if (!hasImage) {
      const query = formData.get('query') as string;
      return this.http.post<AppraisalResponse>(url, { query });
    } else {
      return this.http.post<AppraisalResponse>(url, formData);
    }
  }

  /**
   * 获取特定品牌或型号的价格趋势
   * @param brand 品牌名称
   * @param model 可选的型号名称
   * @returns 价格趋势数据的Observable
   */
  getPriceTrends(brand: string, model?: string): Observable<any> {
    let params: any = { brand };
    if (model) {
      params.model = model;
    }
    
    const url = new URL('trends/price', this.apiUrl).toString();
    return this.http.get<any>(url, { params });
  }

  /**
   * 获取特定品牌的市场分析
   * @param brand 品牌名称
   * @returns 市场分析数据的Observable
   */
  getMarketAnalysis(brand: string): Observable<any> {
    const url = new URL(`trends/market/${brand}`, this.apiUrl).toString();
    return this.http.get<any>(url);
  }
} 