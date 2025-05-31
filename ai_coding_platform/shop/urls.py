from django.urls import path
from . import views

urlpatterns = [
    path('', views.shop_view, name='shop'),
    path('buy/<int:powerup_id>/', views.buy_powerup, name='buy_powerup'),
]
