import { Component, ChangeDetectorRef, NgZone } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import {
    QaApiService,
    SourceItem,
    ChargeMatch,
    ChargeAnalysisResponse,
    ChatResponse,
} from '../../services/qa-api.service';
import {
    ChatSessionService,
    ChatMsg,
    ChatIntent,
} from '../../services/chat-session.service';

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
    showChargeForm = false;

    chargeForm = {
        incidentType: '',
        offenderConduct: '',
        victimType: '',
        injury: '',
        weapon: '',
        propertyTaken: '',
        forcedEntry: '',
        relationship: '',
        location: '',
        threats: '',
        policeInvolvement: '',
        narrativeNotes: '',
    };


    constructor(
        private api: QaApiService,
        private cdr: ChangeDetectorRef,
        private ngZone: NgZone,
        private session: ChatSessionService
    ) { }

    get messages(): ChatMsg[] {
        return this.session.messages;
    }

    get lastSources(): SourceItem[] {
        return this.session.lastSources;
    }

    get lastChargeAnalysis(): ChargeAnalysisResponse | null {
        return this.session.lastChargeAnalysis;
    }

    get lastIntent(): ChatIntent | null {
        return this.session.lastIntent;
    }

    async send() {
        const q = this.question.trim();
        if (!q || this.loading) return;

        if (this.shouldOpenChargeForm(q)) {
            this.session.messages = [
                ...this.session.messages,
                { role: 'user', text: q },
                {
                    role: 'assistant',
                    text: 'Fill out the charge intake form below and I’ll analyze possible Illinois charges.',
                    intent: 'charges',
                },
            ];

            this.question = '';
            this.showChargeForm = true;
            this.loading = false;
            this.cdr.detectChanges();
            return;
        }

        this.error = '';
        this.session.resetSidebar();

        this.session.messages = [
            ...this.session.messages,
            {
                role: 'user',
                text: q,
            },
        ];

        this.question = '';
        this.loading = true;
        this.cdr.detectChanges();

        try {
            const historyForApi = this.session.messages.slice(-12).map(m => ({
                role: m.role,
                text: m.text,
                intent: m.intent,
            }));

            const res: ChatResponse = await this.api.chat(q, historyForApi);

            this.ngZone.run(() => {
                this.session.lastIntent = res.intent || null;
                this.session.lastSources = [...(res.sources || [])];
                this.session.lastChargeAnalysis = res.chargeAnalysis || null;

                this.session.messages = [
                    ...this.session.messages,
                    {
                        role: 'assistant',
                        text: res.answer || '(No answer returned)',
                        intent: res.intent,
                    },
                ];

                this.cdr.detectChanges();
            });
        } catch (e: any) {
            this.ngZone.run(() => {
                this.error = e?.message || 'Request failed';

                this.session.messages = [
                    ...this.session.messages,
                    {
                        role: 'assistant',
                        text: 'Something went wrong calling the API. Make sure backend is running on port 4242.',
                    },
                ];

                this.cdr.detectChanges();
            });
        } finally {
            this.ngZone.run(() => {
                this.loading = false;
                this.cdr.detectChanges();
            });
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

    trackCharge(index: number, item: ChargeMatch) {
        return `${item.citation}-${item.sectionTitle}-${index}`;
    }

    shouldOpenChargeForm(text: string): boolean {
        const q = (text || '').toLowerCase().trim();

        return [
            'help with charges',
            'help me with charges',
            'what can i charge',
            'what could i charge',
            'charge this',
            'help figure out charges',
            'help me figure out charges',
        ].some(p => q.includes(p));
    }

    buildChargeNarrativeFromForm(): string {
        const f = this.chargeForm;

        return `
Incident type: ${f.incidentType}
Offender conduct: ${f.offenderConduct}
Victim type: ${f.victimType}
Injury: ${f.injury}
Weapon: ${f.weapon}
Property taken: ${f.propertyTaken}
Forced entry: ${f.forcedEntry}
Relationship: ${f.relationship}
Location: ${f.location}
Threats: ${f.threats}
Police involvement: ${f.policeInvolvement}
Additional notes: ${f.narrativeNotes}

What Illinois charges could apply?
  `.trim();
    }

async submitChargeForm() {
  const builtQuery = this.buildChargeNarrativeFromForm();

  this.showChargeForm = false;
  this.resetChargeForm();
  this.cdr.detectChanges();

  this.question = builtQuery;
  await this.send();
}

cancelChargeForm() {
  this.showChargeForm = false;
  this.resetChargeForm();
  this.cdr.detectChanges();
}

resetChargeForm() {
  this.chargeForm = {
    incidentType: '',
    offenderConduct: '',
    victimType: '',
    injury: '',
    weapon: '',
    propertyTaken: '',
    forcedEntry: '',
    relationship: '',
    location: '',
    threats: '',
    policeInvolvement: '',
    narrativeNotes: '',
  };
}
}