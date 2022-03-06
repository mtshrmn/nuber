from .reader import Reader
import click
import signal

__version__ = '1.0.1'

@click.command()
@click.argument("book", type=click.Path(exists=True))
@click.option("-c", "--config", type=click.Path(exists=True))
def main(book, config):
    reader = Reader(click.format_filename(book), config_path=config)

    def signal_handler(*_):
        reader.action_quit(None)

    signal.signal(signal.SIGHUP, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    reader.loop() # type: ignore
