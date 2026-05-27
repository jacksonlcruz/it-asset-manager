from django.core.management.base import BaseCommand
import csv
from datetime import datetime, date
from django.utils import timezone
from django.contrib.auth.models import User

from gestao.models import (
    Utente, Dipartimento, Dispositivo, Assegnazione, Preparazione, Sede
)


def parse_date(datestr):
    if not datestr:
        return None
    datestr = datestr.strip()
    for fmt in ('%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y'):
        try:
            return datetime.strptime(datestr, fmt).date()
        except Exception:
            continue
    # fallback: try ISO parse
    try:
        return datetime.fromisoformat(datestr).date()
    except Exception:
        return None


class Command(BaseCommand):
    help = 'Legge preparazioni da preparazioni_da_concludere.csv e le marca come completate'

    def add_arguments(self, parser):
        parser.add_argument('--file', help='Percorso del file CSV (default: preparazioni_da_concludere.csv)', default='preparazioni_da_concludere.csv')

    def handle(self, *args, **options):
        file_path = options['file']
        self.stdout.write(self.style.SUCCESS(f'Avvio elaborazione file: {file_path}'))

        try:
            with open(file_path, mode='r', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                for i, row in enumerate(reader, start=2):
                    try:
                        tipo_richiesta = (row.get('tipo_richiesta') or 'Nuova Assunzione').strip()
                        categoria = (row.get('categoria') or 'Standard').strip()
                        nome = (row.get('nome_nuovo_utente') or '').strip()
                        cognome = (row.get('cognome_nuovo_utente') or '').strip()
                        data_ingresso = parse_date(row.get('data_ingresso') or '')
                        dipartimento_txt = (row.get('dipartimento_nuovo_utente') or '').strip()
                        tipo_contratto = (row.get('tipo_contratto_nuovo_utente') or 'Interno').strip()
                        dispositivo_nuovo_host = (row.get('dispositivo_nuovo_hostname') or '').strip()
                        dispositivo_vecchio_host = (row.get('dispositivo_vecchio_hostname') or '').strip()
                        utente_vecchio_nome = (row.get('utente_vecchio_nome') or '').strip()
                        utente_vecchio_cognome = (row.get('utente_vecchio_cognome') or '').strip()
                        ticket = (row.get('ticket_helpdesk') or '').strip()
                        tipologia_pc = (row.get('tipologia_pc_richiesta') or '').strip()
                        note_software = (row.get('note_software') or '').strip()
                        data_pianificazione = parse_date(row.get('data_pianificazione') or '')
                        data_assegnazione = parse_date(row.get('data_assegnazione') or '') or date.today()
                        tecnico_username = (row.get('tecnico_username') or '').strip()
                        luogo_intervento_txt = (row.get('luogo_intervento') or '').strip()

                        # Trova o crea la sede
                        luogo_obj = None
                        if luogo_intervento_txt:
                            luogo_obj, _ = Sede.objects.get_or_create(nome=luogo_intervento_txt)

                        # Trova il tecnico
                        tecnico_obj = None
                        if tecnico_username:
                            tecnico_obj = User.objects.filter(username__iexact=tecnico_username).first()

                        # Logica Nuova Assunzione
                        utente_finale = None
                        if tipo_richiesta == 'Nuova Assunzione':
                            dip_obj = None
                            if dipartimento_txt:
                                dip_obj, _ = Dipartimento.objects.get_or_create(nome=dipartimento_txt)

                            if nome or cognome:
                                utente_finale, _ = Utente.objects.get_or_create(
                                    nome=nome,
                                    cognome=cognome,
                                    defaults={'dipartimento': dip_obj, 'tipo_contratto': tipo_contratto}
                                )
                            else:
                                self.stdout.write(self.style.WARNING(f'Riga {i}: Nuova assunzione senza nome/cognome; salto.'))
                                continue
                        else:
                            # Sostituzione: prova a recuperare l'utente vecchio
                            utente_finale = None
                            if utente_vecchio_nome or utente_vecchio_cognome:
                                utente_finale = Utente.objects.filter(
                                    nome__iexact=utente_vecchio_nome,
                                    cognome__iexact=utente_vecchio_cognome
                                ).first()

                        # Trova o crea il nuovo dispositivo
                        dispositivo_nuovo = None
                        if dispositivo_nuovo_host:
                            dispositivo_nuovo = Dispositivo.objects.filter(hostname__iexact=dispositivo_nuovo_host).first()
                            if not dispositivo_nuovo:
                                dispositivo_nuovo = Dispositivo.objects.create(
                                    hostname=dispositivo_nuovo_host,
                                    marca='Unknown',
                                    modello='Unknown',
                                    tipo=tipologia_pc or 'Office',
                                    stato='Disponibile'
                                )

                        # Se è una sostituzione, gestisci il vecchio dispositivo (restituzione)
                        if tipo_richiesta != 'Nuova Assunzione' and dispositivo_vecchio_host:
                            dispositivo_vecchio = Dispositivo.objects.filter(hostname__iexact=dispositivo_vecchio_host).first()
                            if dispositivo_vecchio:
                                old_ass = Assegnazione.objects.filter(dispositivo=dispositivo_vecchio, data_restituzione__isnull=True).first()
                                if old_ass:
                                    old_ass.data_restituzione = data_assegnazione or date.today()
                                    old_ass.save()

                        # Crea l'oggetto Preparazione (stato Completato) e l'assegnazione finale
                        preparazione = Preparazione.objects.create(
                            tipo_richiesta=tipo_richiesta,
                            stato_preparazione='Completato',
                            categoria=categoria if categoria in [c[0] for c in Preparazione.CATEGORIA_CHOICES] else 'Standard',
                            luogo_intervento=luogo_obj,
                            tecnico_responsabile=tecnico_obj,
                            nome_nuovo_utente=nome or None,
                            cognome_nuovo_utente=cognome or None,
                            data_ingresso=data_ingresso,
                            dipartimento_nuovo_utente=dipartimento_txt or None,
                            tipo_contratto_nuovo_utente=tipo_contratto or 'Interno',
                            utente=utente_finale if tipo_richiesta == 'Sostituzione' else None,
                            dispositivo_vecchio=None,
                            motivo_sostituzione=None,
                            dispositivo_nuovo=dispositivo_nuovo,
                            ticket_helpdesk=ticket or None,
                            tipologia_pc_richiesta=tipologia_pc or None,
                            note_software=note_software or None,
                            data_pianificazione=timezone.make_aware(datetime.combine(data_pianificazione, datetime.min.time())) if data_pianificazione else None,
                        )

                        # Crea assegnazione se abbiamo un utente e un dispositivo
                        if (utente_finale) and dispositivo_nuovo:
                            assegnazione = Assegnazione.objects.create(
                                dispositivo=dispositivo_nuovo,
                                utente=utente_finale,
                                data_assegnazione=data_assegnazione or date.today()
                            )
                            preparazione.assegnazione = assegnazione
                            preparazione.save()

                        self.stdout.write(self.style.SUCCESS(f'Riga {i}: Preparazione per "{nome} {cognome}" marcata Completato.'))

                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f'Errore riga {i}: {e}'))

        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f'File non trovato: {file_path}'))

        self.stdout.write(self.style.SUCCESS('Elaborazione completata.'))
