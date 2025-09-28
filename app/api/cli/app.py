"""CLI interface for AI Мага using Typer."""

import asyncio
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from app.core.config import settings
from app.core.di import init_container
from app.core.logging import configure_logging
from app.services.llm.yandex_gpt import yandex_gpt
from app.services.voice.audio_io import audio_io

console = Console()
app = typer.Typer(
    name="ai-maga",
    help="AI Мага - голосовой ассистент",
    add_completion=False,
)


@app.callback()
def main():
    """AI Мага CLI."""
    configure_logging()
    init_container()


@app.command()
def chat(
    message: str = typer.Argument(..., help="Message to send to AI"),
    interactive: bool = typer.Option(False, "--interactive", "-i", help="Start interactive chat"),
):
    """Chat with AI Мага."""
    async def chat_async():
        if interactive:
            console.print("[bold green]AI Мага Interactive Chat[/bold green]")
            console.print("Type 'exit' or 'quit' to exit")
            console.print("-" * 50)

            conversation = []

            while True:
                try:
                    user_input = console.input("[bold blue]You:[/bold blue] ")
                    if user_input.lower() in ['exit', 'quit']:
                        break

                    with console.status("Thinking..."):
                        response = await yandex_gpt.chat(user_input, conversation)

                    conversation.extend([
                        {"role": "user", "content": user_input},
                        {"role": "assistant", "content": response}
                    ])

                    console.print(f"[bold green]AI Мага:[/bold green] {response}")
                    console.print()

                except KeyboardInterrupt:
                    break
                except Exception as e:
                    console.print(f"[red]Error: {e}[/red]")
                    break
        else:
            with console.status("Thinking..."):
                response = await yandex_gpt.chat(message)

            console.print(f"[bold green]AI Мага:[/bold green] {response}")

    asyncio.run(chat_async())


@app.command()
def voice_test():
    """Test voice input/output capabilities."""
    async def voice_test_async():
        try:
            console.print("[bold green]AI Мага Voice Test[/bold green]")

            # Initialize audio
            audio_io.initialize()

            # List devices
            devices = audio_io.get_devices()
            console.print(f"Found {len(devices)} audio devices:")

            table = Table("Index", "Name", "Input", "Output")
            for device in devices[:10]:  # Show first 10
                table.add_row(
                    str(device.index),
                    device.name[:50],
                    "✓" if device.is_input_device else "✗",
                    "✓" if device.is_output_device else "✗",
                )
            console.print(table)

            # Test input device
            try:
                audio_io.set_input_device(settings.audio_input_device)
                console.print(f"[green]Input device:[/green] {audio_io.input_device_name}")
            except Exception as e:
                console.print(f"[red]Input device error:[/red] {e}")

            # Test output device
            try:
                audio_io.set_output_device(settings.audio_output_device)
                console.print(f"[green]Output device:[/green] {audio_io.output_device_name}")
            except Exception as e:
                console.print(f"[red]Output device error:[/red] {e}")

            audio_io.terminate()
            console.print("[green]Voice test completed[/green]")

        except Exception as e:
            console.print(f"[red]Voice test failed: {e}[/red]")

    asyncio.run(voice_test_async())


@app.command()
def status():
    """Show system status."""
    console.print("[bold green]AI Мага Status[/bold green]")

    table = Table("Component", "Status", "Details")
    table.add_row("Environment", settings.app_env, f"Log level: {settings.log_level}")
    table.add_row("Database", "Unknown", f"DSN: {'configured' if settings.postgres_dsn else 'not configured'}")
    table.add_row("Redis", "Unknown", f"URL: {'configured' if settings.redis_url else 'not configured'}")
    table.add_row("Yandex Cloud", "Configured" if settings.yc_oauth_token else "Not configured", f"Folder: {settings.yc_folder_id}")
    table.add_row("Telegram", "Configured" if settings.tg_bot_token else "Not configured", f"Users: {len(settings.tg_allowed_user_ids)}")
    table.add_row("HH.ru", "Configured" if settings.hh_api_token else "Not configured", "API ready")
    table.add_row("Voice", "Unknown", f"Hotword: {settings.hotword}")

    console.print(table)


@app.command()
def config():
    """Show current configuration (without secrets)."""
    console.print("[bold green]AI Мага Configuration[/bold green]")

    # Safe config values (no secrets)
    safe_config = {
        "app_env": settings.app_env,
        "log_level": settings.log_level,
        "redis_url": "***" if settings.redis_url else None,
        "yc_folder_id": settings.yc_folder_id,
        "yandex_gpt_model": settings.yandex_gpt_model,
        "yandex_stt_model": settings.yandex_stt_model,
        "yandex_tts_voice": settings.yandex_tts_voice,
        "yandex_vision_ocr_model": settings.yandex_vision_ocr_model,
        "hotword": settings.hotword,
        "voice_pipeline_timeout": settings.voice_pipeline_timeout,
        "llm_max_tokens": settings.llm_max_tokens,
        "llm_temperature": settings.llm_temperature,
        "audio_input_device": settings.audio_input_device,
        "audio_output_device": settings.audio_output_device,
        "metrics_port": settings.metrics_port,
    }

    table = Table("Setting", "Value")
    for key, value in safe_config.items():
        table.add_row(key, str(value))

    console.print(table)


@app.command()
def version():
    """Show version information."""
    from app import __version__
    console.print(f"AI Мага v{__version__}")


if __name__ == "__main__":
    app()
