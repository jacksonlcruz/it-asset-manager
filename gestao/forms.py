# gestao/forms.py
from django import forms
from .models import Preparazione, Dispositivo, Dipartimento # Importamos o Dispositivo
from datetime import date

class PreparazioneForm(forms.ModelForm):
    # Transforma o campo de texto em um menu dropdown que busca na tabela Dipartimento
    dipartimento_nuovo_utente = forms.ModelChoiceField(
        queryset=Dipartimento.objects.all(),
        required=False,
        label="Dipartimento (Nuovo Utente)",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filtra o campo para mostrar apenas dispositivos com status 'Disponibile'
        self.fields['dispositivo_nuovo'].queryset = Dispositivo.objects.filter(stato='Disponibile').order_by('hostname')
        # Também podemos limitar o campo do dispositivo antigo para mostrar apenas os atribuídos
        self.fields['dispositivo_vecchio'].queryset = Dispositivo.objects.filter(stato='Assegnato').order_by('hostname')


    class Meta:
        model = Preparazione
        # Lista de campos ATUALIZADA
        fields = [
            'tipo_richiesta', 'categoria', 'luogo_intervento', # <-- Adicionamos o novo campo
            'nome_nuovo_utente', 'cognome_nuovo_utente', 'data_ingresso', 'dipartimento_nuovo_utente', 'tipo_contratto_nuovo_utente',
            'utente', 'dispositivo_vecchio', 
            'motivo_sostituzione',
            'dispositivo_nuovo',
            'ticket_helpdesk', 'tipologia_pc_richiesta', 'note_software', 'data_pianificazione'
        ]
        # O campo manual foi removido da lista 'fields'

        widgets = {
            'data_ingresso': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'data_pianificazione': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'tipo_richiesta': forms.Select(attrs={'class': 'form-select'}),
            'categoria': forms.Select(attrs={'class': 'form-select'}),
            'tipo_contratto_nuovo_utente': forms.Select(attrs={'class': 'form-select'}),
            'utente': forms.Select(attrs={'class': 'form-select'}),
            'dispositivo_vecchio': forms.Select(attrs={'class': 'form-select'}),
            'dispositivo_nuovo': forms.Select(attrs={'class': 'form-select'}), # Widget para o novo campo
            'motivo_sostituzione': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'luogo_intervento': forms.Select(attrs={'class': 'form-select'}),
            'note_software': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        }
        labels = {
            'tipo_richiesta': 'Tipo di Richiesta', 
            'categoria': 'Categoria della Richiesta',
            'nome_nuovo_utente': 'Nome (Nuovo Utente)',
            'cognome_nuovo_utente': 'Cognome (Nuovo Utente)',
            'data_ingresso': 'Data di Ingresso',
            'dipartimento_nuovo_utente': 'Dipartimento (Nuovo Utente)',
            'utente': 'Utente Esistente (per Sostituzione)',
            'dispositivo_vecchio': 'Dispositivo da Sostituire',
            'dispositivo_nuovo': 'Nuovo Dispositivo (dal Magazzino)', # Label para o novo campo
            'motivo_sostituzione': 'Motivo della Sostituzione',
            'ticket_helpdesk': 'Ticket Help Desk',
            'tipologia_pc_richiesta': 'Tipologia PC Richiesta',
            'note_software': 'Note / Software Richiesti',
            'data_pianificazione': 'Data Pianificata per l\'intervento',
        }



class DispositivoForm(forms.ModelForm):
    class Meta:
        model = Dispositivo
        # Definimos os campos que queremos no formulário
        fields = ['hostname', 'cespite', 'numero_serie', 'marca', 'modello', 'tipo', 'stato', 'data_acquisto', 'note']

        # Adicionamos widgets para que fiquem bonitos com Bootstrap
        widgets = {
            'hostname': forms.TextInput(attrs={'class': 'form-control'}),
            'cespite': forms.TextInput(attrs={'class': 'form-control'}),
            'numero_serie': forms.TextInput(attrs={'class': 'form-control'}),
            'marca': forms.TextInput(attrs={'class': 'form-control'}),
            'modello': forms.TextInput(attrs={'class': 'form-control'}),
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'stato': forms.Select(attrs={'class': 'form-select'}),
            'data_acquisto': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'note': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        }

    # Função especial para tornar alguns campos não obrigatórios
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Tornar campos não-obrigatórios
        self.fields['cespite'].required = False
        self.fields['numero_serie'].required = False
        self.fields['data_acquisto'].required = False
        self.fields['note'].required = False

        # --- NOSSA NOVA LÓGICA ---
        # Se estamos criando um novo dispositivo (não editando um existente)
        if not self.instance.pk:
            # Define o valor inicial do campo 'stato' para 'Disponibile'
            self.fields['stato'].initial = 'Disponibile'
            # Desabilita o campo para que não seja editável na tela de criação
            self.fields['stato'].disabled = True


class LoteDispositiviForm(forms.Form):
    TIPO_PC_CHOICES = [('Notebook', 'Notebook'), ('PC Fisso', 'PC Fisso')]

    # O campo 'tipo' no modelo Dispositivo é para Office/CAD. Este é para o hardware.
    # Mantive os nomes diferentes para clareza: tipo_pc vs tipo_dettaglio
    tipo_pc = forms.ChoiceField(choices=TIPO_PC_CHOICES, label="Tipo de PC (para gerar Hostname)", widget=forms.Select(attrs={'class': 'form-select'}))

    # Usamos as escolhas que já definimos no modelo Dispositivo
    tipo_dettaglio = forms.ChoiceField(choices=Dispositivo.TIPO_CHOICES, label="Tipologia (Office/CAD, etc)", widget=forms.Select(attrs={'class': 'form-select'}))

    marca = forms.CharField(max_length=100, label="Marca", widget=forms.TextInput(attrs={'class': 'form-control'}))
    modello = forms.CharField(max_length=100, label="Modello", widget=forms.TextInput(attrs={'class': 'form-control'}))
    cespite_iniziale = forms.IntegerField(label="Cespite Iniziale", help_text="Es. 78500", widget=forms.NumberInput(attrs={'class': 'form-control'}))
    quantita = forms.IntegerField(label="Quantità di PC da creare", help_text="Es. 50", min_value=1, initial=1, widget=forms.NumberInput(attrs={'class': 'form-control'}))
    data_acquisto = forms.DateField(label="Data di Acquisto", required=False, widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}))


#Classe de devolucao de PC
class RestituzioneForm(forms.Form):
    dispositivo = forms.ModelChoiceField(
        queryset=Dispositivo.objects.filter(stato='Assegnato').order_by('hostname'),
        label="Dispositivo a restituire",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    data_restituzione = forms.DateField(
        label="Data di Restituzione",
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        initial=date.today
    )
    locazione_magazzino = forms.CharField(
        label="Locazione in Magazzino (opzionale)", # <-- Mudamos o texto do label
        help_text="Es. Scaffale A-03",
        required=False, # <-- ESTA É A MUDANÇA PRINCIPAL
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    note = forms.CharField(
        label="Note sulla restituzione",
        required=False,
        widget=forms.Textarea(attrs={'rows': 3, 'class': 'form-control'})
    )