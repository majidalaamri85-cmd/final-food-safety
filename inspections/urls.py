from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', views.user_login, name='user_login'),
    path('logout/', views.user_logout, name='user_logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('external-establishments-approval/', views.external_establishments_approval, name='external_establishments_approval'),
    path('conformity-assessment-bodies-assignment/', views.conformity_assessment_bodies_assignment, name='conformity_assessment_bodies_assignment'),
    path('qualification-followups/', views.qualification_followup_list, name='qualification_followup_list'),
    path('establishments/', views.establishment_list, name='establishment_list'),
    path('establishments/new/', views.establishment_create, name='establishment_create'),
    path('evaluations/', views.evaluation_list, name='evaluation_list'),
    path('evaluations/new/', views.evaluation_create, name='evaluation_create'),
    path('evaluations/<int:pk>/edit/', views.evaluation_update, name='evaluation_update'),
    path('evaluations/<int:pk>/submit/', views.evaluation_submit, name='evaluation_submit'),
    path('evaluations/<int:pk>/pdf/', views.evaluation_pdf, name='evaluation_pdf'),
    path('evaluations/<int:pk>/word/', views.evaluation_word, name='evaluation_word'),
    path('corrective-actions/', views.corrective_action_list, name='corrective_action_list'),
    path('corrective-actions/new/', views.corrective_action_create, name='corrective_action_create'),
    path('corrective-actions/<int:pk>/edit/', views.corrective_action_update, name='corrective_action_update'),
    path('exports/establishments.xlsx', views.export_establishments_excel, name='export_establishments_excel'),
    path('exports/qualification-followups.xlsx', views.export_qualification_followups_excel, name='export_qualification_followups_excel'),
    path('exports/evaluations.xlsx', views.export_evaluations_excel, name='export_evaluations_excel'),
]
