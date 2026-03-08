import { Routes } from '@angular/router';
import { ChatComponent } from './pages/chat/chat.component';

export const routes: Routes = [
  { path: '', component: ChatComponent },
  { path: '**', redirectTo: '' },
];