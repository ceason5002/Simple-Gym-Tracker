from django.urls import path
from . import views

# routes for tracker
urlpatterns = [
    path("", views.home, name="home"),
    path("signup/", views.signup_view, name="signup"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("lifts/add/", views.add_lift, name="add_lift"),
    path("lifts/<int:lift_id>/delete/", views.delete_lift, name="delete_lift"),
    path("workouts/create/", views.create_workout, name="create_workout"),
    path("workouts/<int:workout_id>/", views.workout_detail, name="workout_detail"),
    path("entries/add/", views.add_entry, name="add_entry"),

]
