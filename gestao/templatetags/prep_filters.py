from django import template
from django.utils.html import format_html
import re

register = template.Library()

# Canonical city whitelist (user-provided + common variants)
CANONICAL_CITIES = set([
    'Moncalieri', 'Nichelino', 'Vadò', 'Vado', 'Nizza', 'Barcellona',
    'Ingolstadt', 'Wolfsburg', 'Gaimersheim', 'Napoli', 'Cina', 'USA'
])

SOFTWARE_KEYWORDS = [
    'Office', 'Outlook', 'Teams', 'Chrome', 'Firefox', 'Edge', 'Intune', 'Zoom', 'Slack',
    'Jira', 'SAP', 'Adobe', 'Photoshop', 'Acrobat', 'Excel', 'Word', 'PowerPoint', 'OneDrive',
    'Thunderbird', 'VSCode', 'Docker', 'Citrix', 'VMware', 'Notepad++', 'Putty', 'WinSCP', 'PyCharm'
]
SOFTWARE_PATTERN = re.compile(r"\b(" + "|".join([re.escape(s) for s in SOFTWARE_KEYWORDS]) + r")\b", flags=re.IGNORECASE)

DEVICE_PREFIXES = ['ITDGTOL', 'ITDGTOC', 'EXT', 'IGITMONCL', 'IGITMONCD', 'ITDGTOBA']
DEVICE_PATTERN = re.compile(r'^(?:' + '|'.join(DEVICE_PREFIXES) + r')', flags=re.IGNORECASE)


@register.filter
def validate_ticket(value, fallback_id=None):
    """Return ticket only if it starts with IR or SR (case-insensitive). Otherwise show fallback '#id'."""
    if not value:
        return f"#{fallback_id}" if fallback_id is not None else "--"
    v = str(value).strip()
    if re.match(r'^(?:IR|SR)', v, flags=re.IGNORECASE):
        return v.upper()
    return f"#{fallback_id}" if fallback_id is not None else "--"


@register.filter(is_safe=True)
def format_tipo_richiesta(value):
    """Map various input strings to a strict enum and render a small badge.
    Allowed canonical values: ['sostituzione', 'extra', 'nuovo assunto', 'stagista']
    Unknown values produce a visual fallback showing the original value.
    """
    if not value:
        return format_html('<span class="badge bg-secondary">--</span>')
    v = str(value).strip().lower()
    mapping = {
        'nuova assunzione': 'nuovo assunto',
        'nuovo assunto': 'nuovo assunto',
        'stagista': 'stagista',
        'extra': 'extra',
        'sostituzione': 'sostituzione',
        'riassegnazione': 'sostituzione'
    }
    canonical = mapping.get(v)
    if canonical:
        cls = 'bg-primary' if canonical == 'sostituzione' else 'bg-info text-dark' if canonical == 'stagista' else 'bg-warning text-dark' if canonical == 'extra' else 'bg-success'
        display = canonical.capitalize()
        return format_html('<span class="badge {}">{}</span>', cls, display)
    # fallback visual: show original with muted styling and a tooltip
    return format_html('<span class="badge bg-danger" title="Valore non canonico">{}</span>', str(value))


@register.filter
def validate_luogo(value):
    """Render only city-like names. If not recognized as a city, return '--'."""
    if not value:
        return '--'
    name = str(value).strip()
    # exclude obvious artifacts
    if re.search(r'luogo|originale|software|driver|install|\d', name, flags=re.IGNORECASE):
        return '--'
    # direct whitelist
    if name in CANONICAL_CITIES:
        return name
    # heuristics: allow 1-3 capitalized words, only letters and spaces/hyphen
    if re.match(r'^[A-ZÀ-Ö][A-Za-zÀ-ÿ\-\s]{1,60}$', name):
        # limit to at most 3 words
        if len(name.split()) <= 3:
            return name
    return '--'


@register.simple_tag
def format_user_details(prep):
    """Return structured '[Nome] [Cognome] - [Dipartimento]' sanitized. Expects a Preparazione instance."""
    if not prep:
        return '--'
    def clean_name(s):
        # Fail-safe: ensure string conversion and handle None/model instances
        if s is None:
            return ''
        s_str = str(s).strip()
        if not s_str:
            return ''
        parts = re.split(r'[\s,;]+', s_str)
        kept = [p for p in parts if re.match(r"^[A-Za-zÀ-ÿ'\-]+$", p)]
        return ' '.join(kept)

    tipo = (prep.tipo_richiesta or '').strip().lower()
    if tipo in ['nuova assunzione', 'nuovo assunto']:
        nome = clean_name(getattr(prep, 'nome_nuovo_utente', None))
        cognome = clean_name(getattr(prep, 'cognome_nuovo_utente', None))
        dip = clean_name(getattr(prep, 'dipartimento_nuovo_utente', None))
    else:
        ut = getattr(prep, 'utente', None)
        if ut:
            nome = clean_name(getattr(ut, 'nome', None))
            cognome = clean_name(getattr(ut, 'cognome', None))
            # dipartimento may be a FK object; prefer its 'nome' attribute if present
            dip_obj = getattr(ut, 'dipartimento', None)
            if dip_obj is None:
                dip = ''
            else:
                if hasattr(dip_obj, 'nome'):
                    dip = clean_name(getattr(dip_obj, 'nome', None))
                else:
                    dip = clean_name(str(dip_obj))
        else:
            return '--'

    if not nome and not cognome:
        return '--'
    out = f"{nome} {cognome}".strip()
    if dip:
        out = f"{out} - {dip}"
    return out


@register.filter
def is_nuovo_assunzione(value):
    """Return True if the provided tipo_richiesta value indicates a new hire."""
    if not value:
        return False
    v = str(value).strip().lower()
    return v in ['nuova assunzione', 'nuovo assunto']


@register.filter
def validate_device_hostname(value):
    """Return hostname only if it respects allowed prefixes, else '--'"""
    if not value:
        return '--'
    h = str(value).strip()
    if DEVICE_PATTERN.match(h):
        return h
    return '--'


@register.filter
def extract_software(value):
    """Return comma-separated software names found in the notes. If none, return '--'.
    Allow city mentions only when clearly in a 'spedire' style sentence.
    """
    if not value:
        return '--'
    s = str(value)
    found = SOFTWARE_PATTERN.findall(s)
    unique = []
    for f in found:
        name = f.strip()
        if name.lower() not in [u.lower() for u in unique]:
            unique.append(name)
    if unique:
        return ', '.join(unique)
    # detect 'spedire' contextual city
    m = re.search(r"\b(spedire|spedisci|inviare|invia)\b[^.]*\b([A-Z][a-zA-ZÀ-ÿ\-]+)\b", s, flags=re.IGNORECASE)
    if m:
        return f"Spedire: {m.group(2)}"
    # fallback: if notes is a single capitalized token that looks like a city but isn't contextual, hide it
    if re.match(r'^[A-Z][a-zA-ZÀ-ÿ\-]{1,30}$', s.strip()):
        return '--'
    # otherwise show a short excerpt sanitized
    excerpt = re.sub(r'\s+', ' ', s).strip()
    return excerpt if len(excerpt) <= 100 else excerpt[:97] + '...'
