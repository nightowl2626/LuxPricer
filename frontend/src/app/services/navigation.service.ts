import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class NavigationService {
  // 使用BehaviorSubject存储欢迎页面的状态
  private welcomeActiveSubject = new BehaviorSubject<boolean>(true);
  
  // 公开的Observable用于组件订阅
  public welcomeActive$: Observable<boolean> = this.welcomeActiveSubject.asObservable();
  
  constructor() {}
  
  // 获取当前欢迎页面状态
  get isWelcomeActive(): boolean {
    return this.welcomeActiveSubject.value;
  }
  
  // 设置欢迎页面状态
  setWelcomeActive(active: boolean): void {
    this.welcomeActiveSubject.next(active);
  }
  
  // 返回首页/欢迎页面
  goToHome(): void {
    this.setWelcomeActive(true);
  }
  
  // 前往聊天页面
  goToChat(): void {
    this.setWelcomeActive(false);
  }
} 