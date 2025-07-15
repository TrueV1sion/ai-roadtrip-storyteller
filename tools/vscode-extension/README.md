# Road Trip AI Knowledge Graph - VS Code Extension

Real-time code analysis and pattern suggestions powered by the Knowledge Graph.

## Features

### 🔍 Impact Analysis
- See which files depend on your current file
- Understand the ripple effects of changes
- Risk assessment for modifications

### 🎯 Pattern Search
- Find similar implementations across the codebase
- Learn from existing patterns
- Discover reusable code

### ✅ Real-time Validation
- Instant feedback on code quality
- Pattern compliance checking
- Breaking change detection

### 💡 Smart Suggestions
- Context-aware code improvements
- Best practice recommendations
- Refactoring opportunities

## Installation

1. Ensure Knowledge Graph is running:
   ```bash
   docker-compose up knowledge-graph
   ```

2. Install the extension:
   - Open VS Code
   - Go to Extensions (Ctrl+Shift+X)
   - Search for "Road Trip Knowledge Graph"
   - Click Install

3. Or install from VSIX:
   ```bash
   code --install-extension roadtrip-knowledge-graph-0.1.0.vsix
   ```

## Usage

### Commands

| Command | Shortcut | Description |
|---------|----------|-------------|
| Analyze Impact | `Ctrl+Shift+I` | Analyze impact of current file |
| Search Patterns | `Ctrl+Shift+P` | Search for similar patterns |
| Validate File | - | Run full validation |
| Show Suggestions | - | Get improvement suggestions |

### Status Bar

The extension shows KG status in the status bar:
- ✓ KG - Connected and ready
- ✗ KG - Disconnected
- ↻ KG - Analyzing
- 🔍 KG - Searching
- ⚠ KG - Error

### Code Lens

Look for inline actions above functions and classes:
- "Analyze Impact" - Check dependencies
- "Find Similar" - Search for patterns
- "Show dependencies" - Function-level analysis

### Real-time Analysis

When enabled, the extension will:
- Analyze files on save
- Show inline warnings for issues
- Suggest improvements automatically

## Configuration

Access settings via `File > Preferences > Settings > Extensions > Road Trip Knowledge Graph`

| Setting | Default | Description |
|---------|---------|-------------|
| `serverUrl` | `http://localhost:8000` | Knowledge Graph server URL |
| `enableRealTimeAnalysis` | `true` | Enable real-time analysis |
| `showInlineHints` | `true` | Show inline code hints |
| `highlightDependencies` | `true` | Highlight dependent files |
| `severityLevel` | `medium` | Minimum severity to show |

## Examples

### Analyzing Impact

1. Open any Python/JS/TS file
2. Press `Ctrl+Shift+I`
3. View impact analysis in side panel

### Finding Patterns

1. Select code or place cursor on a function
2. Press `Ctrl+Shift+P`
3. Enter search query (e.g., "authentication")
4. Browse results and click to open

### Validating Changes

1. Make changes to a file
2. Save the file
3. View diagnostics in Problems panel
4. Fix issues based on suggestions

## Troubleshooting

### Extension not connecting

1. Check Knowledge Graph is running:
   ```bash
   curl http://localhost:8000/api/health
   ```

2. Verify server URL in settings

3. Check Docker logs:
   ```bash
   docker-compose logs knowledge-graph
   ```

### No results shown

1. Ensure codebase is analyzed:
   ```bash
   curl -X POST http://localhost:8000/api/analyze/codebase
   ```

2. Check file is in a supported language (Python, JS, TS)

## Development

To contribute to the extension:

```bash
# Clone repository
git clone <repo>
cd tools/vscode-extension

# Install dependencies
npm install

# Compile
npm run compile

# Watch for changes
npm run watch

# Run tests
npm test
```

## License

Part of the Road Trip AI project.