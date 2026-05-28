from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q
import re

from gestao.models import Preparazione, Sede


def _clean_text(s):
    if not s:
        return ''
    s = s.strip()
    s = re.sub(r'[\r\n]+', ' ', s)
    s = re.sub(r'[,:;\-\–\—]+', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s


def _extract_canonical_city(text):
    if not text:
        return None
    t = text.strip()
    # Rimuovi parole common
    t = re.sub(r'(?i)\b(sede|ufficio|filiale|stabilimento|sede di|sede operativa|sede centrale|sede amministrativa)\b', ' ', t)
    # Separa da indirizzi o numeri
    t = re.split(r'[,\-()/:]', t)[0]
    # Rimuovi indicatori di via/piazza
    t = re.sub(r'(?i)\b(via|v\.|piazza|p\.?zza|strada|pza|p\.)\b.*', '', t)
    # Toglie caratteri non alfabetici eccetto spazi e dash
    t = re.sub(r"[^A-Za-zÀ-ÿ'\s\-]", ' ', t)
    t = re.sub(r'\s+', ' ', t).strip()
    if not t:
        return None
    # Mantieni sequenza iniziale di parole che cominciano con maiuscola (es: San Giovanni)
    parts = t.split()
    city_parts = []
    for p in parts:
        if re.match(r'^[A-ZÀ-ÖÙ-Ý]', p):
            city_parts.append(p)
        else:
            break
        if len(city_parts) >= 3:
            break
    if not city_parts:
        # fallback: primo token
        city = parts[0]
    else:
        city = ' '.join(city_parts)
    city = city.strip()
    return city or None


def _looks_like_location_detail(s):
    if not s:
        return False
    s_lower = s.lower()
    # Riconosce dettagli di luogo solo se presenti parole chiave di localizzazione
    if re.search(r'\b(sala|piano|interno|edificio|padiglione|ufficio|stanza|aula|lab|laboratorio|ingresso)\b', s_lower):
        return True
    # Pattern tipo 'room 12', 'rm12', 'r12'
    if re.search(r'\b(?:room|rm|r)\s*\d+\b', s_lower):
        return True
    return False


def _extract_ticket_id(text):
    if not text:
        return None, text
    patterns = [r'\bSR\d{3,}\b', r'\bTICKET[- ]?\d+\b', r'\bINC\d+\b']
    for pat in patterns:
        m = re.search(pat, text, flags=re.IGNORECASE)
        if m:
            ticket = m.group(0).upper()
            new_text = re.sub(re.escape(m.group(0)), '', text, flags=re.IGNORECASE)
            return ticket, _clean_text(new_text)
    return None, text


def _extract_software_parts(text, software_pattern):
    if not text:
        return [], text
    parts = re.split(r'[\n\r;,/]+', text)
    collected = []
    rest = []
    for part in parts:
        p = part.strip()
        if not p:
            continue
        if software_pattern.search(p):
            collected.append(_clean_text(p))
        else:
            rest.append(p)
    return collected, _clean_text(' '.join(rest))


def _clean_name_field(s):
    if not s:
        return None, []
    parts = re.split(r'[\s,;]+', s.strip())
    kept = []
    moved = []
    for p in parts:
        if re.match(r"^[A-Za-zÀ-ÿ'\-]+$", p):
            kept.append(p)
        else:
            moved.append(p)
    return (_clean_text(' '.join(kept)) or None), moved


class Command(BaseCommand):
    help = 'Normalizza i campi delle Preparazione: estrae città in luogo_intervento e pulisce sedi/colonne correlate.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Mostra le modifiche senza salvarle (default)')
        parser.add_argument('--commit', action='store_true', help='Applica le modifiche sul DB')
        parser.add_argument('--limit', type=int, default=0, help='Numero massimo di record da processare (0 = tutti)')

    def handle(self, *args, **options):
        dry_run = options.get('dry_run') and not options.get('commit')
        commit = options.get('commit')
        limit = options.get('limit') or 0

        fields_to_scan = ['note_software', 'motivo_sostituzione', 'dipartimento_nuovo_utente', 'ticket_helpdesk']
        software_source_fields = ['motivo_sostituzione', 'ticket_helpdesk', 'dipartimento_nuovo_utente']

        software_keywords = [
            'Office', 'Outlook', 'Teams', 'Chrome', 'Firefox', 'Edge', 'Intune', 'Zoom', 'Slack',
            'Jira', 'SAP', 'Adobe', 'Photoshop', 'Acrobat', 'Excel', 'Word', 'PowerPoint', 'OneDrive',
            'Thunderbird', 'VSCode', 'Docker', 'Citrix', 'VMware'
        ]
        software_pattern = re.compile(r"\b(" + "|".join([re.escape(s) for s in software_keywords]) + r")\b", flags=re.IGNORECASE)

        # Assicura la presenza delle sedi canoniche fornite dall'utente
        canonical_sedi = [
            'Moncalieri', 'Nichelino', 'Vadò', 'Nizza', 'Barcellona',
            'Ingolstadt', 'Wolfsburg', 'Gaimersheim', 'Napoli', 'Cina', 'USA'
        ]
        for cname in canonical_sedi:
            exists = Sede.objects.filter(nome__iexact=cname).first()
            if not exists:
                if commit:
                    Sede.objects.create(nome=cname)
                    self.stdout.write(self.style.SUCCESS(f"Creato Sede canonica: {cname}"))
                else:
                    self.stdout.write(self.style.WARNING(f"Sede canonica mancante: {cname} (verrà creata con --commit)"))

        # 0) Canonicalizza la tabella Sede: estrai la città da nomi rumorosi e unisci/rename
        self.stdout.write('Canonicalizzazione della tabella Sede...')
        sede_objs = list(Sede.objects.all())
        sede_map = {}  # old_name -> canonical_name
        for s in sede_objs:
            orig = s.nome or ''
            canonical = _extract_canonical_city(orig)
            if not canonical:
                continue
            if canonical.lower() == orig.strip().lower():
                continue
            existing = Sede.objects.filter(nome__iexact=canonical).first()
            if existing:
                # sposta riferimenti e elimina la sede obsoleta
                refs = Preparazione.objects.filter(luogo_intervento=s).count()
                if commit:
                    Preparazione.objects.filter(luogo_intervento=s).update(luogo_intervento=existing)
                    # Copia indirizzo se mancante
                    if s.indirizzo and not existing.indirizzo:
                        existing.indirizzo = s.indirizzo
                        existing.save()
                    s.delete()
                sede_map[orig] = existing.nome
                self.stdout.write(self.style.SUCCESS(f"Unito Sede '{orig}' -> '{existing.nome}' (refs: {refs})"))
            else:
                if commit:
                    # Se possibile, estrai parte indirizzo
                    addr = None
                    m = re.search(r'(via|v\.|piazza|p\.?zza|strada)\s+(.+)', orig, flags=re.IGNORECASE)
                    if m:
                        addr = m.group(0)
                    s.nome = canonical
                    if addr and not s.indirizzo:
                        s.indirizzo = addr
                    s.save()
                sede_map[orig] = canonical
                self.stdout.write(self.style.SUCCESS(f"Rinomina Sede '{orig}' -> '{canonical}'"))

        # Aggiorna la lista dei nomi sedi
        sede_names = list(Sede.objects.values_list('nome', flat=True))
        sede_names_sorted = sorted(sede_names, key=lambda s: len(s or ''), reverse=True)

        # 1) Seleziona preparazioni che hanno contenuti da analizzare o sedi sospette
        q_any = Q()
        for f in fields_to_scan:
            q_any |= (Q(**{f + '__isnull': False}) & ~Q(**{f: ''}))

        q_bad_luogo = Q(luogo_intervento__isnull=False) & (
            Q(luogo_intervento__nome__iregex=r'\\d') | Q(luogo_intervento__nome__icontains='via') | Q(luogo_intervento__nome__icontains='sede')
        )

        qs = Preparazione.objects.filter(q_any | q_bad_luogo)
        total = qs.count()
        if limit > 0:
            qs = qs[:limit]

        start_re = re.compile(r"^\s*([A-ZÀ-ÖÙ-Ý][A-Za-zÀ-ÿ'\s\-]{1,60}?)\s*[-,:]\s*(.*)$")
        end_re = re.compile(r"^(.*?)[-,:]\s*([A-ZÀ-ÖÙ-Ý][A-Za-zÀ-ÿ'\s\-]{1,60})\s*$")

        processed = 0
        changed = 0

        for prep in qs:
            processed += 1
            before = {f: (getattr(prep, f) or '') for f in set(fields_to_scan + ['note_software'])}
            before['luogo_intervento'] = prep.luogo_intervento.nome if prep.luogo_intervento else None

            modified = False

            # 0.a) Estrai ticket se mancante (cerco in vari campi testuali)
            if not (prep.ticket_helpdesk and prep.ticket_helpdesk.strip()):
                ticket_sources = fields_to_scan + ['nome_nuovo_utente', 'cognome_nuovo_utente', 'dipartimento_nuovo_utente', 'note_software', 'motivo_sostituzione']
                for sf in ticket_sources:
                    sval = (getattr(prep, sf) or '').strip()
                    if not sval:
                        continue
                    ticket, new_val = _extract_ticket_id(sval)
                    if ticket:
                        prep.ticket_helpdesk = ticket
                        if new_val != sval:
                            setattr(prep, sf, new_val or None)
                            modified = True
                        break

            # 0.b) Pulisci i campi nome/cognome dai token non-anagrafici
            for name_field in ['nome_nuovo_utente', 'cognome_nuovo_utente']:
                val = (getattr(prep, name_field) or '')
                cleaned, moved = _clean_name_field(val)
                if cleaned != (val or ''):
                    setattr(prep, name_field, cleaned)
                    modified = True
                if moved:
                    existing_note = (prep.note_software or '').strip()
                    add = ' '.join(moved)
                    new_note = (existing_note + ('\n' if existing_note else '') + f"Estratto da {name_field}: {add}").strip()
                    prep.note_software = new_note
                    modified = True

            # Contenuti da controllare
            values = {f: (getattr(prep, f) or '').strip() for f in fields_to_scan}
            combined = ' '.join([v for v in values.values() if v])

            # 2) Cerca corrispondenze con Sede esistenti nel testo combinato
            matched = False
            if combined:
                for sname in sede_names_sorted:
                    if not sname:
                        continue
                    pattern = r'\\b' + re.escape(sname) + r'\\b'
                    if re.search(pattern, combined, flags=re.IGNORECASE):
                        sede_obj = Sede.objects.filter(nome__iexact=sname).first()
                        if sede_obj:
                            if not prep.luogo_intervento or (prep.luogo_intervento and prep.luogo_intervento.pk != sede_obj.pk):
                                prep.luogo_intervento = sede_obj
                                modified = True
                            # Rimuovi la città da tutti i campi scansionati e sposta dettagli luogo se presenti
                            for f in fields_to_scan:
                                v = (getattr(prep, f) or '')
                                if not v:
                                    continue
                                new_v = re.sub(pattern, '', v, flags=re.IGNORECASE)
                                new_v = _clean_text(new_v)
                                if new_v and _looks_like_location_detail(new_v):
                                    # sposta in note_software come dettaglio luogo
                                    existing_note = (prep.note_software or '').strip()
                                    add = f"Luogo dettagli: {new_v}"
                                    if add not in existing_note:
                                        prep.note_software = (existing_note + ('\n' if existing_note else '') + add).strip()
                                        modified = True
                                    setattr(prep, f, None)
                                else:
                                    if new_v != (getattr(prep, f) or ''):
                                        setattr(prep, f, new_v or None)
                                        modified = True
                            matched = True
                            break

            if not matched:
                # 3) Prova pattern generici campo-per-campo (es: "Città - testo" o "testo - Città")
                for f in fields_to_scan:
                    val = values.get(f, '')
                    if not val:
                        continue
                    m = start_re.match(val)
                    if m:
                        city = m.group(1).strip()
                        rest = m.group(2).strip()
                        sede_obj, _ = Sede.objects.get_or_create(nome=city)
                        # rimuovi city da tutti i campi
                        for ff in fields_to_scan:
                            v = (getattr(prep, ff) or '')
                            v_new = re.sub(re.escape(city), '', v, flags=re.IGNORECASE)
                            v_new = _clean_text(v_new)
                            if v_new and _looks_like_location_detail(v_new):
                                existing_note = (prep.note_software or '').strip()
                                add = f"Luogo dettagli: {v_new}"
                                if add not in existing_note:
                                    prep.note_software = (existing_note + ('\n' if existing_note else '') + add).strip()
                                    modified = True
                                setattr(prep, ff, None)
                            else:
                                if v_new != (getattr(prep, ff) or ''):
                                    setattr(prep, ff, v_new or None)
                                    modified = True
                        prep.luogo_intervento = sede_obj
                        modified = True
                        break

                    m2 = end_re.match(val)
                    if m2:
                        city = m2.group(2).strip()
                        sede_obj, _ = Sede.objects.get_or_create(nome=city)
                        for ff in fields_to_scan:
                            v = (getattr(prep, ff) or '')
                            v_new = re.sub(re.escape(city), '', v, flags=re.IGNORECASE)
                            v_new = _clean_text(v_new)
                            if v_new and _looks_like_location_detail(v_new):
                                existing_note = (prep.note_software or '').strip()
                                add = f"Luogo dettagli: {v_new}"
                                if add not in existing_note:
                                    prep.note_software = (existing_note + ('\n' if existing_note else '') + add).strip()
                                    modified = True
                                setattr(prep, ff, None)
                            else:
                                if v_new != (getattr(prep, ff) or ''):
                                    setattr(prep, ff, v_new or None)
                                    modified = True
                        prep.luogo_intervento = sede_obj
                        modified = True
                        break

            # 4) Estrai informazioni software da altri campi verso note_software
            collected_sw = []
            for f in software_source_fields:
                val = (getattr(prep, f) or '').strip()
                if not val:
                    continue
                parts_collected, remainder = _extract_software_parts(val, software_pattern)
                if parts_collected:
                    collected_sw.extend(parts_collected)
                if remainder != val:
                    setattr(prep, f, remainder or None)
                    modified = True

            if collected_sw:
                existing_note = (prep.note_software or '').strip()
                add_text = '; '.join(collected_sw)
                if add_text not in existing_note:
                    prep.note_software = (existing_note + ('\n' if existing_note else '') + add_text).strip()
                    modified = True

            if modified:
                changed += 1
                if commit:
                    try:
                        with transaction.atomic():
                            prep.save()
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f"Errore salvando Preparazione #{prep.pk}: {e}"))
                else:
                    after = {f: (getattr(prep, f) or '') for f in set(fields_to_scan + ['note_software'])}
                    after['luogo_intervento'] = prep.luogo_intervento.nome if prep.luogo_intervento else None
                    self.stdout.write(self.style.WARNING(f"Preparazione #{prep.pk} avrebbe cambiamenti:"))
                    for k in after.keys():
                        if before.get(k, '') != after.get(k, ''):
                            self.stdout.write(f" - {k}: '{before.get(k)}' -> '{after.get(k)}'")

        self.stdout.write(self.style.SUCCESS(f'Processati {processed} record; {changed} modifiche rilevate.'))
        if not commit:
            self.stdout.write('Esegui con --commit per applicare le modifiche sul database.')
