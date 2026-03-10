import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { firstValueFrom } from 'rxjs';

export type SourceItem = {
  source: string;
  title: string;
  text: string;
  url: string;
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

export type ChatApiResponse = {
  success: boolean;
  intent: 'qa' | 'charges' | 'hybrid';
  answer: string;
  sources: SourceItem[];
  chargeAnalysis: ChargeAnalysisResponse | null;
};

@Injectable({
  providedIn: 'root',
})
export class ChatApiService {
  private apiUrl = 'http://localhost:4242/api/chat';

  constructor(private http: HttpClient) {}

  send(query: string): Promise<ChatApiResponse> {
    return firstValueFrom(
      this.http.post<ChatApiResponse>(this.apiUrl, { query })
    );
  }
}