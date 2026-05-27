#!/usr/bin/env python3
"""Convert a tab-separated inventory export into a CSV suitable for `manage.py mark_concluse`.

Usage examples:
  python scripts/convert_to_mark_concluse.py -i preparazioni_raw.tsv -o preparazioni_to_import.csv
  python scripts/convert_to_mark_concluse.py --help

The script is forgiving: it detects tabs vs commas, removes parenthetical codes from the `Utente` column
and attempts to extract surname / name, finds a device code in the `Nome` or `Cespite` columns and
writes the target CSV header used by `mark_concluse` (minimal compatible set by default).
"""
import csv
import re
import argparse
import datetime
from pathlib import Path


MINIMAL_HEADER = [
    'tipo_richiesta',
    'categoria',
    'nome_nuovo_utente',
    'cognome_nuovo_utente',
    'data_ingresso',
    'dipartimento_nuovo_utente',
    'tipo_contratto_nuovo_utente',
    'dispositivo_nuovo_hostname',
    'tipologia_pc_richiesta',
    'data_pianificazione',
    'data_assegnazione',
    'tecnico_username',
    'luogo_intervento',
]

FULL_HEADER = [
    'tipo_richiesta','categoria','nome_nuovo_utente','cognome_nuovo_utente','data_ingresso',
    'dipartimento_nuovo_utente','tipo_contratto_nuovo_utente','dispositivo_nuovo_hostname',
    'dispositivo_vecchio_hostname','utente_vecchio_nome','utente_vecchio_cognome','ticket_helpdesk',
    'tipologia_pc_richiesta','note_software','data_pianificazione','data_assegnazione','tecnico_username','luogo_intervento'
]


def parse_args():
    p = argparse.ArgumentParser(description='Convert tab-separated export to mark_concluse CSV')
    p.add_argument('-i', '--input', default='preparazioni_raw.tsv', help='Input file (tab- or comma-separated)')
    p.add_argument('-o', '--output', default='preparazioni_to_import.csv', help='Output CSV file')
    p.add_argument('--delimiter', default=None, help='Force input delimiter (e.g. "\t" or ",")')
    p.add_argument('--tipo', default='Sostituzione', help='Default valore per `tipo_richiesta`')
    p.add_argument('--categoria', default='Standard', help='Default valore per `categoria`')
    p.add_argument('--contratto', default='Interno', help='Default valore per `tipo_contratto_nuovo_utente`')
    p.add_argument('--full', action='store_true', help='Write the full header (compatible with mark_concluse)')
    return p.parse_args()


def strip_paren(s: str) -> str:
    if not s:
        return ''
    return re.sub(r"\(.*?\)", "", s).strip()


def split_name(utente: str):
    """Try to extract `nome` and `cognome` from the `Utente` column.

    Heuristics:
    - remove parenthetical codes
    - look for the last comma: text like "Cognome, Nome"
    - otherwise split on whitespace and take first token as cognome
    """
    u = strip_paren(utente)
    if not u:
        return '', ''
    # If there is a comma, prefer last comma-separated pair
    if ',' in u:
        parts = [p.strip() for p in u.split(',') if p.strip()]
        if len(parts) >= 2:
            cognome = parts[0]
            nome = ','.join(parts[1:]).strip()
            return nome, cognome
    # fallback: split words
    parts = u.split()
    if len(parts) >= 2:
        cognome = parts[0]
        nome = ' '.join(parts[1:])
        return nome, cognome
    return '', u


def find_device_code(nome_field: str, cespite_field: str):
    """Try to extract a device hostname/code from `Nome` or `Cespite` fields."""
    for v in (nome_field, cespite_field):
        if not v:
            continue
        v = v.strip()
        # common pattern like ITDGTOL00069400 or IT... with digits
        m = re.search(r'IT[A-Z0-9]+\d+', v)
        if m:
            return m.group(0)
        # sometimes the field already contains a short code like 69400
        m2 = re.search(r'\b\d{4,}\b', v)
        if m2:
            return v
    return ''


def normalize_date(s: str):
    s = (s or '').strip()
    if not s:
        return ''
    for fmt in ('%d/%m/%Y','%Y-%m-%d','%d-%m-%Y'):
        try:
            d = datetime.datetime.strptime(s, fmt)
            return d.strftime('%d/%m/%Y')
        except Exception:
            continue
    return s


def main():
    args = parse_args()
    inp = Path(args.input)
    out = Path(args.output)
    if not inp.exists():
        print(f'Input file not found: {inp}')
        return 1

    sample = inp.read_text(encoding='utf-8', errors='ignore')[:4096]
    delim = args.delimiter or ('\t' if '\t' in sample else (',' if ',' in sample.splitlines()[0] else '\t'))

    with inp.open(newline='') as inf, out.open('w', newline='', encoding='utf-8') as outf:
        reader = csv.DictReader(inf, delimiter=delim)
        header = FULL_HEADER if args.full else MINIMAL_HEADER
        writer = csv.DictWriter(outf, fieldnames=header)
        writer.writeheader()

        for i, row in enumerate(reader, start=2):
            user_raw = row.get('Utente') or row.get('utente') or ''
            nome, cognome = split_name(user_raw)

            device_code = find_device_code(row.get('Nome') or row.get('nome') or '', row.get('Cespite') or row.get('cespite') or '')

            out_row = {
                'tipo_richiesta': args.tipo,
                'categoria': args.categoria,
                'nome_nuovo_utente': '',
                'cognome_nuovo_utente': '',
                'data_ingresso': normalize_date(row.get('Data Arrivo') or row.get('data arrivo') or ''),
                'dipartimento_nuovo_utente': '',
                'tipo_contratto_nuovo_utente': args.contratto,
                'dispositivo_nuovo_hostname': device_code,
                'tipologia_pc_richiesta': row.get('Modello') or row.get('modello') or '',
                'data_pianificazione': normalize_date(row.get('Data pianificazione') or row.get('data pianificazione') or ''),
                'data_assegnazione': '',
                'tecnico_username': row.get('In carico a') or row.get('In carico a') or '',
                'luogo_intervento': '',
            }

            if args.full:
                # add the other keys expected by the full header
                out_row_full = {
                    'tipo_richiesta': out_row['tipo_richiesta'],
                    'categoria': out_row['categoria'],
                    'nome_nuovo_utente': out_row['nome_nuovo_utente'],
                    'cognome_nuovo_utente': out_row['cognome_nuovo_utente'],
                    'data_ingresso': out_row['data_ingresso'],
                    'dipartimento_nuovo_utente': out_row['dipartimento_nuovo_utente'],
                    'tipo_contratto_nuovo_utente': out_row['tipo_contratto_nuovo_utente'],
                    'dispositivo_nuovo_hostname': out_row['dispositivo_nuovo_hostname'],
                    'dispositivo_vecchio_hostname': '',
                    'utente_vecchio_nome': nome,
                    'utente_vecchio_cognome': cognome,
                    'ticket_helpdesk': (row.get('Apertura Ticket') or row.get('Apertura ticket') or row.get('ticket') or ''),
                    'tipologia_pc_richiesta': out_row['tipologia_pc_richiesta'],
                    'note_software': row.get('Note') or row.get('note') or '',
                    'data_pianificazione': out_row['data_pianificazione'],
                    'data_assegnazione': out_row['data_assegnazione'],
                    'tecnico_username': out_row['tecnico_username'],
                    'luogo_intervento': out_row['luogo_intervento'],
                }
                writer.writerow(out_row_full)
            else:
                # minimal header: put parsed user into utente vecchio-like fields by setting nome/cognome nuovo blank (typical for sostituzione)
                out_min = {k: out_row.get(k, '') for k in MINIMAL_HEADER}
                writer.writerow(out_min)

    print(f'Wrote CSV to {out} (delimiter used: {repr(delim)})')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
