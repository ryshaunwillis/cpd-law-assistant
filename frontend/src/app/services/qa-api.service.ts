import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { firstValueFrom } from 'rxjs';
import { environment } from '../../../../backend/src/environments/environment';


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

@Injectable({ providedIn: 'root' })
export class QaApiService {
    private apiBase = environment.apiBase;

  constructor(private http: HttpClient) {}

  async ask(question: string): Promise<AskResponse> {
    return await firstValueFrom(
      this.http.post<AskResponse>(`${this.apiBase}/api/ask`, { question })
    );
  }
}