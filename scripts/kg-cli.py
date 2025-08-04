#!/usr/bin/env python3
"""
Knowledge Graph CLI Tool
Provides command-line access to Knowledge Graph features
"""

import click
import httpx
import json
import sys
from pathlib import Path
from typing import Dict, Any, List
from rich.console import Console
from rich.table import Table
from rich.syntax import Syntax
from rich.panel import Panel
from rich.tree import Tree
from rich import print as rprint

console = Console()

# Configuration
KG_URL = "http://localhost:8000"
TIMEOUT = 10.0


class KnowledgeGraphCLI:
    """CLI client for Knowledge Graph operations"""
    
    def __init__(self, base_url: str = KG_URL):
        self.base_url = base_url
        self.client = httpx.Client(base_url=base_url, timeout=TIMEOUT)
    
    def check_health(self) -> bool:
        """Check if Knowledge Graph is running"""
        try:
            response = self.client.get("/api/health")
            return response.status_code == 200
        except Exception as e:
            return False
    
    def analyze_impact(self, file_path: str) -> Dict[str, Any]:
        """Analyze impact of changes to a file"""
        response = self.client.post(
            "/api/impact/analyze",
            json={"node_id": file_path, "max_depth": 5}
        )
        return response.json()
    
    def search_patterns(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search for code patterns"""
        response = self.client.post(
            "/api/search",
            json={"query": query, "limit": limit}
        )
        return response.json()
    
    def validate_commit(self, files: List[str]) -> Dict[str, Any]:
        """Validate files before commit"""
        response = self.client.post(
            "/api/agent/pre-commit",
            json={"files": files, "message": "CLI validation"}
        )
        return response.json()
    
    def get_agent_status(self) -> Dict[str, Any]:
        """Get status of all agents"""
        response = self.client.get("/api/agent/status")
        return response.json()
    
    def analyze_file(self, file_path: str) -> Dict[str, Any]:
        """Request full analysis of a file"""
        response = self.client.post(
            "/api/agent/analyze",
            json={
                "type": "file_change",
                "data": {"file_path": file_path}
            }
        )
        return response.json()


# CLI instance
kg_cli = KnowledgeGraphCLI()


@click.group()
@click.option('--url', default=KG_URL, help='Knowledge Graph server URL')
@click.pass_context
def cli(ctx, url):
    """Road Trip AI Knowledge Graph CLI
    
    Analyze code impact, search patterns, and validate changes.
    """
    ctx.obj = KnowledgeGraphCLI(url)
    
    # Check if KG is running
    if not ctx.obj.check_health():
        console.print("[red]❌ Knowledge Graph is not running![/red]")
        console.print("[yellow]Start it with: docker-compose up knowledge-graph[/yellow]")
        sys.exit(1)


@cli.command()
@click.pass_obj
def status(kg: KnowledgeGraphCLI):
    """Check Knowledge Graph and agent status"""
    console.print("[green]✅ Knowledge Graph is running[/green]\n")
    
    # Get agent status
    agent_status = kg.get_agent_status()
    
    table = Table(title="Agent Status", show_header=True)
    table.add_column("Agent", style="cyan")
    table.add_column("Status", style="magenta")
    table.add_column("Running", style="green")
    
    for agent_name, status in agent_status.items():
        running = "✅" if status.get("running") else "❌"
        table.add_row(
            agent_name,
            status.get("status", "unknown"),
            running
        )
    
    console.print(table)


@cli.command()
@click.argument('file_path')
@click.option('--depth', default=5, help='Maximum depth for impact analysis')
@click.pass_obj
def impact(kg: KnowledgeGraphCLI, file_path: str, depth: int):
    """Analyze impact of changes to a file
    
    Example: kg-cli impact backend/app/services/booking_services.py
    """
    with console.status(f"Analyzing impact of {file_path}..."):
        result = kg.analyze_impact(file_path)
    
    # Display results
    panel = Panel(
        f"[bold]Impact Analysis: {file_path}[/bold]",
        expand=False
    )
    console.print(panel)
    
    # Show dependencies
    deps = result.get("impacted_files", [])
    if deps:
        console.print(f"\n[yellow]This file affects {len(deps)} other files:[/yellow]")
        
        tree = Tree("Dependencies")
        for dep in deps[:10]:  # Show first 10
            tree.add(f"[cyan]{dep}[/cyan]")
        if len(deps) > 10:
            tree.add(f"[dim]... and {len(deps) - 10} more[/dim]")
        
        console.print(tree)
    else:
        console.print("[green]No dependencies found[/green]")
    
    # Show risk assessment
    risk_level = "Low"
    if len(deps) > 20:
        risk_level = "[red]Critical[/red]"
    elif len(deps) > 10:
        risk_level = "[yellow]High[/yellow]"
    elif len(deps) > 5:
        risk_level = "[orange]Medium[/orange]"
    
    console.print(f"\n[bold]Risk Level:[/bold] {risk_level}")


@cli.command()
@click.argument('query')
@click.option('--limit', default=10, help='Maximum results to return')
@click.pass_obj
def search(kg: KnowledgeGraphCLI, query: str, limit: int):
    """Search for code patterns
    
    Example: kg-cli search "authentication pattern"
    """
    with console.status(f"Searching for '{query}'..."):
        results = kg.search_patterns(query, limit)
    
    if not results:
        console.print(f"[yellow]No results found for '{query}'[/yellow]")
        return
    
    console.print(f"\n[green]Found {len(results)} results:[/green]\n")
    
    for i, result in enumerate(results, 1):
        file_path = result.get("file", "Unknown")
        score = result.get("score", 0)
        snippet = result.get("snippet", "")
        
        # Create result panel
        panel = Panel(
            f"[cyan]{file_path}[/cyan]\n"
            f"[dim]Score: {score:.2f}[/dim]\n\n"
            f"{snippet}",
            title=f"Result {i}",
            expand=False
        )
        console.print(panel)


@cli.command()
@click.argument('file_path')
@click.pass_obj
def analyze(kg: KnowledgeGraphCLI, file_path: str):
    """Run full agent analysis on a file
    
    Example: kg-cli analyze backend/app/routes/booking.py
    """
    with console.status(f"Running agent analysis on {file_path}..."):
        result = kg.analyze_file(file_path)
    
    severity = result.get("severity", "unknown")
    
    # Color code severity
    severity_color = {
        "critical": "red",
        "high": "yellow",
        "medium": "orange",
        "low": "green"
    }.get(severity, "white")
    
    console.print(f"\n[bold]Analysis Complete[/bold]")
    console.print(f"Severity: [{severity_color}]{severity}[/{severity_color}]\n")
    
    # Show results from each agent
    for agent_result in result.get("results", []):
        agent_name = agent_result.get("agent_name", "Unknown")
        findings = agent_result.get("findings", [])
        suggestions = agent_result.get("suggestions", [])
        
        if findings or suggestions:
            console.print(f"[bold cyan]{agent_name}:[/bold cyan]")
            
            if findings:
                console.print("  [yellow]Findings:[/yellow]")
                for finding in findings:
                    console.print(f"    • {finding.get('message', finding)}")
            
            if suggestions:
                console.print("  [green]Suggestions:[/green]")
                for suggestion in suggestions:
                    console.print(f"    • {suggestion.get('message', suggestion)}")
            
            console.print()


@cli.command()
@click.argument('files', nargs=-1, required=True)
@click.pass_obj
def validate(kg: KnowledgeGraphCLI, files):
    """Validate files before committing
    
    Example: kg-cli validate backend/app/services/*.py
    """
    file_list = list(files)
    
    with console.status(f"Validating {len(file_list)} files..."):
        result = kg.validate_commit(file_list)
    
    allow_commit = result.get("allow_commit", False)
    severity = result.get("analysis", {}).get("severity", "unknown")
    
    if allow_commit:
        console.print("[green]✅ Validation passed![/green]")
        console.print(f"Severity: {severity}")
    else:
        console.print("[red]❌ Validation failed![/red]")
        console.print(f"Severity: [red]{severity}[/red]")
        console.print("\n[yellow]Issues found:[/yellow]")
        
        # Show issues
        for agent_result in result.get("analysis", {}).get("results", []):
            for finding in agent_result.get("findings", []):
                console.print(f"  • {finding.get('message', finding)}")


@cli.command()
@click.argument('pattern_type')
@click.option('--examples', default=5, help='Number of examples to show')
@click.pass_obj
def patterns(kg: KnowledgeGraphCLI, pattern_type: str, examples: int):
    """Find examples of code patterns
    
    Example: kg-cli patterns "repository pattern"
    """
    with console.status(f"Finding {pattern_type} examples..."):
        results = kg.search_patterns(pattern_type, examples)
    
    if not results:
        console.print(f"[yellow]No examples found for '{pattern_type}'[/yellow]")
        return
    
    console.print(f"\n[green]Found {len(results)} examples of {pattern_type}:[/green]\n")
    
    for i, result in enumerate(results, 1):
        file_path = result.get("file", "Unknown")
        
        # Try to read the file and show the pattern
        try:
            with open(file_path, 'r') as f:
                content = f.read()
                
            # Find relevant section (simplified)
            lines = content.split('\n')
            start = max(0, result.get("line", 0) - 5)
            end = min(len(lines), start + 15)
            snippet = '\n'.join(lines[start:end])
            
            syntax = Syntax(
                snippet,
                "python",
                theme="monokai",
                line_numbers=True,
                start_line=start + 1
            )
            
            panel = Panel(
                syntax,
                title=f"Example {i}: {file_path}",
                expand=False
            )
            console.print(panel)
            
        except Exception as e:
            console.print(f"{i}. [cyan]{file_path}[/cyan]")


@cli.command()
@click.pass_obj
def watch(kg: KnowledgeGraphCLI):
    """Watch for real-time Knowledge Graph events (WebSocket)"""
    console.print("[yellow]Connecting to Knowledge Graph WebSocket...[/yellow]")
    console.print("[dim]Press Ctrl+C to stop[/dim]\n")
    
    import websocket
    import threading
    
    def on_message(ws, message):
        try:
            data = json.loads(message)
            event_type = data.get("type", "unknown")
            
            if event_type == "critical_change":
                console.print(f"[red]🚨 CRITICAL: {data.get('data', {}).get('file_path')}[/red]")
            elif event_type == "analysis_complete":
                console.print(f"[green]✅ Analysis complete: {data.get('file')}[/green]")
            else:
                console.print(f"[cyan]📡 {event_type}: {json.dumps(data, indent=2)}[/cyan]")
        except Exception as e:
            console.print(f"[dim]{message}[/dim]")
    
    def on_error(ws, error):
        console.print(f"[red]Error: {error}[/red]")
    
    def on_close(ws):
        console.print("[yellow]WebSocket closed[/yellow]")
    
    def on_open(ws):
        console.print("[green]Connected to Knowledge Graph[/green]\n")
    
    ws_url = kg.base_url.replace("http://", "ws://") + "/ws"
    ws = websocket.WebSocketApp(
        ws_url,
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )
    
    try:
        ws.run_forever()
    except KeyboardInterrupt:
        console.print("\n[yellow]Stopping watch...[/yellow]")


if __name__ == "__main__":
    cli()