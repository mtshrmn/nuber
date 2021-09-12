from .reader import Reader
import click

__version__ = '0.1.0'

@click.command()
@click.argument("book", type=click.Path(exists=True))
def main(book):
    reader = Reader(click.format_filename(book))

    reader.loop() # type: ignore
