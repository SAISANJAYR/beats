from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('song/<int:pk>/', views.song_detail, name='song_detail'),
    path('song/add/', views.add_song, name='add_song'),
    path('song/<int:pk>/rate/', views.rate_song, name='rate_song'),
    path('rating/<int:pk>/delete/', views.delete_rating, name='delete_rating'),
    path('profile/<str:username>/', views.profile, name='profile'),
    path('crate-digger/', views.crate_digger_view, name='crate_digger'),
    path('faq/', views.faq_view, name='faq'),
    path('help/', views.faq_view, name='help'),
    path('tickets/', views.support_tickets_view, name='tickets'),
    path('tickets/create/', views.create_ticket_api, name='create_ticket_api'),
    path('health/', views.health_check_view, name='health_check'),
    path('api/recommendations/', views.api_recommendations, name='api_recommendations'),
    path('api/quick-add/', views.api_quick_add, name='api_quick_add'),
    path('api/feedback/', views.submit_feedback_api, name='submit_feedback_api'),
    path('signup/', views.signup_view, name='signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
]
