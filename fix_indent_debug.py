from pathlib import Path
text = Path('sustainable_forex_journal.py').read_text(encoding='utf-8').splitlines()
for i in range(2337,2490):
    line = text[i-1]
    indent = len(line) - len(line.lstrip(' '))
    print(f"{i:4} {indent:2} {repr(line)}")
