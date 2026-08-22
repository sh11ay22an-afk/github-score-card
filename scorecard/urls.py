from django.contrib import admin
from django.urls import path
from github_app import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.home, name='home'),
    path('score/', views.score_card, name='score_card'),
    path('leaderboard/', views.leaderboard, name='leaderboard'),
    path('leaderboard/clear/', views.clear_leaderboard, name='clear_leaderboard'),
    path('history/clear/', views.clear_history, name='clear_history'),
]