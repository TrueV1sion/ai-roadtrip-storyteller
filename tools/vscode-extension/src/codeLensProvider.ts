import * as vscode from 'vscode';
import { KnowledgeGraphClient } from './kgClient';

export class CodeLensProvider implements vscode.CodeLensProvider {
    private _onDidChangeCodeLenses: vscode.EventEmitter<void> = new vscode.EventEmitter<void>();
    public readonly onDidChangeCodeLenses: vscode.Event<void> = this._onDidChangeCodeLenses.event;
    
    constructor(private kgClient: KnowledgeGraphClient) {}
    
    async provideCodeLenses(
        document: vscode.TextDocument,
        token: vscode.CancellationToken
    ): Promise<vscode.CodeLens[]> {
        const codeLenses: vscode.CodeLens[] = [];
        
        // Add code lens at the top of the file
        const topOfDocument = new vscode.Range(0, 0, 0, 0);
        
        // Impact analysis lens
        codeLenses.push(new vscode.CodeLens(topOfDocument, {
            title: "$(graph) Analyze Impact",
            command: "roadtrip-kg.analyzeImpact",
            tooltip: "Analyze impact of changes to this file"
        }));
        
        // Pattern search lens
        codeLenses.push(new vscode.CodeLens(topOfDocument, {
            title: "$(search) Find Similar",
            command: "roadtrip-kg.searchPatterns",
            tooltip: "Find similar patterns in codebase"
        }));
        
        // Add function-level code lenses
        const text = document.getText();
        const functionRegex = /^(async\s+)?function\s+(\w+)|^(export\s+)?(async\s+)?const\s+(\w+)\s*=/gm;
        const classRegex = /^(export\s+)?class\s+(\w+)/gm;
        
        let match;
        
        // Find functions
        while ((match = functionRegex.exec(text)) !== null) {
            const line = document.lineAt(document.positionAt(match.index).line);
            const range = new vscode.Range(line.range.start, line.range.end);
            
            codeLenses.push(new vscode.CodeLens(range, {
                title: "$(info) Show dependencies",
                command: "roadtrip-kg.showDependencies",
                arguments: [document.uri, range]
            }));
        }
        
        // Find classes
        while ((match = classRegex.exec(text)) !== null) {
            const line = document.lineAt(document.positionAt(match.index).line);
            const range = new vscode.Range(line.range.start, line.range.end);
            
            codeLenses.push(new vscode.CodeLens(range, {
                title: "$(symbol-class) Analyze class impact",
                command: "roadtrip-kg.analyzeClassImpact",
                arguments: [document.uri, range]
            }));
        }
        
        return codeLenses;
    }
    
    resolveCodeLens(codeLens: vscode.CodeLens, token: vscode.CancellationToken): vscode.CodeLens {
        return codeLens;
    }
}