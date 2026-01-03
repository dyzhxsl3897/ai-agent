import { Component, signal } from '@angular/core';
import { ApiService } from './api.service';

@Component({
  selector: 'app-root',
  imports: [],
  templateUrl: './app.html',
  styleUrl: './app.css'
})
export class App {
  protected readonly title = signal('frontend');

  lightOnState = signal<boolean | null>(null);
  garageHeight = signal<number | null>(null);
  busy = signal(false);
  message = '';

  private refreshTimer: any;

  constructor(public api: ApiService) { }

  ngOnInit() {
    this.refresh(); // 先立即刷一次

    this.refreshTimer = setInterval(() => {
      this.refresh();
    }, 333);
  }

  async refresh() {
    this.message = '';
    try {
      this.lightOnState.set(await this.api.lightStatus());
      this.garageHeight.set(await this.api.garageStatus());
    } catch (e: any) {
      this.message = `Error: ${e?.message ?? e}`;
    }
  }

  private async run(action: () => Promise<any>) {
    this.busy.set(true);
    this.message = '';
    try {
      await action();
      await this.refresh();
    } catch (e: any) {
      this.message = `Error: ${e?.message ?? e}`;
    } finally {
      this.busy.set(false);
    }
  }

  // ----- Actions exposed to template -----
  lightOn() { return this.run(() => this.api.lightOn()); }
  lightOff() { return this.run(() => this.api.lightOff()); }
  garageOpen() { return this.run(() => this.api.garageOpen()); }
  garageClose() { return this.run(() => this.api.garageClose()); }

  ngOnDestroy() {
    if (this.refreshTimer) {
      clearInterval(this.refreshTimer);
    }
  }

}
