from django.urls import path
from .views import signup_view, login_view, logout_view, profile_dashboard, leaderboard


urlpatterns = [
    path('signup/', signup_view, name='signup'),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('profile/', profile_dashboard, name='profile_dashboard'),
    path('leaderboard/', leaderboard, name='leaderboard'),

]
