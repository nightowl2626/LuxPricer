import { Component } from '@angular/core';
import { NavigationService } from './services/navigation.service';

@Component({
  selector: 'app-root',
  template: `
    <div class="app-container">
      <header>
        <div class="header-content">
          <div class="logo" (click)="goToHome()" [class.clickable]="!isWelcomeActive">
            <img src="assets/lplogo.svg" alt="LuxPricer" class="logo-img">
            <h1 class="brand-gradient-text">LuxPricer</h1>
          </div>
        </div>
      </header>
      
      <main>
        <app-chat></app-chat>
      </main>
      
      <footer>
        <p>© 2025 LuxPricer - Luxury Item Price Estimation System</p>
      </footer>
    </div>
  `,
  styles: [`
    @use '../styles/variables' as v;
    
    .app-container {
      display: flex;
      flex-direction: column;
      min-height: 100vh;
      background-color: #f9f9f9;
    }
    
    header {
      background-color: #ffffff;
      padding: 16px 0;
      box-shadow: 0 2px 12px rgba(0, 0, 0, 0.05);
      border-bottom: 1px solid v.$color-accent-skin;
    }
    
    .header-content {
      display: flex;
      justify-content: space-between;
      align-items: center;
      max-width: 1400px;
      margin: 0 auto;
      padding: 0 40px;
    }
    
    .logo {
      display: flex;
      align-items: center;
      gap: 16px;
      
      &.clickable {
        cursor: pointer;
        transition: transform 0.2s ease;
        
        &:hover {
          transform: translateY(-2px);
          
          .logo-img {
            filter: drop-shadow(0 4px 6px rgba(0, 0, 0, 0.1));
          }
          
          h1 {
            text-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
          }
        }
        
        &:active {
          transform: translateY(0);
        }
      }
      
      .logo-img {
        height: 52px;
        width: auto;
        transition: filter 0.2s ease;
      }
      
      h1 {
        margin: 0;
        font-size: 32px;
        font-weight: 700;
        font-family: 'Playfair Display', 'Higuen Serif', serif;
        transition: text-shadow 0.2s ease;
      }
    }
    
    main {
      flex: 1;
      display: flex;
      justify-content: center;
      align-items: flex-start;
      padding: 30px 20px;
    }
    
    footer {
      background-color: #ffffff;
      color: #777;
      padding: 16px 0;
      text-align: center;
      font-size: 14px;
      border-top: 1px solid v.$color-accent-skin;
    }
  `]
})
export class AppComponent {
  title = 'LuxPricer Price Estimation';
  
  constructor(private navigationService: NavigationService) {}
  
  get isWelcomeActive(): boolean {
    return this.navigationService.isWelcomeActive;
  }
  
  goToHome(): void {
    if (!this.isWelcomeActive) {
      this.navigationService.goToHome();
    }
  }
} 