import * as vscode from 'vscode';

export class DiagnosticManager {
    private diagnosticCollection: vscode.DiagnosticCollection;
    
    constructor() {
        this.diagnosticCollection = vscode.languages.createDiagnosticCollection('roadtrip-kg');
    }
    
    addDiagnostic(
        uri: vscode.Uri,
        range: vscode.Range,
        message: string,
        severity: vscode.DiagnosticSeverity = vscode.DiagnosticSeverity.Warning
    ) {
        const diagnostic = new vscode.Diagnostic(range, message, severity);
        diagnostic.source = 'Knowledge Graph';
        
        const existingDiagnostics = this.diagnosticCollection.get(uri) || [];
        this.diagnosticCollection.set(uri, [...existingDiagnostics, diagnostic]);
    }
    
    clearDiagnostics(uri: vscode.Uri) {
        this.diagnosticCollection.delete(uri);
    }
    
    updateFromValidation(uri: vscode.Uri, validation: any) {
        this.clearDiagnostics(uri);
        
        validation.results.forEach((result: any) => {
            result.findings.forEach((finding: any) => {
                const severity = this.getSeverity(finding.severity || result.severity);
                
                // Try to extract line number from finding
                const line = finding.line || 0;
                const range = new vscode.Range(line, 0, line, 0);
                
                this.addDiagnostic(uri, range, finding.message, severity);
            });
        });
    }
    
    private getSeverity(severity: string): vscode.DiagnosticSeverity {
        switch (severity) {
            case 'critical':
                return vscode.DiagnosticSeverity.Error;
            case 'high':
                return vscode.DiagnosticSeverity.Warning;
            case 'medium':
                return vscode.DiagnosticSeverity.Information;
            case 'low':
            default:
                return vscode.DiagnosticSeverity.Hint;
        }
    }
    
    dispose() {
        this.diagnosticCollection.dispose();
    }
}