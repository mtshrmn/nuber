from .nuber import Reader

__version__ = '0.1.0'

def main():
    reader = Reader("/home/suerflowz/documents/literature/86--EIGHTY-SIX [Yen Press] [LuCaZ]/86--EIGHTY-SIX v01 [Yen Press] [LuCaZ].epub")

    reader.loop()
