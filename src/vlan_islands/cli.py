"""
Command-line interface for the VLAN Islands Detection tool.

Provides comprehensive CLI commands for analyzing network topologies,
generating reports, and interacting with the AI chatbot.
"""

import sys
import os
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt, Confirm
from rich.markdown import Markdown

from .parser import NetworkTopologyParser, NetworkParseError
from .analyzer import VLANIslandAnalyzer
from .reports import ReportGenerator
from .chatbot import NetworkChatbot
from .visualization import NetworkVisualizer

console = Console()


@click.group()
@click.version_option(version="1.0.0", prog_name="vlan-islands")
def main():
    """
    [*] VLAN Islands Detection and Troubleshooting Tool
    
    An AI-powered solution for analyzing network topologies and fixing VLAN connectivity issues.
    """
    pass


@main.command()
@click.argument('network_file', type=click.Path(exists=True, path_type=Path))
@click.option('--output', '-o', type=click.Path(path_type=Path), help='Output directory for reports')
@click.option('--format', '-f', 
              type=click.Choice(['json', 'csv', 'txt', 'all'], case_sensitive=False),
              default='txt', help='Report format')
@click.option('--quiet', '-q', is_flag=True, help='Suppress detailed output')
@click.option('--summary-only', '-s', is_flag=True, help='Show only summary table')
def analyze(network_file: Path, output: Optional[Path], format: str, quiet: bool, summary_only: bool):
    """
    Analyze network topology for VLAN islands.
    
    NETWORK_FILE: Path to the network topology JSON file
    """
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True
        ) as progress:
            
            # Load network topology
            task = progress.add_task("Loading network topology...", total=None)
            topology = NetworkTopologyParser.load_from_file(network_file)
            progress.update(task, description="[+] Network topology loaded")
            
            # Analyze VLANs
            progress.update(task, description="Analyzing VLAN islands...")
            analyzer = VLANIslandAnalyzer(topology)
            report = analyzer.analyze_all_vlans()
            progress.update(task, description="[+] Analysis complete")
        
        if not quiet:
            console.print(f"\n[bold blue]Network Analysis Complete[/bold blue]")
            console.print(f"Analyzed {len(report.vlan_results)} VLANs across {report.topology_summary['total_devices']} devices")
        
        # Display summary
        if summary_only:
            summary_table = ReportGenerator.generate_summary_table(report)
            console.print("\n[bold]VLAN Summary[/bold]")
            console.print(summary_table)
        elif not quiet:
            _display_analysis_results(report)
        
        # Generate reports
        if output:
            _generate_reports(report, output, format, quiet)
        
        # Show recommendations
        if not quiet and report.problematic_vlans:
            console.print("\n[!] [bold yellow]Recommendations[/bold yellow]")
            for rec in report.recommendations[:5]:  # Show first 5
                console.print(f"  {rec}")
            
            if len(report.recommendations) > 5:
                console.print(f"  ... and {len(report.recommendations) - 5} more recommendations")
            
            console.print(f"\n[*] [bold cyan]Try the interactive chatbot:[/bold cyan]")
            console.print(f"  vlan-islands chat {network_file}")
    
    except NetworkParseError as e:
        console.print(f"[X] [bold red]Network parsing error:[/bold red] {e}")
        sys.exit(1)
    except Exception as e:
        console.print(f"[X] [bold red]Analysis failed:[/bold red] {e}")
        sys.exit(1)


@main.command()
@click.argument('network_file', type=click.Path(exists=True, path_type=Path))
@click.option('--session-id', '-s', help='Resume existing chat session')
@click.option('--export-session', '-e', help='Export chat session to file')
def chat(network_file: Path, session_id: Optional[str], export_session: Optional[str]):
    """
    Start interactive AI chatbot for network troubleshooting.
    
    NETWORK_FILE: Path to the network topology JSON file
    """
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True
        ) as progress:
            
            task = progress.add_task("Initializing AI assistant...", total=None)
            
            # Load and analyze network
            topology = NetworkTopologyParser.load_from_file(network_file)
            analyzer = VLANIslandAnalyzer(topology)
            report = analyzer.analyze_all_vlans()
            
            # Initialize chatbot
            chatbot = NetworkChatbot(topology, report)
            
            # Create or resume session
            if session_id:
                if session_id not in chatbot.sessions:
                    console.print(f"[!] Session '{session_id}' not found, creating new session")
                    session_id = chatbot.create_session(session_id)
                else:
                    console.print(f"[>] Resuming session '{session_id}'")
            else:
                session_id = chatbot.create_session()
                console.print(f"[+] Created new session: {session_id}")
            
            progress.update(task, description="[+] AI assistant ready")
        
        # Welcome message
        console.print(Panel(
            chatbot.get_network_overview(),
            title="[*] Network Troubleshooting Assistant",
            border_style="cyan"
        ))
        
        console.print("\n[>] [bold]Chat Commands:[/bold]")
        console.print("  • Type 'help' for assistance")
        console.print("  • Type 'overview' for network summary")
        console.print("  • Type 'analyze VLAN_ID' to analyze specific VLAN")
        console.print("  • Type 'quit' or 'exit' to end session")
        console.print("  • Press Ctrl+C to exit\n")
        
        # Chat loop
        try:
            while True:
                user_input = Prompt.ask("[bold blue]You[/bold blue]").strip()
                
                if user_input.lower() in ['quit', 'exit', 'bye']:
                    break
                elif user_input.lower() == 'help':
                    console.print(chatbot.get_quick_help())
                    continue
                elif user_input.lower() == 'overview':
                    console.print(chatbot.get_network_overview())
                    continue
                elif user_input.lower().startswith('analyze '):
                    try:
                        vlan_id = int(user_input.split()[1])
                        analysis = chatbot.analyze_vlan_interactive(vlan_id)
                        console.print(Markdown(analysis))
                        continue
                    except (IndexError, ValueError):
                        console.print("[X] Usage: analyze <VLAN_ID>")
                        continue
                elif not user_input:
                    continue
                
                # Process with AI
                with console.status("[*] Thinking...", spinner="dots"):
                    response = chatbot.chat(session_id, user_input)
                
                console.print(f"[bold green]Assistant[/bold green]: {response}")
                console.print()
        
        except KeyboardInterrupt:
            console.print("\n\n[>] Chat session ended.")
        
        # Export session if requested
        if export_session:
            exported_file = chatbot.export_session(session_id, export_session)
            console.print(f"[>] Session exported to: {exported_file}")
        
        # Show session summary
        summary = chatbot.get_session_summary(session_id)
        console.print(f"\n[#] Session Summary: {summary['message_count']} messages exchanged")
    
    except NetworkParseError as e:
        console.print(f"[X] [bold red]Network parsing error:[/bold red] {e}")
        sys.exit(1)
    except Exception as e:
        console.print(f"[X] [bold red]Chatbot initialization failed:[/bold red] {e}")
        sys.exit(1)


@main.command()
@click.argument('network_file', type=click.Path(exists=True, path_type=Path))
@click.option('--vlan-id', '-v', type=int, help='Analyze specific VLAN')
@click.option('--output', '-o', type=click.Path(path_type=Path), help='Output file for visualization')
@click.option('--format', '-f', 
              type=click.Choice(['png', 'html', 'svg'], case_sensitive=False),
              default='html', help='Visualization format')
@click.option('--show-islands', '-i', is_flag=True, help='Highlight VLAN islands')
def visualize(network_file: Path, vlan_id: Optional[int], output: Optional[Path], format: str, show_islands: bool):
    """
    Generate network topology visualization.
    
    NETWORK_FILE: Path to the network topology JSON file
    """
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True
        ) as progress:
            
            task = progress.add_task("Loading network topology...", total=None)
            topology = NetworkTopologyParser.load_from_file(network_file)
            
            progress.update(task, description="Analyzing network...")
            analyzer = VLANIslandAnalyzer(topology)
            report = analyzer.analyze_all_vlans()
            
            progress.update(task, description="Generating visualization...")
            visualizer = NetworkVisualizer(topology, report)
            
            # Generate visualization
            if vlan_id:
                output_file = visualizer.create_vlan_visualization(vlan_id, output, format)
                console.print(f"🎨 VLAN {vlan_id} visualization saved to: {output_file}")
            else:
                output_file = visualizer.create_topology_visualization(output, format, highlight_islands=show_islands)
                console.print(f"🎨 Network topology visualization saved to: {output_file}")
        
        if format == 'html':
            if Confirm.ask("Open visualization in browser?"):
                import webbrowser
                webbrowser.open(f"file://{Path(output_file).absolute()}")
    
    except NetworkParseError as e:
        console.print(f"[X] [bold red]Network parsing error:[/bold red] {e}")
        sys.exit(1)
    except Exception as e:
        console.print(f"[X] [bold red]Visualization failed:[/bold red] {e}")
        sys.exit(1)


@main.command()
@click.argument('network_file', type=click.Path(exists=True, path_type=Path))
def validate(network_file: Path):
    """
    Validate network topology file.
    
    NETWORK_FILE: Path to the network topology JSON file
    """
    console.print(f"[bold]Validating network topology:[/bold] {network_file}")
    
    try:
        is_valid, errors = NetworkTopologyParser.validate_file(network_file)
        
        if is_valid:
            console.print("[+] [bold green]Network topology is valid![/bold green]")
            
            # Load and show summary
            topology = NetworkTopologyParser.load_from_file(network_file)
            summary = NetworkTopologyParser.get_topology_summary(topology)
            
            console.print(f"\n[#] [bold]Topology Summary:[/bold]")
            console.print(f"  • Devices: {summary['total_devices']}")
            console.print(f"  • Links: {summary['total_links']}")
            console.print(f"  • VLANs: {summary['total_vlans']}")
            
            if 'devices_per_location' in summary:
                console.print(f"  • Locations: {len(summary['devices_per_location'])}")
        else:
            console.print("[X] [bold red]Network topology validation failed![/bold red]")
            console.print("\n[!] [bold]Validation Errors:[/bold]")
            for i, error in enumerate(errors, 1):
                console.print(f"  {i}. {error}")
            sys.exit(1)
    
    except Exception as e:
        console.print(f"[X] [bold red]Validation error:[/bold red] {e}")
        sys.exit(1)


@main.command()
@click.argument('network_file', type=click.Path(exists=True, path_type=Path))
@click.option('--vlan-id', '-v', type=int, required=True, help='VLAN ID to analyze')
def vlan(network_file: Path, vlan_id: int):
    """
    Detailed analysis of a specific VLAN.
    
    NETWORK_FILE: Path to the network topology JSON file
    """
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True
        ) as progress:
            
            task = progress.add_task("Analyzing VLAN...", total=None)
            topology = NetworkTopologyParser.load_from_file(network_file)
            analyzer = VLANIslandAnalyzer(topology)
            result = analyzer.analyze_vlan(vlan_id)
            
            progress.update(task, description="[+] Analysis complete")
        
        if not result:
            console.print(f"[X] [bold red]VLAN {vlan_id} not found in topology[/bold red]")
            sys.exit(1)
        
        # Display VLAN analysis
        _display_vlan_details(result, analyzer)
    
    except NetworkParseError as e:
        console.print(f"[X] [bold red]Network parsing error:[/bold red] {e}")
        sys.exit(1)
    except Exception as e:
        console.print(f"[X] [bold red]VLAN analysis failed:[/bold red] {e}")
        sys.exit(1)


def _display_analysis_results(report):
    """Display analysis results in a formatted way."""
    # Status overview
    if report.problematic_vlans:
        status_color = "red"
        status_icon = "[!]"
        status_text = f"{len(report.problematic_vlans)} VLANs need attention"
    else:
        status_color = "green"
        status_icon = "[+]"
        status_text = "All VLANs are healthy"
    
    console.print(f"\n{status_icon} [bold {status_color}]{status_text}[/bold {status_color}]")
    
    # Problematic VLANs table
    if report.problematic_vlans:
        console.print(f"\n[!] [bold red]Problematic VLANs[/bold red]")
        
        table = Table(show_header=True, header_style="bold red")
        table.add_column("VLAN ID", style="cyan")
        table.add_column("Name", style="white")
        table.add_column("Islands", justify="center")
        table.add_column("Isolated Devices", justify="center")
        table.add_column("Fragmentation", justify="center")
        
        for result in sorted(report.problematic_vlans, key=lambda x: x.fragmentation_ratio, reverse=True):
            table.add_row(
                str(result.vlan_id),
                result.vlan_name,
                str(result.island_count),
                str(result.isolated_devices),
                f"{result.fragmentation_ratio:.1%}"
            )
        
        console.print(table)
    
    # Healthy VLANs summary
    if report.healthy_vlans:
        console.print(f"\n[+] [bold green]Healthy VLANs: {len(report.healthy_vlans)}[/bold green]")


def _display_vlan_details(result, analyzer):
    """Display detailed VLAN analysis."""
    console.print(f"\n[bold blue]VLAN {result.vlan_id} ({result.vlan_name}) Analysis[/bold blue]")
    
    if not result.has_islands:
        console.print("[+] [bold green]This VLAN is healthy with no connectivity issues[/bold green]")
        console.print(f"[#] Total devices: {result.total_devices}")
        return
    
    # Problem summary
    console.print(f"[!] [bold red]Connectivity Issues Detected[/bold red]")
    console.print(f"  • Islands: {result.island_count}")
    console.print(f"  • Isolated devices: {result.isolated_devices}")
    console.print(f"  • Fragmentation: {result.fragmentation_ratio:.1%}")
    
    # Islands table
    console.print(f"\n[>] [bold]Island Details[/bold]")
    
    table = Table(show_header=True)
    table.add_column("Island ID", style="cyan")
    table.add_column("Status", style="white")
    table.add_column("Size", justify="center")
    table.add_column("Devices")
    
    for island in result.islands:
        status = "[*] MAIN" if island.is_main_island else "[!] ISOLATED"
        devices_str = ", ".join(sorted(list(island.devices))[:3])
        if island.size > 3:
            devices_str += f" ... (+{island.size-3} more)"
        
        table.add_row(
            str(island.island_id),
            status,
            str(island.size),
            devices_str
        )
    
    console.print(table)
    
    # Connectivity suggestions
    suggestions = analyzer.get_island_connectivity_suggestions(result.vlan_id)
    if suggestions.get("connection_opportunities"):
        console.print(f"\n[!] [bold yellow]Connection Opportunities[/bold yellow]")
        for i, opp in enumerate(suggestions["connection_opportunities"][:3], 1):
            console.print(f"  {i}. Bridge island {opp['isolated_island']['id']} "
                         f"({opp['isolated_island']['size']} devices) to main island")


def _generate_reports(report, output_dir: Path, format: str, quiet: bool):
    """Generate and save reports."""
    if not quiet:
        console.print(f"\n📄 [bold]Generating reports...[/bold]")
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    if format == 'all':
        exported = ReportGenerator.export_all_formats(report, output_dir)
        if not quiet:
            for fmt, path in exported.items():
                console.print(f"  • {fmt.upper()}: {path}")
    else:
        if format == 'json':
            path = output_dir / "analysis_report.json"
            ReportGenerator.generate_json_report(report, path)
        elif format == 'csv':
            path = output_dir / "analysis_report.csv"
            ReportGenerator.generate_csv_report(report, path)
        elif format == 'txt':
            path = output_dir / "analysis_report.txt"
            ReportGenerator.generate_text_report(report, path)
        
        if not quiet:
            console.print(f"  • Report saved: {path}")


if __name__ == '__main__':
    main()
