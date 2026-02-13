from django.urls import path
from . import views

urlpatterns = [
    path('', views.root),
    path('api/v1/health', views.health),
    path('api/v1/weather/analytics/heavy', views.analytics_heavy),
    path('api/v1/weather/analytics/light', views.analytics_light),
    path('api/v1/weather/analytics/medium', views.analytics_medium),
    path('api/v1/weather/external', views.weather_external),
    path('api/v1/weather/fetch', views.weather_fetch),
    path('api/v1/users', views.create_user),
    path('api/v1/users/<int:user_id>', views.get_user),
    path('api/v1/users/<int:user_id>', views.update_user),
    path('api/v1/users/<int:user_id>', views.delete_user),
]