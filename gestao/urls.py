from django.urls import path
from . import views

urlpatterns = [
    # A string vazia '' significa a raiz do site
    path('', views.dashboard, name='dashboard'),
    path('utenti/', views.lista_utenti, name='lista_utenti'),
    path('dispositivi/', views.lista_dispositivi, name='lista_dispositivi'),
    path('utenti/<int:pk>/', views.dettaglio_utente, name='dettaglio_utente'),
    path('dispositivi/nuovo/', views.cria_dispositivo_singolo, name='cria_dispositivo_singolo'),
    path('dispositivi/lote/', views.cria_lote_dispositivi, name='cria_lote_dispositivi'),
    path('dispositivi/<int:pk>/edit/', views.modifica_dispositivo, name='modifica_dispositivo'),
    path('dispositivi/<int:pk>/', views.dettaglio_dispositivo, name='dettaglio_dispositivo'),
    path('dispositivi/<int:pk>/delete/', views.cancella_dispositivo, name='cancella_dispositivo'),
    path('restituzione/', views.restituzione_pc, name='restituzione_pc'),
    path('report/', views.report_page, name='report_page'),
    path('search/', views.search_results, name='search_results'),

    # --- API ---
    path('api/get-dispositivi-utente/', views.get_dispositivi_utente, name='get_dispositivi_utente'),
    path('api/get-dispositivi-per-tipo/', views.get_dispositivi_per_tipo, name='get_dispositivi_per_tipo'),
    path('api/chart/disponibili-per-tipo/', views.disponibili_per_tipo_chart_data, name='disponibili_per_tipo_chart_data'),
    path('api/chart/dispositivi-per-marca/', views.dispositivi_per_marca_data, name='dispositivi_per_marca_data'),
    path('api/chart/assegnazioni-mensili/', views.assegnazioni_mensili_data, name='assegnazioni_mensili_data'),
    path('api/chart/preparazioni-per-motivo/', views.preparazioni_per_motivo_data, name='preparazioni_per_motivo_data'),

    # --- Preparazioni ---
    path('preparazioni/', views.lista_preparazioni, name='lista_preparazioni'),
    path('preparazioni/nuova/', views.crea_preparazione, name='crea_preparazione'),
    path('preparazioni/<int:pk>/', views.dettaglio_preparazione, name='dettaglio_preparazione'),
    path('preparazioni/<int:pk>/edit/', views.modifica_preparazione, name='modifica_preparazione'),
    path('preparazioni/<int:pk>/delete/', views.cancella_preparazione, name='cancella_preparazione'),
]