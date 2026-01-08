from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("signup/", views.signup_view, name="signup"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),

    path("dashboard/", views.dashboard, name="dashboard"),
    path("workouts/create/", views.create_workout, name="create_workout"),
    path("workouts/<int:workout_id>/", views.workout_detail, name="workout_detail"),
    path("entries/add/", views.add_entry, name="add_entry"),
    path("settings/theme/", views.theme_settings, name="theme_settings"),
]
