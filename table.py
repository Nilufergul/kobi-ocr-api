# table.py
import re
from typing import List, Dict, Any


def _find_markdown_tables(text: str) -> List[re.Match]:
    """
    Metindeki markdown benzeri '|' içeren tabloları bulur.
    Hem '| col1 | col2 |' hem de 'col1 | col2 | col3' formatlarını kapsar.
    """
    pattern = r"((?:^[^\n]*\|[^\n]*\|[^\n]*$\n?)+)"
    return list(re.finditer(pattern, text, flags=re.MULTILINE))


def _guess_title(full_text: str, table_start_idx: int) -> str | None:
    """
    Tablo bloğunun hemen üstündeki son anlamlı satırı 'başlık' olarak tahmin eder.
    Örn: 'AKTIF', 'PASIF', 'GELIR TABLOSU' gibi.
    """
    lines_before = full_text[:table_start_idx].splitlines()

    for line in reversed(lines_before):
        line = line.strip()
        if not line:
            continue
        if "|" in line:
            # pipe içeren satır muhtemelen başka bir tablonun satırı
            continue
        if len(line) > 120:
            # çok uzun açıklamaları başlık sayma
            continue
        return line

    return None


def _split_row(line: str) -> list[str]:
    return [c.strip() for c in line.strip("|").split("|")]


def _is_align_row(cells: list[str]) -> bool:
    """
    ':--', '---', ':---:' gibi hizalama satırlarını tespit eder.
    """
    if not cells:
        return False
    joined = "".join(cells).replace(":", "").replace("-", "").strip()
    return joined == ""


def _parse_markdown_table(block: str) -> tuple[list[str], list[dict[str, str]], str | None]:
    """
    Tek bir markdown tablo bloğunu:
    - varsa tablo içindeki başlık (internal title)
    - kolon listesine
    - satır listesine (dict olarak)

    çevirir.
    """
    lines = [l.strip() for l in block.splitlines() if l.strip()]
    if not lines:
        return [], [], None

    # 1) Tablo içi başlık satırı (ör: '| KURUMA BAĞLI ... |  |  |')
    internal_title: str | None = None
    first_cells = _split_row(lines[0])
    non_empty_first = [c for c in first_cells if c]

    # sadece 1 dolu hücre + en az 2 sütun → tablo içi başlık varsay
    if len(non_empty_first) == 1 and len(first_cells) >= 2:
        internal_title = non_empty_first[0]
        lines = lines[1:]  # bu satırı tablodan çıkar

    if not lines:
        return [], [], internal_title

    # 2) Header satırını belirle
    #    - Eğer ilk satır align satırıysa → header = ikinci satır
    #    - Yoksa header = ilk satır, ikinci satır align ise onu atla
    first_cells = _split_row(lines[0])
    if _is_align_row(first_cells):
        # Örneğin:
        # | KURUMA BAĞLI ... |
        # | :--: | :--: | :--: |
        # | Türü |  | Sayısı |
        # internal title çıkarıldıktan sonra ilk satır align satırı olur
        if len(lines) < 2:
            return [], [], internal_title
        header = _split_row(lines[1])
        data_start = 2
    else:
        header = first_cells
        data_start = 1
        # Klasik markdown: header + align satırı
        if len(lines) > 1 and _is_align_row(_split_row(lines[1])):
            data_start = 2

    # 3) Veri satırları
    rows: list[dict[str, str]] = []
    for line in lines[data_start:]:
        cells = _split_row(line)
        row = dict(zip(header, cells))
        rows.append(row)

    return header, rows, internal_title


def extract_all_tables_from_ocr_text(text: str) -> List[Dict[str, Any]]:
    """
    OCR'den gelen uzun markdown/text içinden
    - bütün tabloları bulur
    - her biri için title, columns, rows döner.
    """
    tables: list[dict[str, Any]] = []

    for match in _find_markdown_tables(text):
        block = match.group(1)
        columns, rows, internal_title = _parse_markdown_table(block)

        if not columns:
            continue

        title = internal_title or _guess_title(text, match.start())

        tables.append(
            {
                "title": title,
                "columns": columns,
                "rows": rows,
            }
        )

    return tables
