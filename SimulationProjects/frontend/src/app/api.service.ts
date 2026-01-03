import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { firstValueFrom } from 'rxjs';

@Injectable({ providedIn: 'root' })
export class ApiService {
  private baseUrl = 'http://localhost:8080/api';

  constructor(private http: HttpClient) {}

  // Light
  lightOn() { return firstValueFrom(this.http.get(`${this.baseUrl}/light/on`, { responseType: 'text' })); }
  lightOff() { return firstValueFrom(this.http.get(`${this.baseUrl}/light/off`, { responseType: 'text' })); }
  lightStatus() { return firstValueFrom(this.http.get<boolean>(`${this.baseUrl}/light/status`)); }

  // Garage door
  garageOpen() { return firstValueFrom(this.http.get(`${this.baseUrl}/garagedoor/open`, { responseType: 'text' })); }
  garageClose() { return firstValueFrom(this.http.get(`${this.baseUrl}/garagedoor/close`, { responseType: 'text' })); }
  garageStatus() { return firstValueFrom(this.http.get<number>(`${this.baseUrl}/garagedoor/status`)); }
}
