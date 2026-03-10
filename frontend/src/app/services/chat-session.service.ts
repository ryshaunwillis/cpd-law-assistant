import { Injectable } from '@angular/core';
import {
  ChargeAnalysisResponse,
  SourceItem,
} from './qa-api.service';

export type ChatIntent = 'qa' | 'charges' | 'hybrid';

export type ChatMsg = {
  role: 'user' | 'assistant';
  text: string;
  intent?: ChatIntent;
};

@Injectable({
  providedIn: 'root',
})
export class ChatSessionService {
  messages: ChatMsg[] = [
    {
      role: 'assistant',
      text:
        'Ask a question about CPD directives or Illinois law. You can also describe an incident and I’ll try to identify possible charges.',
      intent: 'qa',
    },
  ];

  lastSources: SourceItem[] = [];
  lastChargeAnalysis: ChargeAnalysisResponse | null = null;
  lastIntent: ChatIntent | null = null;

  resetSidebar() {
    this.lastSources = [];
    this.lastChargeAnalysis = null;
    this.lastIntent = null;
  }
}