import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { QaApiService, SourceItem } from '../../services/qa-api.service';

type ChatMsg = {
  role: 'user' | 'assistant';
  text: string;
};

@Component({
  selector: 'app-chat',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './chat.component.html',
  styleUrls: ['./chat.component.scss'],
})
export class ChatComponent {
  question = '';
  loading = false;
  error = '';

  messages: ChatMsg[] = [
    {
      role: 'assistant',
      text:
        'Ask a question about CPD directives or Illinois law. I will answer using quotes + sources when available.',
    },
  ];

  lastSources: SourceItem[] = [];

  constructor(private api: QaApiService) {}

  async send() {
    const q = this.question.trim();
    if (!q || this.loading) return;

    this.error = '';
    this.lastSources = [];
    this.messages.push({ role: 'user', text: q });
    this.question = '';
    this.loading = true;

    try {
      const res = await this.api.ask(q);
      this.messages.push({ role: 'assistant', text: res.answer || '(No answer returned)' });
      this.lastSources = res.sources || [];
    } catch (e: any) {
      this.error = e?.message || 'Request failed';
      this.messages.push({
        role: 'assistant',
        text: `Something went wrong calling the API. Make sure backend is running on port 4242.`,
      });
    } finally {
      this.loading = false;
    }
  }

  onEnter(ev: KeyboardEvent) {
    if (ev.key === 'Enter' && !ev.shiftKey) {
      ev.preventDefault();
      this.send();
    }
  }

  shortText(t: string, max = 240) {
    const s = (t || '').replace(/\s+/g, ' ').trim();
    if (s.length <= max) return s;
    return s.slice(0, max) + '…';
  }
} 