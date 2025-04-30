import { NgModule } from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';
import { HttpClientModule } from '@angular/common/http';
import { FormsModule } from '@angular/forms';

import { AppComponent } from './app.component';
import { ChatComponent } from './chat/chat.component';
import { AppraisalService } from './services/appraisal.service';
import { MarkdownService } from './services/markdown.service';
import { PdfService } from './services/pdf.service';
import { BrandButtonComponent } from './shared/brand-button/brand-button.component';
import { NavigationService } from './services/navigation.service';

@NgModule({
  declarations: [
    AppComponent,
    ChatComponent,
    BrandButtonComponent
  ],
  imports: [
    BrowserModule,
    HttpClientModule,
    FormsModule
  ],
  providers: [
    AppraisalService,
    MarkdownService,
    PdfService,
    NavigationService
  ],
  bootstrap: [AppComponent]
})
export class AppModule { } 