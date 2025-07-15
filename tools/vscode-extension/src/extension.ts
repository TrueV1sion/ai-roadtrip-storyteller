import * as vscode from 'vscode';
import { KnowledgeGraphClient } from './kgClient';
import { CodeLensProvider } from './codeLensProvider';
import { DiagnosticManager } from './diagnosticManager';
import { StatusBarManager } from './statusBarManager';

let kgClient: KnowledgeGraphClient;
let diagnosticManager: DiagnosticManager;
let statusBarManager: StatusBarManager;

export function activate(context: vscode.ExtensionContext) {
    console.log('Road Trip Knowledge Graph extension activated');
    
    // Initialize components
    const config = vscode.workspace.getConfiguration('roadtrip-kg');
    const serverUrl = config.get<string>('serverUrl', 'http://localhost:8000');
    
    kgClient = new KnowledgeGraphClient(serverUrl);
    diagnosticManager = new DiagnosticManager();
    statusBarManager = new StatusBarManager();
    
    // Check KG health
    kgClient.checkHealth().then(isHealthy => {
        if (isHealthy) {
            statusBarManager.setStatus('connected');
            vscode.window.showInformationMessage('Knowledge Graph connected!');
        } else {
            statusBarManager.setStatus('disconnected');
            vscode.window.showWarningMessage('Knowledge Graph is not running. Start with: docker-compose up');
        }
    });
    
    // Register commands
    context.subscriptions.push(
        vscode.commands.registerCommand('roadtrip-kg.analyzeImpact', analyzeImpact),
        vscode.commands.registerCommand('roadtrip-kg.searchPatterns', searchPatterns),
        vscode.commands.registerCommand('roadtrip-kg.validateFile', validateFile),
        vscode.commands.registerCommand('roadtrip-kg.showSuggestions', showSuggestions),
        vscode.commands.registerCommand('roadtrip-kg.toggleRealTime', toggleRealTime)
    );
    
    // Register code lens provider
    const codeLensProvider = new CodeLensProvider(kgClient);
    context.subscriptions.push(
        vscode.languages.registerCodeLensProvider(
            { pattern: '**/*.{py,js,ts,tsx}' },
            codeLensProvider
        )
    );
    
    // Set up file watchers for real-time analysis
    if (config.get<boolean>('enableRealTimeAnalysis', true)) {
        setupFileWatchers(context);
    }
    
    // Add status bar
    context.subscriptions.push(statusBarManager);
}

async function analyzeImpact() {
    const editor = vscode.window.activeTextEditor;
    if (!editor) {
        vscode.window.showErrorMessage('No active editor');
        return;
    }
    
    const filePath = vscode.workspace.asRelativePath(editor.document.uri);
    statusBarManager.setStatus('analyzing');
    
    try {
        const impact = await kgClient.analyzeImpact(filePath);
        
        // Create webview to show results
        const panel = vscode.window.createWebviewPanel(
            'kgImpactAnalysis',
            `Impact Analysis: ${filePath}`,
            vscode.ViewColumn.Two,
            { enableScripts: true }
        );
        
        panel.webview.html = getImpactHtml(filePath, impact);
        statusBarManager.setStatus('connected');
        
        // Add diagnostics for high-impact changes
        if (impact.dependencies && impact.dependencies.length > 10) {
            diagnosticManager.addDiagnostic(
                editor.document.uri,
                new vscode.Range(0, 0, 0, 0),
                `High impact: This file affects ${impact.dependencies.length} other files`,
                vscode.DiagnosticSeverity.Warning
            );
        }
        
    } catch (error) {
        vscode.window.showErrorMessage(`Analysis failed: ${error}`);
        statusBarManager.setStatus('error');
    }
}

async function searchPatterns() {
    const query = await vscode.window.showInputBox({
        prompt: 'Enter pattern to search for',
        placeHolder: 'e.g., authentication, repository pattern, error handling'
    });
    
    if (!query) return;
    
    statusBarManager.setStatus('searching');
    
    try {
        const results = await kgClient.searchPatterns(query);
        
        // Show results in quick pick
        const items = results.map(r => ({
            label: r.file,
            description: `Score: ${r.score.toFixed(2)}`,
            detail: r.snippet,
            result: r
        }));
        
        const selected = await vscode.window.showQuickPick(items, {
            placeHolder: 'Select a result to open'
        });
        
        if (selected) {
            // Open the file
            const uri = vscode.Uri.file(selected.result.file);
            const doc = await vscode.workspace.openTextDocument(uri);
            await vscode.window.showTextDocument(doc);
        }
        
        statusBarManager.setStatus('connected');
        
    } catch (error) {
        vscode.window.showErrorMessage(`Search failed: ${error}`);
        statusBarManager.setStatus('error');
    }
}

async function validateFile() {
    const editor = vscode.window.activeTextEditor;
    if (!editor) return;
    
    const filePath = vscode.workspace.asRelativePath(editor.document.uri);
    statusBarManager.setStatus('validating');
    
    try {
        const validation = await kgClient.validateFile(filePath);
        
        // Clear existing diagnostics
        diagnosticManager.clearDiagnostics(editor.document.uri);
        
        // Add new diagnostics
        validation.results.forEach((result: any) => {
            result.findings.forEach((finding: any) => {
                const severity = finding.severity === 'critical' 
                    ? vscode.DiagnosticSeverity.Error
                    : finding.severity === 'high'
                    ? vscode.DiagnosticSeverity.Warning
                    : vscode.DiagnosticSeverity.Information;
                
                diagnosticManager.addDiagnostic(
                    editor.document.uri,
                    new vscode.Range(0, 0, 0, 0), // Would need line numbers from KG
                    finding.message,
                    severity
                );
            });
        });
        
        // Show summary
        const severity = validation.severity;
        const message = `Validation complete: ${severity}`;
        
        if (severity === 'critical') {
            vscode.window.showErrorMessage(message);
        } else if (severity === 'high') {
            vscode.window.showWarningMessage(message);
        } else {
            vscode.window.showInformationMessage(message);
        }
        
        statusBarManager.setStatus('connected');
        
    } catch (error) {
        vscode.window.showErrorMessage(`Validation failed: ${error}`);
        statusBarManager.setStatus('error');
    }
}

async function showSuggestions() {
    const editor = vscode.window.activeTextEditor;
    if (!editor) return;
    
    // Get current selection or word
    const selection = editor.selection;
    const wordRange = editor.document.getWordRangeAtPosition(selection.start);
    const word = editor.document.getText(wordRange);
    
    try {
        const suggestions = await kgClient.getSuggestions(word);
        
        // Show suggestions in quick pick
        const items = suggestions.map(s => ({
            label: s.title,
            description: s.type,
            detail: s.description
        }));
        
        await vscode.window.showQuickPick(items, {
            placeHolder: 'Suggestions from Knowledge Graph'
        });
        
    } catch (error) {
        vscode.window.showErrorMessage(`Failed to get suggestions: ${error}`);
    }
}

function toggleRealTime() {
    const config = vscode.workspace.getConfiguration('roadtrip-kg');
    const current = config.get<boolean>('enableRealTimeAnalysis', true);
    config.update('enableRealTimeAnalysis', !current, true);
    
    vscode.window.showInformationMessage(
        `Real-time analysis ${!current ? 'enabled' : 'disabled'}`
    );
}

function setupFileWatchers(context: vscode.ExtensionContext) {
    // Watch for file saves
    const saveWatcher = vscode.workspace.onDidSaveTextDocument(async (document) => {
        if (!isRelevantFile(document)) return;
        
        const filePath = vscode.workspace.asRelativePath(document.uri);
        
        // Notify KG of file change
        try {
            await kgClient.notifyFileChange(filePath, 'saved');
            
            // Run validation in background
            const validation = await kgClient.validateFile(filePath);
            
            if (validation.severity === 'critical' || validation.severity === 'high') {
                diagnosticManager.updateFromValidation(document.uri, validation);
            }
            
        } catch (error) {
            console.error('Failed to notify KG of file change:', error);
        }
    });
    
    context.subscriptions.push(saveWatcher);
}

function isRelevantFile(document: vscode.TextDocument): boolean {
    const extensions = ['.py', '.js', '.ts', '.tsx', '.jsx'];
    return extensions.some(ext => document.fileName.endsWith(ext));
}

function getImpactHtml(filePath: string, impact: any): string {
    const dependencies = impact.dependencies || [];
    const riskLevel = dependencies.length > 20 ? 'Critical' 
                    : dependencies.length > 10 ? 'High'
                    : dependencies.length > 5 ? 'Medium' 
                    : 'Low';
    
    return `
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body { 
                    font-family: var(--vscode-font-family); 
                    color: var(--vscode-foreground);
                    padding: 20px;
                }
                h1 { color: var(--vscode-textLink-foreground); }
                .risk-critical { color: #f44336; }
                .risk-high { color: #ff9800; }
                .risk-medium { color: #ffc107; }
                .risk-low { color: #4caf50; }
                .dependency {
                    padding: 5px;
                    margin: 2px 0;
                    background: var(--vscode-editor-background);
                    border-left: 3px solid var(--vscode-textLink-foreground);
                }
                .stats {
                    display: flex;
                    gap: 20px;
                    margin: 20px 0;
                }
                .stat {
                    padding: 10px;
                    background: var(--vscode-editor-background);
                    border-radius: 5px;
                }
            </style>
        </head>
        <body>
            <h1>Impact Analysis: ${filePath}</h1>
            
            <div class="stats">
                <div class="stat">
                    <strong>Dependencies:</strong> ${dependencies.length}
                </div>
                <div class="stat">
                    <strong>Risk Level:</strong> 
                    <span class="risk-${riskLevel.toLowerCase()}">${riskLevel}</span>
                </div>
            </div>
            
            <h2>Affected Files</h2>
            <div id="dependencies">
                ${dependencies.map(dep => `
                    <div class="dependency">${dep}</div>
                `).join('')}
            </div>
            
            <h2>Recommendations</h2>
            <ul>
                ${dependencies.length > 10 ? '<li>Consider breaking this file into smaller modules</li>' : ''}
                ${dependencies.length > 5 ? '<li>Ensure comprehensive testing before changes</li>' : ''}
                <li>Run full test suite after modifications</li>
            </ul>
        </body>
        </html>
    `;
}

export function deactivate() {
    if (diagnosticManager) {
        diagnosticManager.dispose();
    }
}