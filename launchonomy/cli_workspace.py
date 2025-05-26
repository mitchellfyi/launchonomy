#!/usr/bin/env python3
"""
Launchonomy Workspace Management CLI

Provides command-line tools for managing mission workspaces including:
- Creating and configuring workspaces
- Listing and inspecting workspace contents
- Managing workspace assets and state
- Archiving and restoring workspaces
- Workspace analytics and reporting
"""

import os
import sys
import json
import click
from pathlib import Path
from typing import Optional, List, Dict, Any
from rich.console import Console
from rich.table import Table
from rich.tree import Tree
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt, Confirm
from datetime import datetime

# Add the parent directory to the path so we can import launchonomy modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from launchonomy.core.workspace_manager import WorkspaceManager, WorkspaceConfig
from launchonomy.core.mission_manager import MissionManager

console = Console()

@click.group()
@click.option('--base-dir', default='.launchonomy', help='Base directory for workspaces')
@click.pass_context
def workspace(ctx, base_dir):
    """Launchonomy Workspace Management CLI"""
    ctx.ensure_object(dict)
    ctx.obj['base_dir'] = base_dir
    ctx.obj['workspace_manager'] = WorkspaceManager(base_dir)

@workspace.command()
@click.argument('mission_name')
@click.option('--mission-id', help='Custom mission ID (auto-generated if not provided)')
@click.option('--description', help='Mission description')
@click.option('--tags', help='Comma-separated tags')
@click.pass_context
def create(ctx, mission_name: str, mission_id: Optional[str], description: Optional[str], tags: Optional[str]):
    """Create a new mission workspace"""
    wm: WorkspaceManager = ctx.obj['workspace_manager']
    
    # Generate mission ID if not provided
    if not mission_id:
        import re
        safe_name = re.sub(r'\W+', '_', mission_name.lower())
        mission_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_mission_{safe_name}"
    
    # Parse tags
    tag_list = [tag.strip() for tag in tags.split(',')] if tags else []
    
    # Use mission_name as description if not provided
    overall_mission = description or mission_name
    
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Creating workspace...", total=None)
            
            config = wm.create_workspace(
                mission_id=mission_id,
                mission_name=mission_name,
                overall_mission=overall_mission,
                tags=tag_list
            )
            
            progress.update(task, description="Workspace created successfully!")
        
        console.print(Panel.fit(
            f"[bold green]✅ Workspace Created Successfully![/bold green]\n\n"
            f"[cyan]Mission ID:[/cyan] {config.mission_id}\n"
            f"[cyan]Mission Name:[/cyan] {config.mission_name}\n"
            f"[cyan]Workspace Path:[/cyan] {config.workspace_path}\n"
            f"[cyan]Created:[/cyan] {config.created_at}\n"
            f"[cyan]Tags:[/cyan] {', '.join(config.tags) if config.tags else 'None'}",
            title="Workspace Created"
        ))
        
        # Show directory structure
        _show_workspace_structure(config.workspace_path)
        
    except Exception as e:
        console.print(f"[red]❌ Error creating workspace: {e}[/red]")
        sys.exit(1)

@workspace.command()
@click.option('--status', help='Filter by status (active, paused, completed, archived)')
@click.option('--tag', help='Filter by tag')
@click.option('--limit', default=20, help='Maximum number of workspaces to show')
@click.pass_context
def list(ctx, status: Optional[str], tag: Optional[str], limit: int):
    """List all mission workspaces"""
    wm: WorkspaceManager = ctx.obj['workspace_manager']
    
    try:
        workspaces = wm.list_workspaces(status_filter=status)
        
        # Filter by tag if specified
        if tag:
            workspaces = [ws for ws in workspaces if tag in ws.tags]
        
        # Limit results
        workspaces = workspaces[:limit]
        
        if not workspaces:
            console.print("[yellow]No workspaces found matching the criteria.[/yellow]")
            return
        
        # Create table
        table = Table(title=f"Mission Workspaces ({len(workspaces)} found)")
        table.add_column("Mission ID", style="cyan", no_wrap=True)
        table.add_column("Name", style="green")
        table.add_column("Status", style="yellow")
        table.add_column("Created", style="blue")
        table.add_column("Tags", style="magenta")
        table.add_column("Assets", style="white")
        
        for ws in workspaces:
            # Get workspace summary for asset count
            summary = wm.get_workspace_summary(ws.mission_id)
            asset_count = "N/A"
            if summary:
                total_assets = summary.get('total_assets', 0)
                total_agents = summary.get('total_agents', 0)
                total_tools = summary.get('total_tools', 0)
                asset_count = f"{total_assets} ({total_agents}A, {total_tools}T)"
            
            # Format creation date
            try:
                created_dt = datetime.fromisoformat(ws.created_at.replace('Z', '+00:00'))
                created_str = created_dt.strftime('%Y-%m-%d %H:%M')
            except:
                created_str = ws.created_at[:16]
            
            table.add_row(
                ws.mission_id[:30] + "..." if len(ws.mission_id) > 30 else ws.mission_id,
                ws.mission_name[:25] + "..." if len(ws.mission_name) > 25 else ws.mission_name,
                ws.status,
                created_str,
                ", ".join(ws.tags[:2]) + ("..." if len(ws.tags) > 2 else ""),
                asset_count
            )
        
        console.print(table)
        
    except Exception as e:
        console.print(f"[red]❌ Error listing workspaces: {e}[/red]")
        sys.exit(1)

@workspace.command()
@click.argument('mission_id')
@click.option('--show-assets', is_flag=True, help='Show detailed asset information')
@click.option('--show-logs', is_flag=True, help='Show recent log entries')
@click.pass_context
def inspect(ctx, mission_id: str, show_assets: bool, show_logs: bool):
    """Inspect a specific workspace in detail"""
    wm: WorkspaceManager = ctx.obj['workspace_manager']
    
    try:
        config = wm.get_workspace(mission_id)
        if not config:
            console.print(f"[red]❌ Workspace not found: {mission_id}[/red]")
            sys.exit(1)
        
        # Get workspace summary
        summary = wm.get_workspace_summary(mission_id)
        
        # Display workspace information
        console.print(Panel.fit(
            f"[bold cyan]Mission Workspace Details[/bold cyan]\n\n"
            f"[cyan]Mission ID:[/cyan] {config.mission_id}\n"
            f"[cyan]Mission Name:[/cyan] {config.mission_name}\n"
            f"[cyan]Description:[/cyan] {config.overall_mission}\n"
            f"[cyan]Status:[/cyan] {config.status}\n"
            f"[cyan]Created:[/cyan] {config.created_at}\n"
            f"[cyan]Last Updated:[/cyan] {config.last_updated or 'Never'}\n"
            f"[cyan]Workspace Path:[/cyan] {config.workspace_path}\n"
            f"[cyan]Tags:[/cyan] {', '.join(config.tags) if config.tags else 'None'}",
            title=f"Workspace: {mission_id}"
        ))
        
        if summary:
            # Display summary statistics
            stats_table = Table(title="Workspace Statistics")
            stats_table.add_column("Category", style="cyan")
            stats_table.add_column("Count", style="green")
            stats_table.add_column("Details", style="yellow")
            
            stats_table.add_row("Agents", str(summary.get('total_agents', 0)), 
                              f"{len(summary.get('agents', {}))} unique agents")
            stats_table.add_row("Tools", str(summary.get('total_tools', 0)), 
                              f"{len(summary.get('tools', {}))} unique tools")
            stats_table.add_row("Assets", str(summary.get('total_assets', 0)), 
                              f"{summary.get('storage_size_mb', 0):.1f} MB total")
            stats_table.add_row("Log Files", str(summary.get('total_logs', 0)), 
                              f"Across {len(summary.get('log_categories', []))} categories")
            
            console.print(stats_table)
            
            # Show recent assets
            if summary.get('recent_assets'):
                console.print("\n[bold]Recent Assets:[/bold]")
                for asset in summary['recent_assets'][:5]:
                    console.print(f"  • {asset['name']} ({asset['type']}) - {asset['created_at'][:16]}")
        
        # Show directory structure
        console.print("\n[bold]Directory Structure:[/bold]")
        _show_workspace_structure(config.workspace_path)
        
        # Show detailed assets if requested
        if show_assets and summary:
            _show_detailed_assets(summary)
        
        # Show recent logs if requested
        if show_logs:
            _show_recent_logs(config.workspace_path)
            
    except Exception as e:
        console.print(f"[red]❌ Error inspecting workspace: {e}[/red]")
        sys.exit(1)

@workspace.command()
@click.argument('mission_id')
@click.option('--archive-path', help='Custom archive path (default: archives/)')
@click.option('--force', is_flag=True, help='Force archive without confirmation')
@click.pass_context
def archive(ctx, mission_id: str, archive_path: Optional[str], force: bool):
    """Archive a mission workspace"""
    wm: WorkspaceManager = ctx.obj['workspace_manager']
    
    try:
        config = wm.get_workspace(mission_id)
        if not config:
            console.print(f"[red]❌ Workspace not found: {mission_id}[/red]")
            sys.exit(1)
        
        if not force:
            console.print(f"[yellow]About to archive workspace:[/yellow] {config.mission_name}")
            console.print(f"[yellow]Path:[/yellow] {config.workspace_path}")
            
            if not Confirm.ask("Are you sure you want to archive this workspace?"):
                console.print("[yellow]Archive cancelled.[/yellow]")
                return
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Archiving workspace...", total=None)
            
            success = wm.archive_workspace(mission_id, archive_path)
            
            if success:
                progress.update(task, description="Workspace archived successfully!")
                console.print(f"[green]✅ Workspace archived successfully![/green]")
            else:
                console.print(f"[red]❌ Failed to archive workspace[/red]")
                sys.exit(1)
                
    except Exception as e:
        console.print(f"[red]❌ Error archiving workspace: {e}[/red]")
        sys.exit(1)

@workspace.command()
@click.argument('mission_id')
@click.option('--status', type=click.Choice(['active', 'paused', 'completed', 'archived']), 
              help='New status for the workspace')
@click.option('--add-tag', help='Add a tag to the workspace')
@click.option('--remove-tag', help='Remove a tag from the workspace')
@click.pass_context
def update(ctx, mission_id: str, status: Optional[str], add_tag: Optional[str], remove_tag: Optional[str]):
    """Update workspace configuration"""
    wm: WorkspaceManager = ctx.obj['workspace_manager']
    
    try:
        config = wm.get_workspace(mission_id)
        if not config:
            console.print(f"[red]❌ Workspace not found: {mission_id}[/red]")
            sys.exit(1)
        
        changes_made = False
        
        # Update status
        if status and status != config.status:
            config.status = status
            changes_made = True
            console.print(f"[green]✅ Status updated to: {status}[/green]")
        
        # Add tag
        if add_tag and add_tag not in config.tags:
            config.tags.append(add_tag)
            changes_made = True
            console.print(f"[green]✅ Added tag: {add_tag}[/green]")
        
        # Remove tag
        if remove_tag and remove_tag in config.tags:
            config.tags.remove(remove_tag)
            changes_made = True
            console.print(f"[green]✅ Removed tag: {remove_tag}[/green]")
        
        if changes_made:
            # Save updated config
            config.last_updated = datetime.now().isoformat()
            wm._save_workspace_config(config)
            console.print(f"[green]✅ Workspace configuration updated![/green]")
        else:
            console.print(f"[yellow]No changes made to workspace configuration.[/yellow]")
            
    except Exception as e:
        console.print(f"[red]❌ Error updating workspace: {e}[/red]")
        sys.exit(1)

@workspace.command()
@click.pass_context
def status(ctx):
    """Show overall workspace system status"""
    wm: WorkspaceManager = ctx.obj['workspace_manager']
    
    try:
        workspaces = wm.list_workspaces()
        
        # Calculate statistics
        total_workspaces = len(workspaces)
        status_counts = {}
        tag_counts = {}
        total_size = 0.0
        
        for ws in workspaces:
            # Count by status
            status_counts[ws.status] = status_counts.get(ws.status, 0) + 1
            
            # Count tags
            for tag in ws.tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
            
            # Calculate total size
            summary = wm.get_workspace_summary(ws.mission_id)
            if summary:
                total_size += summary.get('storage_size_mb', 0)
        
        # Display system status
        console.print(Panel.fit(
            f"[bold cyan]Workspace System Status[/bold cyan]\n\n"
            f"[cyan]Base Directory:[/cyan] {wm.base_dir}\n"
            f"[cyan]Total Workspaces:[/cyan] {total_workspaces}\n"
            f"[cyan]Total Storage:[/cyan] {total_size:.1f} MB\n"
            f"[cyan]Current Workspace:[/cyan] {wm.current_workspace or 'None'}",
            title="System Overview"
        ))
        
        # Status breakdown
        if status_counts:
            status_table = Table(title="Workspaces by Status")
            status_table.add_column("Status", style="cyan")
            status_table.add_column("Count", style="green")
            status_table.add_column("Percentage", style="yellow")
            
            for status, count in sorted(status_counts.items()):
                percentage = (count / total_workspaces) * 100
                status_table.add_row(status, str(count), f"{percentage:.1f}%")
            
            console.print(status_table)
        
        # Top tags
        if tag_counts:
            console.print("\n[bold]Most Common Tags:[/bold]")
            sorted_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)
            for tag, count in sorted_tags[:5]:
                console.print(f"  • {tag}: {count} workspace{'s' if count != 1 else ''}")
                
    except Exception as e:
        console.print(f"[red]❌ Error getting system status: {e}[/red]")
        sys.exit(1)

def _show_workspace_structure(workspace_path: str):
    """Show the directory structure of a workspace"""
    try:
        if not workspace_path:
            console.print("[red]No workspace path provided[/red]")
            return
            
        workspace_dir = Path(workspace_path)
        
        if not workspace_dir.exists():
            console.print(f"[red]Workspace directory does not exist: {workspace_path}[/red]")
            return
        
        tree = Tree(f"📁 {workspace_dir.name}")
        
        # Add main directories and files
        for item in sorted(workspace_dir.iterdir()):
            if item.is_dir():
                # Count items in directory
                try:
                    item_count = len(list(item.iterdir()))
                    if item_count == 0:
                        tree.add(f"📁 {item.name}/ [dim](empty)[/dim]")
                    else:
                        tree.add(f"📁 {item.name}/ [dim]({item_count} items)[/dim]")
                except PermissionError:
                    tree.add(f"📁 {item.name}/ [red](permission denied)[/red]")
                except Exception:
                    tree.add(f"📁 {item.name}/")
            else:
                tree.add(f"📄 {item.name}")
        
        console.print(tree)
        
    except Exception as e:
        console.print(f"[red]Error showing directory structure: {str(e)}[/red]")

def _show_detailed_assets(summary: Dict[str, Any]):
    """Show detailed asset information"""
    console.print("\n[bold]Detailed Assets:[/bold]")
    
    # Agents
    agents = summary.get('agents', {})
    if agents:
        console.print("\n[cyan]Agents:[/cyan]")
        for agent_name, agent_info in agents.items():
            console.print(f"  • {agent_name}: {agent_info.get('description', 'No description')}")
    
    # Tools
    tools = summary.get('tools', {})
    if tools:
        console.print("\n[cyan]Tools:[/cyan]")
        for tool_name, tool_info in tools.items():
            console.print(f"  • {tool_name}: {tool_info.get('description', 'No description')}")
    
    # Recent files
    recent_assets = summary.get('recent_assets', [])
    if recent_assets:
        console.print("\n[cyan]Recent Assets:[/cyan]")
        for asset in recent_assets[:10]:
            console.print(f"  • {asset['name']} ({asset['type']}) - {asset['created_at'][:16]}")

def _show_recent_logs(workspace_path: str):
    """Show recent log entries"""
    console.print("\n[bold]Recent Logs:[/bold]")
    
    logs_dir = Path(workspace_path) / "logs"
    if not logs_dir.exists():
        console.print("  No logs directory found")
        return
    
    try:
        # Find recent log files
        log_files = []
        for log_file in logs_dir.rglob("*.json"):
            if log_file.is_file():
                stat = log_file.stat()
                log_files.append((log_file, stat.st_mtime))
        
        # Sort by modification time (newest first)
        log_files.sort(key=lambda x: x[1], reverse=True)
        
        # Show first 5 log files
        for log_file, mtime in log_files[:5]:
            relative_path = log_file.relative_to(logs_dir)
            mod_time = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M')
            console.print(f"  • {relative_path} - {mod_time}")
            
    except Exception as e:
        console.print(f"  [red]Error reading logs: {e}[/red]")

if __name__ == '__main__':
    workspace() 