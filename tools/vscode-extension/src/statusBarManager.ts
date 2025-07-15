import * as vscode from 'vscode';

export class StatusBarManager {
    private statusBarItem: vscode.StatusBarItem;
    private statusIcons = {
        connected: '$(check) KG',
        disconnected: '$(x) KG',
        analyzing: '$(sync~spin) KG',
        searching: '$(search) KG',
        validating: '$(shield) KG',
        error: '$(warning) KG'
    };
    
    constructor() {
        this.statusBarItem = vscode.window.createStatusBarItem(
            vscode.StatusBarAlignment.Right,
            100
        );
        this.statusBarItem.command = 'roadtrip-kg.showStatus';
        this.setStatus('disconnected');
        this.statusBarItem.show();
    }
    
    setStatus(status: keyof typeof this.statusIcons) {
        this.statusBarItem.text = this.statusIcons[status];
        
        switch (status) {
            case 'connected':
                this.statusBarItem.tooltip = 'Knowledge Graph connected';
                this.statusBarItem.backgroundColor = undefined;
                break;
            case 'disconnected':
                this.statusBarItem.tooltip = 'Knowledge Graph disconnected - Click to reconnect';
                this.statusBarItem.backgroundColor = new vscode.ThemeColor('statusBarItem.errorBackground');
                break;
            case 'analyzing':
                this.statusBarItem.tooltip = 'Analyzing impact...';
                break;
            case 'error':
                this.statusBarItem.tooltip = 'Knowledge Graph error';
                this.statusBarItem.backgroundColor = new vscode.ThemeColor('statusBarItem.warningBackground');
                break;
        }
    }
    
    dispose() {
        this.statusBarItem.dispose();
    }
}