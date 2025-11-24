# gestao/views.py - VERSÃO CORRIGIDA E COMPLETA
from django.shortcuts import render, redirect, get_object_or_404 #
from django.db.models import Count, Q, OuterRef, Subquery
from .models import Dispositivo, Utente, Assegnazione, Preparazione, Dipartimento
from django.http import JsonResponse
from django.contrib import messages
from datetime import date, timedelta
from .forms import PreparazioneForm, DispositivoForm, LoteDispositiviForm, RestituzioneForm
from django.db.models.functions import TruncMonth
from dateutil.relativedelta import relativedelta

def dashboard(request):

    # --- LÓGICA ATUALIZADA PARA CONTAR APENAS PCS NOVOS ---
    disponibili_novi = Dispositivo.objects.filter(
    stato='Disponibile', 
    assegnazione__isnull=True # A mágica: só conta se NUNCA teve uma 'Assegnazione'
    )

    disponibili_office = disponibili_novi.filter(tipo='Office').count()
    disponibili_cad = disponibili_novi.filter(tipo='CAD').count()
    total_disponibili = disponibili_novi.count()
    
    # 1. NÚMEROS DE PCS DISPONÍVEIS, SEPARANDO CAD E OFFICE
    #disponibili_office = Dispositivo.objects.filter(stato='Disponibile', tipo='Office').count()
    #disponibili_cad = Dispositivo.objects.filter(stato='Disponibile', tipo='CAD').count()
    #total_disponibili = disponibili_office + disponibili_cad

    # 2. QUANTIDADE DE PREPARAÇÕES EM ANDAMENTO
    preparazioni_in_corso = Preparazione.objects.exclude(stato_preparazione='Completato').count()

    # 3. PC PIÙ VECCHI IN USO (Lógica mantida)
    pcs_piu_vecchi = Dispositivo.objects.filter(stato='Assegnato').order_by('data_acquisto')[:20]

    # 4. PROSSIME PREPARAZIONI GIÀ AGENDATE
    today = date.today()
    prossime_preparazioni = Preparazione.objects.filter(
        data_pianificazione__gte=today
    ).exclude(
        stato_preparazione='Completato'
    ).order_by('data_pianificazione')[:20]

    # Agrupando tudo no "contexto" para enviar para a página
    context = {
        'disponibili_office': disponibili_office,
        'disponibili_cad': disponibili_cad,
        'total_disponibili': total_disponibili,
        'preparazioni_in_corso': preparazioni_in_corso,
        'pcs_piu_vecchi': pcs_piu_vecchi,
        'prossime_preparazioni': prossime_preparazioni,
        'page_title': 'Dashboard'
    }

    return render(request, 'gestao/dashboard.html', context)

def lista_dispositivi(request):
    # --- Lógica para deletar em lote ---
    if request.method == 'POST' and 'delete_selected' in request.POST:
        device_ids = request.POST.getlist('device_ids')
        dispositivi_da_cancellare = Dispositivo.objects.filter(id__in=device_ids).exclude(stato='Assegnato')
        count = dispositivi_da_cancellare.count()
        dispositivi_da_cancellare.delete()
        messages.success(request, f'{count} dispositivi cancellati con successo.')
        return redirect('lista_dispositivi')

    # --- Lógica para mostrar a lista (GET request) ---

    # Lógica de Ordenação
    sort_by = request.GET.get('sort', 'hostname')
    allowed_sort_fields = ['hostname', 'tipo', 'stato', 'locazione_magazzino', 'utente_cognome',
                           '-hostname', '-tipo', '-stato', '-locazione_magazzino', '-utente_cognome']
    if sort_by not in allowed_sort_fields:
        sort_by = 'hostname'

    # --- NOVA LÓGICA PARA ORDENAR POR USUÁRIO ---
    # Cria uma subquery para buscar o sobrenome do usuário da atribuição ativa
    utente_subquery = Assegnazione.objects.filter(
        dispositivo=OuterRef('pk'), 
        data_restituzione__isnull=True
    ).values('utente__cognome')[:1]

    # Anota cada dispositivo com o sobrenome do seu usuário atual
    dispositivi_list = Dispositivo.objects.annotate(
        utente_cognome=Subquery(utente_subquery)
    )

    # Aplica a ordenação
    dispositivi_list = dispositivi_list.order_by(sort_by)

    # Lógica de Filtro (continua a mesma)
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
    # O import é feito AQUI DENTRO para quebrar o ciclo
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
    # Pega o ID do usuário que foi enviado pela URL (ex: ?utente_id=1)
    utente_id = request.GET.get('utente_id')

    # Filtra os dispositivos que estão 'Assegnato' para o utente_id recebido.
    # A busca 'assegnazione__utente_id' navega através do relacionamento reverso.
    dispositivi = Dispositivo.objects.filter(
        stato='Assegnato', 
        assegnazione__utente_id=utente_id,
        assegnazione__data_restituzione__isnull=True # Garante que são atribuições ativas
    ).values('id', 'hostname') # Pega apenas os campos que precisamos

    # Retorna os dados como uma lista JSON
    return JsonResponse(list(dispositivi), safe=False)


def get_dispositivi_per_tipo(request):
    # Pega a tipologia enviada pela URL (ex: ?tipologia=Office)
    tipologia = request.GET.get('tipologia')

    # Filtra os dispositivos que estão 'Disponibile' E são da tipologia recebida
    dispositivi = Dispositivo.objects.filter(
        stato='Disponibile', 
        tipo=tipologia
    ).values('id', 'hostname')

    # Retorna os dados como uma lista JSON
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
                # --- Lógica para Nuova Assunzione ATUALIZADA ---
                if preparazione.tipo_richiesta == 'Nuova Assunzione':
                    # 1. Encontra ou cria o objeto Dipartimento
                    dipartimento_obj = None
                    if preparazione.dipartimento_nuovo_utente:
                        dipartimento_obj, _ = Dipartimento.objects.get_or_create(
                            nome=preparazione.dipartimento_nuovo_utente.strip()
                        )
                    # 2. Cria o novo usuário, ligando-o ao objeto Dipartimento
                    utente_finale = Utente.objects.create(
                        nome=preparazione.nome_nuovo_utente,
                        cognome=preparazione.cognome_nuovo_utente,
                        dipartimento=dipartimento_obj,# Passa o objeto, não o texto
                        tipo_contratto=preparazione.tipo_contratto_nuovo_utente
                    )
                # --- Lógica para Sostituzione (sem alteração na atribuição) ---
                else:
                    utente_finale = preparazione.utente
                    if preparazione.dispositivo_vecchio:
                        old_assegnazione = Assegnazione.objects.filter(dispositivo=preparazione.dispositivo_vecchio, data_restituzione__isnull=True).first()
                        if old_assegnazione:
                            old_assegnazione.data_restituzione = date.today()
                            old_assegnazione.save()

                # 3. Cria a atribuição final
                if utente_finale:
                    assegnazione = Assegnazione.objects.create(
                        dispositivo=preparazione.dispositivo_nuovo,
                        utente=utente_finale,
                        data_assegnazione=date.today()
                    )
                    preparazione.assegnazione = assegnazione # Linka com a atribuição criada

                preparazione.stato_preparazione = 'Completato'
                preparazione.save()
                messages.success(request, 'Preparazione finalizzata con successo!')

        else: # Lógica para salvar o Checklist (sem alteração)
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
    # A linha de import é adicionada AQUI DENTRO para que a função conheça o formulário
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
        return redirect('lista_preparazioni') # Redireciona para a lista principal

    # Se for o primeiro acesso, apenas mostra a página de confirmação
    context = {
        'preparazione': preparazione,
        'page_title': f'Conferma Cancellazione Preparazione #{pk}'
    }
    return render(request, 'gestao/preparazione_confirm_delete.html', context)


def cria_dispositivo_singolo(request):
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


def cria_lote_dispositivi(request):
    if request.method == 'POST':
        form = LoteDispositiviForm(request.POST)
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
        form = LoteDispositiviForm()

    # AS LINHAS ABAIXO ESTAVAM FALTANDO
    context = {
        'form': form,
        'page_title': 'Aggiungi Lote di Dispositivi'
    }
    return render(request, 'gestao/lote_dispositivi_form.html', context)


def modifica_dispositivo(request, pk):
    # Busca o dispositivo pelo seu ID (pk), ou retorna um erro 404 se não encontrar
    dispositivo = get_object_or_404(Dispositivo, pk=pk)

    if request.method == 'POST':
        # Passamos 'instance=dispositivo' para que o Django saiba que estamos
        # editando um objeto existente, e não criando um novo.
        form = DispositivoForm(request.POST, instance=dispositivo)
        if form.is_valid():
            form.save()
            messages.success(request, f"Dispositivo '{dispositivo.hostname}' aggiornato con successo.")
            return redirect('lista_dispositivi') # Redireciona de volta para a lista
    else:
        # Se for o primeiro acesso (GET), pré-preenche o formulário com os dados do dispositivo
        form = DispositivoForm(instance=dispositivo)

    context = {
        'form': form,
        'page_title': f"Modifica Dispositivo: {dispositivo.hostname}"
    }
    # Reutilizamos o mesmo template do formulário de criação!
    return render(request, 'gestao/dispositivo_form.html', context)

# gestao/views.py
# ... (imports e outras views) ...


def cancella_dispositivo(request, pk):
    dispositivo = get_object_or_404(Dispositivo, pk=pk)

    # Regra de segurança: não permitir deletar um PC que está atribuído
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
                # 1. Encerra a atribuição antiga
                assegnazione_attiva.data_restituzione = data_restituzione
                assegnazione_attiva.save()

                # --- LÓGICA ATUALIZADA E EXPLÍCITA ---
                # 2. Define o status do dispositivo como 'In Bonifica'
                dispositivo.stato = 'In Bonifica'
                
                # 3. Atualiza os outros campos do dispositivo
                dispositivo.locazione_magazzino = locazione
                if note_restituzione:
                    dispositivo.note = f"Restituito il {data_restituzione.strftime('%d/%m/%Y')}: {note_restituzione}\n---\n{dispositivo.note or ''}"
                
                # 4. Salva todas as mudanças no dispositivo de uma só vez
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
    # Agrupa os dispositivos com stato='Disponibile' por 'tipo' e conta quantos existem em cada grupo
    data = Dispositivo.objects.filter(stato='Disponibile').values('tipo').annotate(total=Count('tipo')).order_by('tipo')

    # Prepara os dados para o formato que o Chart.js espera
    labels = [item['tipo'] for item in data]
    chart_data = [item['total'] for item in data]

    response_data = {
        'labels': labels,
        'data': chart_data,
    }
    return JsonResponse(response_data)


def report_page(request):
    # --- Lógica para os gráficos anuais ---
    current_year = date.today().year
    # Pega o ano atual e os dois anteriores
    years = [current_year, current_year - 1, current_year - 2]

    annual_data = {}
    # As categorias que queremos em cada gráfico
    labels = ['Nuovi Funzionari', 'Stagisti/Interinali', 'Sostituzioni/Extra']

    for year in years:
        # Filtra as preparações finalizadas para o ano específico
        preparazioni_anno = Preparazione.objects.filter(
            data_pianificazione__year=year,
            stato_preparazione='Completato'
        )
        # Faz as contagens para cada categoria dentro daquele ano
        novos_funcionarios = preparazioni_anno.filter(tipo_richiesta='Nuova Assunzione', categoria='Standard').count()
        novos_stagisti = preparazioni_anno.filter(tipo_richiesta='Nuova Assunzione', categoria__in=['Stagista', 'Interinale']).count()
        trocas_reassegnazioni = preparazioni_anno.filter(Q(tipo_richiesta='Sostituzione') | Q(categoria__in=['Riassegnazione', 'Extra'])).count()

        # Guarda os dados para aquele ano
        annual_data[year] = {
            'labels': labels,
            'data': [novos_funcionarios, novos_stagisti, trocas_reassegnazioni]
        }

    # --- Lógica para a tabela de descarte (continua a mesma) ---
    dispositivi_rottamati = Dispositivo.objects.filter(stato='Rottamato')

    context = {
        'page_title': 'Report e Statistiche',
        'dispositivi_rottamati': dispositivi_rottamati,
        'annual_data': annual_data # Passa o dicionário Python diretamente
    }
    return render(request, 'gestao/report_page.html', context)


def dispositivi_per_marca_data(request):
    data = Dispositivo.objects.values('marca').annotate(total=Count('marca')).order_by('-total')
    labels = [item['marca'] for item in data]
    chart_data = [item['total'] for item in data]
    return JsonResponse({'labels': labels, 'data': chart_data})


def dettaglio_dispositivo(request, pk):
    dispositivo = get_object_or_404(Dispositivo, pk=pk)

    # Busca todo o histórico de atribuições para este dispositivo, das mais recentes às mais antigas
    storico_assegnazioni = Assegnazione.objects.filter(dispositivo=dispositivo).order_by('-data_assegnazione')

    context = {
        'dispositivo': dispositivo,
        'storico': storico_assegnazioni,
        'page_title': f"Dettaglio: {dispositivo.hostname}"
    }
    return render(request, 'gestao/dettaglio_dispositivo.html', context)


def lista_utenti(request):
    # Busca todos os usuários, ordenados por sobrenome e nome
    utenti_list = Utente.objects.all().order_by('cognome', 'nome')

    context = {
        'utenti': utenti_list,
        'page_title': 'Elenco Utenti'
    }
    return render(request, 'gestao/lista_utenti.html', context)


def dettaglio_utente(request, pk):
    # Busca o usuário pelo seu ID (pk)
    utente = get_object_or_404(Utente, pk=pk)

    # Busca todo o histórico de atribuições para este usuário
    storico_assegnazioni = Assegnazione.objects.filter(utente=utente).order_by('-data_assegnazione')

    context = {
        'utente': utente,
        'storico': storico_assegnazioni,
        'page_title': f"Dettaglio Utente: {utente}"
    }
    return render(request, 'gestao/dettaglio_utente.html', context)


def assegnazioni_mensili_data(request):
    # Agrupa por mês e, dentro de cada mês, conta quantos são 'Office' e quantos são 'CAD'
    data = Assegnazione.objects.annotate(
        month=TruncMonth('data_assegnazione')
    ).values('month').annotate(
        office_count=Count('id', filter=Q(dispositivo__tipo='Office')),
        cad_count=Count('id', filter=Q(dispositivo__tipo='CAD'))
    ).order_by('month')

    # Formata os dados para o formato que o Chart.js espera para gráficos empilhados
    labels = [d['month'].strftime('%b %Y') for d in data]

    datasets = [
        {
            'label': 'Office',
            'data': [d['office_count'] for d in data],
            'backgroundColor': 'rgba(0, 123, 255, 0.7)', # Azul
        },
        {
            'label': 'CAD',
            'data': [d['cad_count'] for d in data],
            'backgroundColor': 'rgba(255, 193, 7, 0.7)', # Amarelo
        }
    ]

    return JsonResponse({'labels': labels, 'datasets': datasets})


def preparazioni_per_motivo_data(request):
    today = date.today()
    # --- A MUDANÇA ESTÁ AQUI ---
    # Em vez de 1 ano atrás, pegamos 3 anos atrás.
    # date(today.year - 3, 1, 1) significa "1 de janeiro, três anos atrás".
    three_years_ago = date(today.year - 3, 1, 1)

    # Filtra as preparações finalizadas nos últimos 3 anos
    preparazioni_recenti = Preparazione.objects.filter(
        data_pianificazione__gte=three_years_ago,
        stato_preparazione='Completato'
    )

    # O resto da lógica continua exatamente o mesmo
    novos_funcionarios = preparazioni_recenti.filter(tipo_richiesta='Nuova Assunzione', categoria='Standard').count()
    novos_stagisti = preparazioni_recenti.filter(tipo_richiesta='Nuova Assunzione', categoria='Stagista/Interinale').count()
    trocas_reassegnazioni = preparazioni_recenti.filter(Q(tipo_richiesta='Sostituzione') | Q(categoria='Riassegnazione')).count()

    labels = ['Nuovi Funzionari', 'Stagisti/Interinali', 'Sostituzioni/Extra']
    chart_data = [novos_funcionarios, novos_stagisti, trocas_reassegnazioni]

    return JsonResponse({'labels': labels, 'data': chart_data})


def search_results(request):
    query = request.GET.get('q', '')

    dispositivi_results = Utente.objects.none()
    utenti_results = Utente.objects.none()
    preparazioni_results = Preparazione.objects.none()

    if query:
        # Busca em Dispositivos
        dispositivi_results = Dispositivo.objects.filter(
            Q(hostname__icontains=query) | 
            Q(cespite__icontains=query) | 
            Q(modello__icontains=query)
        )
        # Busca em Utenti
        utenti_results = Utente.objects.filter(
            Q(nome__icontains=query) | 
            Q(cognome__icontains=query)
        )
        # --- LÓGICA DE BUSCA MELHORADA PARA PREPARAZIONI ---
        preparazioni_results = Preparazione.objects.filter(
            Q(ticket_helpdesk__icontains=query) |
            Q(utente__nome__icontains=query) |
            Q(utente__cognome__icontains=query) |
            Q(nome_nuovo_utente__icontains=query) |
            Q(cognome_nuovo_utente__icontains=query)
        )
        # Permite também buscar pelo número do ID
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