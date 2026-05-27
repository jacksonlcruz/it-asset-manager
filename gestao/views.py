# gestao/views.py - VERSIONE CORRETTA E COMPLETA
from django.shortcuts import render, redirect, get_object_or_404 #
from django.db.models import Count, Q, OuterRef, Subquery
from .models import Dispositivo, Utente, Assegnazione, Preparazione, Dipartimento
from django.http import JsonResponse
from django.contrib import messages
from datetime import date, timedelta
from .forms import PreparazioneForm, DispositivoForm, LottoDispositiviForm, RestituzioneForm
from django.db.models.functions import TruncMonth
from dateutil.relativedelta import relativedelta

def dashboard(request):

    # --- LOGICA: contare i PC disponibili in magazzino ---
    # Mostra SOLO i dispositivi con stato 'Disponibile' (esclude 'In Bonifica')
    disponibili_novi = Dispositivo.objects.filter(stato='Disponibile')

    disponibili_office = disponibili_novi.filter(tipo='Office').count()
    disponibili_cad = disponibili_novi.filter(tipo='CAD').count()
    total_disponibili = disponibili_novi.count()
    
    # 1. NUMERO DI PC DISPONIBILI, SEPARANDO CAD E OFFICE
    #disponibili_office = Dispositivo.objects.filter(stato='Disponibile', tipo='Office').count()
    #disponibili_cad = Dispositivo.objects.filter(stato='Disponibile', tipo='CAD').count()
    #total_disponibili = disponibili_office + disponibili_cad

    # 2. NUMERO DI PREPARAZIONI IN CORSO
    preparazioni_in_corso = Preparazione.objects.exclude(stato_preparazione='Completato').count()

    # 3. PC PIÙ VECCHI IN USO
    pcs_piu_vecchi = Dispositivo.objects.filter(stato='Assegnato').order_by('data_acquisto')[:20]

    # 4. PROSSIME PREPARAZIONI GIÀ AGENDATE
    today = date.today()
    prossime_preparazioni = Preparazione.objects.filter(
        data_pianificazione__gte=today
    ).exclude(
        stato_preparazione='Completato'
    ).order_by('data_pianificazione')[:20]

    # Preparazioni recenti: ultime 10 (ordina per id decrescente come proxy per "create")
    preparazioni_recenti = Preparazione.objects.all().order_by('-id')[:10]

    # Raccoglie tutto nel "contesto" da inviare alla pagina
    context = {
        'disponibili_office': disponibili_office,
        'disponibili_cad': disponibili_cad,
        'total_disponibili': total_disponibili,
        'preparazioni_in_corso': preparazioni_in_corso,
        'pcs_piu_vecchi': pcs_piu_vecchi,
        'prossime_preparazioni': prossime_preparazioni,
        'preparazioni_recenti': preparazioni_recenti,
        'page_title': 'Dashboard'
    }

    return render(request, 'gestao/dashboard.html', context)

def lista_dispositivi(request):
    # --- Logica per l'eliminazione multipla ---
    if request.method == 'POST' and 'delete_selected' in request.POST:
        device_ids = request.POST.getlist('device_ids')
        dispositivi_da_cancellare = Dispositivo.objects.filter(id__in=device_ids).exclude(stato='Assegnato')
        count = dispositivi_da_cancellare.count()
        dispositivi_da_cancellare.delete()
        messages.success(request, f'{count} dispositivi cancellati con successo.')
        return redirect('lista_dispositivi')

    # --- Logica per mostrare la lista (richiesta GET) ---

    # Logica di Ordinamento
    sort_by = request.GET.get('sort', 'hostname')
    allowed_sort_fields = ['hostname', 'tipo', 'stato', 'locazione_magazzino', 'utente_cognome',
                           '-hostname', '-tipo', '-stato', '-locazione_magazzino', '-utente_cognome']
    if sort_by not in allowed_sort_fields:
        sort_by = 'hostname'

    # --- NUOVA LOGICA PER ORDINARE PER UTENTE ---
    # Crea una subquery per recuperare il cognome dell'utente dall'assegnazione attiva
    utente_subquery = Assegnazione.objects.filter(
        dispositivo=OuterRef('pk'), 
        data_restituzione__isnull=True
    ).values('utente__cognome')[:1]

    # Annota ogni dispositivo con il cognome dell'utente attuale
    dispositivi_list = Dispositivo.objects.annotate(
        utente_cognome=Subquery(utente_subquery)
    )

    # Applica l'ordinamento
    dispositivi_list = dispositivi_list.order_by(sort_by)

    # Logica di Filtro
    query = request.GET.get('q')
    stato_filter = request.GET.get('stato')
    if query: 
        dispositivi_list = dispositivi_list.filter(Q(hostname__icontains=query) | Q(cespite__icontains=query))
    if stato_filter: 
        dispositivi_list = dispositivi_list.filter(stato=stato_filter)

    stati_disponibili = Dispositivo.objects.values_list('stato', flat=True).distinct()

    context = {
        'dispositivi': dispositivi_list,
        'stati_disponibili': stati_disponibili,
        'current_sort': sort_by,
        'page_title': 'Elenco Dispositivi'
    }
    return render(request, 'gestao/lista_dispositivi.html', context)

def lista_preparazioni(request):
    preparazioni_list = Preparazione.objects.all().order_by('-id')
    context = {'preparazioni': preparazioni_list, 'page_title': 'Coda di Preparazione PC'}
    return render(request, 'gestao/lista_preparazioni.html', context)

# View que usa o formulário
def crea_preparazione(request):
    # L'import è fatto QUI DENTRO per evitare l'importazione circolare
    from .forms import PreparazioneForm

    if request.method == 'POST':
        form = PreparazioneForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Nuova preparazione creata con successo.')
            return redirect('lista_preparazioni')
    else:
        form = PreparazioneForm()
    context = {'form': form, 'page_title': 'Crea Nuova Preparazione'}
    return render(request, 'gestao/preparazione_form.html', context)

# Adicionei a importação que faltava para a função dashboard
from datetime import date, timedelta


def get_dispositivi_utente(request):
    # Recupera l'ID utente inviato tramite URL (es: ?utente_id=1)
    utente_id = request.GET.get('utente_id')

    # Filtra i dispositivi con stato 'Assegnato' per l'utente_id ricevuto.
    # La ricerca 'assegnazione__utente_id' naviga attraverso la relazione inversa.
    dispositivi = Dispositivo.objects.filter(
        stato='Assegnato', 
        assegnazione__utente_id=utente_id,
        assegnazione__data_restituzione__isnull=True # Recupera solo le assegnazioni attive
    ).values('id', 'hostname') # Recupera solo i campi necessari

    # Restituisce i dati come lista JSON
    return JsonResponse(list(dispositivi), safe=False)


def get_dispositivi_per_tipo(request):
    # Recupera la tipologia inviata tramite URL (es: ?tipologia=Office)
    tipologia = request.GET.get('tipologia')

    # Filtra i dispositivi con stato 'Disponibile' E della tipologia ricevuta
    dispositivi = Dispositivo.objects.filter(
        stato='Disponibile', 
        tipo=tipologia
    ).values('id', 'hostname')

    # Restituisce i dati come lista JSON
    return JsonResponse(list(dispositivi), safe=False)


def dettaglio_preparazione(request, pk):
    preparazione = get_object_or_404(Preparazione, pk=pk)
    if request.method == 'POST':
        if 'finalizza' in request.POST:
            if not preparazione.dispositivo_nuovo:
                messages.error(request, 'Errore: Selezionare un "Nuovo Dispositivo" prima di finalizzare.')
            else:
                preparazione.tecnico_responsabile = request.user
                utente_finale = None
                # --- Logica per Nuova Assunzione ---
                if preparazione.tipo_richiesta == 'Nuova Assunzione':
                    # 1. Trova o crea l'oggetto Dipartimento
                    dipartimento_obj = None
                    if preparazione.dipartimento_nuovo_utente:
                        dipartimento_obj, _ = Dipartimento.objects.get_or_create(
                            nome=preparazione.dipartimento_nuovo_utente.strip()
                        )
                    # 2. Crea il nuovo utente, collegandolo all'oggetto Dipartimento
                    utente_finale = Utente.objects.create(
                        nome=preparazione.nome_nuovo_utente,
                        cognome=preparazione.cognome_nuovo_utente,
                        dipartimento=dipartimento_obj, # Passa l'oggetto, non il testo
                        tipo_contratto=preparazione.tipo_contratto_nuovo_utente
                    )
                # --- Logica per Sostituzione ---
                else:
                    utente_finale = preparazione.utente
                    if preparazione.dispositivo_vecchio:
                        old_assegnazione = Assegnazione.objects.filter(dispositivo=preparazione.dispositivo_vecchio, data_restituzione__isnull=True).first()
                        if old_assegnazione:
                            old_assegnazione.data_restituzione = date.today()
                            old_assegnazione.save()

                # 3. Crea l'assegnazione finale
                if utente_finale:
                    assegnazione = Assegnazione.objects.create(
                        dispositivo=preparazione.dispositivo_nuovo,
                        utente=utente_finale,
                        data_assegnazione=date.today()
                    )
                    preparazione.assegnazione = assegnazione # Collega con l'assegnazione creata

                preparazione.stato_preparazione = 'Completato'
                preparazione.save()
                messages.success(request, 'Preparazione finalizzata con successo!')

        else: # Logica per salvare la Checklist
            preparazione.mail_inviata = 'mail_inviata' in request.POST
            preparazione.dati_in_scsm = 'dati_in_scsm' in request.POST
            preparazione.in_ars = 'in_ars' in request.POST
            preparazione.delivery_inviato = 'delivery_inviato' in request.POST
            preparazione.save()
            messages.success(request, 'Checklist aggiornato!')

        return redirect('dettaglio_preparazione', pk=preparazione.pk)

    context = {'preparazione': preparazione, 'page_title': f"Dettaglio Preparazione #{preparazione.pk}"}
    return render(request, 'gestao/dettaglio_preparazione.html', context)


def modifica_preparazione(request, pk):
    # L'import è aggiunto QUI DENTRO per accedere al formulario
    from .forms import PreparazioneForm 

    preparazione = get_object_or_404(Preparazione, pk=pk)
    if request.method == 'POST':
        form = PreparazioneForm(request.POST, instance=preparazione)
        if form.is_valid():
            form.save()
            messages.success(request, 'Preparazione aggiornata con successo!')
            return redirect('dettaglio_preparazione', pk=preparazione.pk)
    else:
        form = PreparazioneForm(instance=preparazione)

    context = {
        'form': form,
        'page_title': f'Modifica Preparazione #{preparazione.pk}'
    }
    return render(request, 'gestao/preparazione_form.html', context)


def cancella_preparazione(request, pk):
    preparazione = get_object_or_404(Preparazione, pk=pk)

    # Se o usuário confirmar a exclusão no formulário
    if request.method == 'POST':
        preparazione.delete()
        messages.success(request, f'Preparazione #{pk} cancellata con successo.')
        return redirect('lista_preparazioni') # Reindirizza alla lista principale

    # Se è il primo accesso, mostra solo la pagina di conferma
    context = {
        'preparazione': preparazione,
        'page_title': f'Conferma Cancellazione Preparazione #{pk}'
    }
    return render(request, 'gestao/preparazione_confirm_delete.html', context)


def crea_dispositivo_singolo(request):
    if request.method == 'POST':
        form = DispositivoForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, f"Dispositivo '{form.cleaned_data['hostname']}' creato con successo.")
            return redirect('lista_dispositivi')
    else:
        form = DispositivoForm()

    context = {
        'form': form,
        'page_title': 'Aggiungi Dispositivo Singolo'
    }
    return render(request, 'gestao/dispositivo_form.html', context)


def crea_lotto_dispositivi(request):
    if request.method == 'POST':
        form = LottoDispositiviForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            marca = data['marca']
            modello = data['modello']
            tipo_pc = data['tipo_pc']
            tipologia = data['tipo_dettaglio']
            cespite_start = data['cespite_iniziale']
            quantita = data['quantita']
            data_acquisto = data['data_acquisto']
            
            dispositivi_creati = 0
            dispositivi_esistenti = []

            for i in range(quantita):
                cespite_num = cespite_start + i
                cespite_str = str(cespite_num)
                
                if tipo_pc == 'Notebook':
                    hostname = f"IGITMONCL0{cespite_str}"
                else:
                    hostname = f"IGITMONCD0{cespite_str}"
                
                dispositivo, created = Dispositivo.objects.get_or_create(
                    cespite=cespite_str,
                    defaults={
                        'hostname': hostname,
                        'marca': marca,
                        'modello': modello,
                        'tipo': tipologia,
                        'numero_serie': cespite_str,
                        'stato': 'Disponibile',
                        'data_acquisto': data_acquisto
                    }
                )
                if created:
                    dispositivi_creati += 1
                else:
                    dispositivi_esistenti.append(hostname)
            
            msg = f"{dispositivi_creati} dispositivi creati con successo."
            if dispositivi_esistenti:
                msg += f" {len(dispositivi_esistenti)} dispositivi già esistevano e sono stati ignorati: {', '.join(dispositivi_esistenti)}."
            messages.success(request, msg)
            return redirect('lista_dispositivi')
    
    # O 'else' deve estar alinhado com o 'if request.method == 'POST''
    else:
        form = LottoDispositiviForm()

    # AS LINHAS ABAIXO ESTAVAM FALTANDO
    context = {
        'form': form,
        'page_title': 'Aggiungi Lote di Dispositivi'
    }
    return render(request, 'gestao/lote_dispositivi_form.html', context)


def modifica_dispositivo(request, pk):
    # Recupera il dispositivo tramite ID (pk), o restituisce 404 se non trovato
    dispositivo = get_object_or_404(Dispositivo, pk=pk)

    if request.method == 'POST':
        # Si passa 'instance=dispositivo' affinché Django sappia che stiamo
        # modificando un oggetto esistente, e non creandone uno nuovo.
        form = DispositivoForm(request.POST, instance=dispositivo)
        if form.is_valid():
            form.save()
            messages.success(request, f"Dispositivo '{dispositivo.hostname}' aggiornato con successo.")
            return redirect('lista_dispositivi') # Reindirizza alla lista
    else:
        # Se è il primo accesso (GET), precompila il modulo con i dati del dispositivo
        form = DispositivoForm(instance=dispositivo)

    context = {
        'form': form,
        'page_title': f"Modifica Dispositivo: {dispositivo.hostname}"
    }
    # Riutilizziamo lo stesso template del modulo di creazione!
    return render(request, 'gestao/dispositivo_form.html', context)


def cancella_dispositivo(request, pk):
    dispositivo = get_object_or_404(Dispositivo, pk=pk)

    # Regola di sicurezza: non permettere di cancellare un PC assegnato a un utente
    if dispositivo.stato == 'Assegnato':
        messages.error(request, f"Impossibile cancellare un dispositivo che è attualmente assegnato a un utente.")
        return redirect('lista_dispositivi')

    if request.method == 'POST':
        hostname = dispositivo.hostname
        dispositivo.delete()
        messages.success(request, f'Dispositivo "{hostname}" cancellato con successo.')
        return redirect('lista_dispositivi')

    context = {
        'dispositivo': dispositivo,
        'page_title': f'Conferma Cancellazione Dispositivo'
    }
    return render(request, 'gestao/dispositivo_confirm_delete.html', context)


def restituzione_pc(request):
    if request.method == 'POST':
        form = RestituzioneForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            dispositivo = data['dispositivo']
            data_restituzione = data['data_restituzione']
            locazione = data['locazione_magazzino']
            note_restituzione = data['note']

            assegnazione_attiva = Assegnazione.objects.filter(
                dispositivo=dispositivo, 
                data_restituzione__isnull=True
            ).first()

            if assegnazione_attiva:
                # 1. Chiude la vecchia assegnazione
                assegnazione_attiva.data_restituzione = data_restituzione
                assegnazione_attiva.save()

                # --- LOGICA AGGIORNATA ED ESPLICITA ---
                # 2. Imposta lo stato del dispositivo come 'In Bonifica'
                dispositivo.stato = 'In Bonifica'
                
                # 3. Aggiorna gli altri campi del dispositivo
                dispositivo.locazione_magazzino = locazione
                if note_restituzione:
                    dispositivo.note = f"Restituito il {data_restituzione.strftime('%d/%m/%Y')}: {note_restituzione}\n---\n{dispositivo.note or ''}"
                
                # 4. Salva tutte le modifiche sul dispositivo in una sola operazione
                dispositivo.save()

                messages.success(request, f"Dispositivo '{dispositivo.hostname}' restituito con successo e ora è 'In Bonifica'.")
            else:
                messages.error(request, f"Errore: Nessuna assegnazione attiva trovata per il dispositivo '{dispositivo.hostname}'.")
            
            return redirect('lista_dispositivi')
    else:
        form = RestituzioneForm()

    context = {
        'form': form,
        'page_title': 'Registra Restituzione PC'
    }
    return render(request, 'gestao/restituzione_form.html', context)


def disponibili_per_tipo_chart_data(request):
    # Restituisce il conteggio dei dispositivi con stato 'Disponibile',
    # aggregando solo le categorie Office e CAD come richiesto.
    office = Dispositivo.objects.filter(stato='Disponibile', tipo='Office').count()
    cad = Dispositivo.objects.filter(stato='Disponibile', tipo='CAD').count()

    labels = ['Office', 'CAD']
    chart_data = [office, cad]

    return JsonResponse({'labels': labels, 'data': chart_data})


def report_page(request):
    # --- Logica per i grafici annuali ---
    current_year = date.today().year
    # Recupera l'anno corrente e i due precedenti
    years = [current_year, current_year - 1, current_year - 2]

    annual_data = {}
    # Le categorie da mostrare in ogni grafico
    labels = ['Nuovi Funzionari', 'Stagisti/Interinali', 'Sostituzioni/Extra']

    for year in years:
        # Filtra le preparazioni completate per l'anno specifico
        preparazioni_anno = Preparazione.objects.filter(
            data_pianificazione__year=year,
            stato_preparazione='Completato'
        )
        # Esegue i conteggi per ogni categoria all'interno di quell'anno
        nuovi_funzionari = preparazioni_anno.filter(tipo_richiesta='Nuova Assunzione', categoria='Standard').count()
        nuovi_stagisti = preparazioni_anno.filter(tipo_richiesta='Nuova Assunzione', categoria__in=['Stagista', 'Interinale']).count()
        sostituzioni_riassegnazioni = preparazioni_anno.filter(Q(tipo_richiesta='Sostituzione') | Q(categoria__in=['Riassegnazione', 'Extra'])).count()

        # Salva i dati per quell'anno
        annual_data[year] = {
            'labels': labels,
            'data': [nuovi_funzionari, nuovi_stagisti, sostituzioni_riassegnazioni]
        }

    # --- Logica per la tabella di rottamazione ---
    dispositivi_rottamati = Dispositivo.objects.filter(stato='Rottamato')

    context = {
        'page_title': 'Report e Statistiche',
        'dispositivi_rottamati': dispositivi_rottamati,
        'annual_data': annual_data # Passa il dizionario Python direttamente
    }
    return render(request, 'gestao/report_page.html', context)


def dispositivi_per_marca_data(request):
    data = Dispositivo.objects.values('marca').annotate(total=Count('marca')).order_by('-total')
    labels = [item['marca'] for item in data]
    chart_data = [item['total'] for item in data]
    return JsonResponse({'labels': labels, 'data': chart_data})


def dettaglio_dispositivo(request, pk):
    dispositivo = get_object_or_404(Dispositivo, pk=pk)

    # Recupera tutto lo storico delle assegnazioni per questo dispositivo, dalle più recenti alle più vecchie
    storico_assegnazioni = Assegnazione.objects.filter(dispositivo=dispositivo).order_by('-data_assegnazione')

    context = {
        'dispositivo': dispositivo,
        'storico': storico_assegnazioni,
        'page_title': f"Dettaglio: {dispositivo.hostname}"
    }
    return render(request, 'gestao/dettaglio_dispositivo.html', context)


def lista_utenti(request):
    # Recupera tutti gli utenti, ordinati per cognome e nome
    utenti_list = Utente.objects.all().order_by('cognome', 'nome')

    context = {
        'utenti': utenti_list,
        'page_title': 'Elenco Utenti'
    }
    return render(request, 'gestao/lista_utenti.html', context)


def dettaglio_utente(request, pk):
    # Recupera l'utente tramite ID (pk)
    utente = get_object_or_404(Utente, pk=pk)

    # Recupera tutto lo storico delle assegnazioni per questo utente
    storico_assegnazioni = Assegnazione.objects.filter(utente=utente).order_by('-data_assegnazione')

    context = {
        'utente': utente,
        'storico': storico_assegnazioni,
        'page_title': f"Dettaglio Utente: {utente}"
    }
    return render(request, 'gestao/dettaglio_utente.html', context)


def assegnazioni_mensili_data(request):
    # Raggruppa per mese e, all'interno di ogni mese, conta quanti sono 'Office' e quanti 'CAD'
    data = Assegnazione.objects.annotate(
        month=TruncMonth('data_assegnazione')
    ).values('month').annotate(
        office_count=Count('id', filter=Q(dispositivo__tipo='Office')),
        cad_count=Count('id', filter=Q(dispositivo__tipo='CAD'))
    ).order_by('month')

    # Formatta i dati nel formato atteso da Chart.js per grafici a barre sovrapposte
    labels = [d['month'].strftime('%b %Y') for d in data]

    datasets = [
        {
            'label': 'Office',
            'data': [d['office_count'] for d in data],
            'backgroundColor': 'rgba(0, 123, 255, 0.7)', # Blu
        },
        {
            'label': 'CAD',
            'data': [d['cad_count'] for d in data],
            'backgroundColor': 'rgba(255, 193, 7, 0.7)', # Giallo
        }
    ]

    return JsonResponse({'labels': labels, 'datasets': datasets})


def preparazioni_per_motivo_data(request):
    today = date.today()
    # --- LA MODIFICA È QUI ---
    # Invece di 1 anno fa, recuperiamo 3 anni fa.
    # date(today.year - 3, 1, 1) significa "1° gennaio, tre anni fa".
    three_years_ago = date(today.year - 3, 1, 1)

    # Filtra le preparazioni completate negli ultimi 3 anni
    preparazioni_recenti = Preparazione.objects.filter(
        data_pianificazione__gte=three_years_ago,
        stato_preparazione='Completato'
    )

    # Il resto della logica rimane invariato
    nuovi_funzionari = preparazioni_recenti.filter(tipo_richiesta='Nuova Assunzione', categoria='Standard').count()
    nuovi_stagisti = preparazioni_recenti.filter(tipo_richiesta='Nuova Assunzione', categoria='Stagista/Interinale').count()
    sostituzioni_riassegnazioni = preparazioni_recenti.filter(Q(tipo_richiesta='Sostituzione') | Q(categoria='Riassegnazione')).count()

    labels = ['Nuovi Funzionari', 'Stagisti/Interinali', 'Sostituzioni/Extra']
    chart_data = [nuovi_funzionari, nuovi_stagisti, sostituzioni_riassegnazioni]

    return JsonResponse({'labels': labels, 'data': chart_data})


def search_results(request):
    query = request.GET.get('q', '')

    dispositivi_results = Utente.objects.none()
    utenti_results = Utente.objects.none()
    preparazioni_results = Preparazione.objects.none()

    if query:
        # Ricerca in Dispositivi
        dispositivi_results = Dispositivo.objects.filter(
            Q(hostname__icontains=query) | 
            Q(cespite__icontains=query) | 
            Q(modello__icontains=query)
        )
        # Ricerca in Utenti
        utenti_results = Utente.objects.filter(
            Q(nome__icontains=query) | 
            Q(cognome__icontains=query)
        )
        # --- LOGICA DI RICERCA MIGLIORATA PER PREPARAZIONI ---
        preparazioni_results = Preparazione.objects.filter(
            Q(ticket_helpdesk__icontains=query) |
            Q(utente__nome__icontains=query) |
            Q(utente__cognome__icontains=query) |
            Q(nome_nuovo_utente__icontains=query) |
            Q(cognome_nuovo_utente__icontains=query)
        )
        # Permette anche la ricerca per numero ID
        if query.isdigit():
            preparazioni_results = preparazioni_results.union(Preparazione.objects.filter(pk=query))


    context = {
        'query': query,
        'dispositivi': dispositivi_results,
        'utenti': utenti_results,
        'preparazioni': preparazioni_results,
        'page_title': f"Risultati per '{query}'"
    }
    return render(request, 'gestao/search_results.html', context)