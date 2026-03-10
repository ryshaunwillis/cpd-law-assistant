import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';

@Injectable({
  providedIn: 'root'
})
export class ChargeAnalysisService {

  private apiUrl = 'http://localhost:4242/api/charges/analyze';

  constructor(private http: HttpClient) {}

  analyzeNarrative(query: string) {
    return this.http.post(this.apiUrl, { query });
  }

}