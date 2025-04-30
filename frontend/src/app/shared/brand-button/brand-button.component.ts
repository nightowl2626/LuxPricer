import { Component, Input } from '@angular/core';

@Component({
  selector: 'app-brand-button',
  template: `
    <button [ngClass]="color" class="brand-btn">
      <ng-content></ng-content>
    </button>
  `,
  styles: [`
    @use 'src/styles/variables' as v;

    .brand-btn {
      border: none;
      border-radius: v.$radius-pill;
      padding: .75rem 1.5rem;
      font-family: 'Playfair Display', 'Higuen Serif', serif;
      font-size: 1.25rem;
      cursor: pointer;
      color: #fff;
      box-shadow: 0 4px 10px rgba(0, 0, 0, 0.08);
      transition: all 0.3s ease;
      display: inline-block;
      text-align: center;

      &:active { transform: scale(.97); }
      
      &:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 15px rgba(0, 0, 0, 0.12);
      }

      &.brown { background: v.$color-brand-brown; }
      &.purple { background: v.$color-brand-purple; }
      &.green { background: v.$color-accent-dark; }
    }
  `]
})
export class BrandButtonComponent {
  @Input() color: 'brown' | 'purple' | 'green' = 'purple';
} 