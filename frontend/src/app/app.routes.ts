import { Routes } from '@angular/router';
import { ChatComponent } from './pages/chat/chat.component';
import { HttpClientModule } from '@angular/common/http';

export const routes: Routes = [
  { path: '', component: ChatComponent },
  { path: '**', redirectTo: '' },
];