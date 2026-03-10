import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { firstValueFrom } from 'rxjs';
import { environment } from '../../environments/environment';


export type SourceItem = {
  title: string;
  url: string;
  source: string;
  text: string;
};

export type AskResponse = {
  answer: string;
  sources: SourceItem[];
};

export type ChargeMatch = {
  citation: string;
  sectionTitle: string;
  whyItFits?: string[];
  missingFacts?: string[];
  analysisScore?: number;
};

export type ChargeAnalysisResponse = {
  likelyCharges?: ChargeMatch[];
  possibleCharges?: ChargeMatch[];
  possibleEnhancedCharges?: ChargeMatch[];
  contextualMatches?: ChargeMatch[];
  globalMissingFacts?: string[];
  disclaimer?: string;
};

export type ChatIntent = 'qa' | 'charges' | 'hybrid';

export type ChatMessage = {
  role: 'user' | 'assistant';
  text: string;
  intent?: ChatIntent;
};

export type ChatResponse = {
  success: boolean;
  intent: ChatIntent;
  answer: string;
  sources: SourceItem[];
  chargeAnalysis: ChargeAnalysisResponse | null;
};

@Injectable({ providedIn: 'root' })
export class QaApiService {
  private apiBase = environment.apiBase;

  constructor(private http: HttpClient) {}

  async ask(question: string): Promise<AskResponse> {
    return await firstValueFrom(
      this.http.post<AskResponse>(`${this.apiBase}/api/ask`, { question })
    );
  }

  async chat(query: string, history: ChatMessage[] = []): Promise<ChatResponse> {
    return await firstValueFrom(
      this.http.post<ChatResponse>(`${this.apiBase}/api/chat`, {
        query,
        history,
      })
    );
  }
}