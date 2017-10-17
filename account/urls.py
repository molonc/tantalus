from django.conf.urls import url
from . import views

app_name = 'account'
urlpatterns = [
    url(r'^login/', views.login_view, name='login'),
    url(r'^logout$', views.logout_view, name='logout'),
    url(r'^password/change$', views.password_update, name='password_update'),
    url(r'^password/forget$', views.password_forget, name='password_forget'),
]