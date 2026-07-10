import typer
from rich.console import Console

from neutron.langmath.config import settings

console = Console()
app = typer.Typer(help="LangMath Second Brain CLI")


@app.command()
def learn(text: str = typer.Argument(..., help="Text to save to your second brain")):
    """
    Save new knowledge into the Second Brain.
    """
    from neutron.langmath.core.rag import ingest_text

    console.print("[bold green]Ingesting to brain...[/bold green]")
    num_chunks = ingest_text(text)
    console.print(f"✨ Successfully vectorized into {num_chunks} chunks.")


@app.command()
def ask(query: str = typer.Argument(..., help="Question to ask your brain")):
    """
    Ask a question based on your stored knowledge.
    """
    from neutron.langmath.core.retrieval import ask_oracle

    console.print(
        f"[bold blue]Consulting oracle (Provider: {settings.llm_provider})...[/bold blue]"
    )
    console.print(f"User Query: {query}")

    try:
        result = ask_oracle(query)
        console.print("\n[bold cyan]Answer:[/bold cyan]")
        console.print(result["answer"])
        console.print("\n[bold magenta]Sources Used:[/bold magenta]")
        for i, source in enumerate(result["sources"]):
            console.print(f"[magenta][{i+1}][/magenta] {source[:100]}...")
    except Exception as e:
        console.print(f"[bold red]Error querying the oracle:[/bold red] {str(e)}")


@app.command()
def status():
    """
    Show detailed status of the knowledge base.
    """
    from rich.panel import Panel
    from rich.table import Table

    from neutron.langmath.core.rag import get_collection_stats

    stats = get_collection_stats()

    table = Table(title="Knowledge Base Statistics")
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="magenta")

    table.add_row("Total Chunks", str(stats["count"]))
    table.add_row("Unique Sources", ", ".join(stats["sources"]) or "None")
    table.add_row("Storage Path", settings.chroma_db_dir)

    console.print(table)

    if stats["count"] > 0:
        sample_doc = stats["sample"]["documents"][0]
        sample_meta = stats["sample"]["metadatas"][0]

        console.print("\n[bold yellow]Sample Knowledge Chunk:[/bold yellow]")
        console.print(Panel(sample_doc, title=f"Source: {sample_meta['source']}"))
    else:
        console.print(
            "\n[yellow]Your second brain is still empty. Use 'langmath learn' to add knowledge![/yellow]"
        )


@app.command()
def sync(path: str = typer.Argument(..., help="Path to a directory or file to index")):
    """
    Recursively index all Markdown files in a directory.
    """
    import os

    from rich.progress import Progress

    from neutron.langmath.core.rag import ingest_text

    if not os.path.exists(path):
        console.print(f"[bold red]Error:[/bold red] Path '{path}' does not exist.")
        raise typer.Exit(1)

    files_to_index = []
    if os.path.isfile(path):
        if path.endswith((".md", ".txt")):
            files_to_index.append(path)
    else:
        for root, _, files in os.walk(path):
            for file in files:
                if file.endswith((".md", ".txt")):
                    files_to_index.append(os.path.join(root, file))

    if not files_to_index:
        console.print("[yellow]No supported files (.md, .txt) found to index.[/yellow]")
        return

    console.print(f"🔍 Found [bold]{len(files_to_index)}[/bold] files to index.")

    with Progress() as progress:
        task = progress.add_task("[cyan]Indexing...", total=len(files_to_index))

        total_chunks = 0
        for file_path in files_to_index:
            try:
                with open(file_path, encoding="utf-8") as f:
                    content = f.read()
                    chunks = ingest_text(content, source=file_path)
                    total_chunks += chunks
            except Exception as e:
                console.print(f"[red]Error indexing {file_path}: {e}[/red]")

            progress.update(task, advance=1)

    console.print(
        f"✨ Successfully indexed [bold]{total_chunks}[/bold] chunks from {len(files_to_index)} files."
    )


@app.command()
def info():
    """
    Show current configuration.
    """
    console.print("[bold cyan]LangMath Second Brain Config[/bold cyan]")
    console.print(f"Provider: {settings.llm_provider}")
    console.print(f"DB Directory: {settings.chroma_db_dir}")
    if settings.llm_provider == "nvidia":
        console.print(f"Model: {settings.nvidia_model}")
        has_key = bool(settings.nvidia_api_key)
        console.print(f"API Key Configured: {'[green]Yes[/green]' if has_key else '[red]No[/red]'}")
    else:
        console.print(f"Llama.cpp URL: {settings.llama_cpp_base_url}")


if __name__ == "__main__":
    app()
