from django.urls import path
from . import views, nutrition_views as nv

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

    # NutrientAI
    path("nutrition/", nv.nutrition_dashboard, name="nutrition"),
    path("nutrition/settings/", nv.nutrition_settings, name="nutrition_settings"),
    path("nutrition/api/day/", nv.api_day, name="nutrition_api_day"),
    path("nutrition/api/search/", nv.api_search, name="nutrition_api_search"),
    path("nutrition/api/barcode/<str:code>/", nv.api_barcode, name="nutrition_api_barcode"),
    path("nutrition/api/log/", nv.api_log_add, name="nutrition_api_log_add"),
    path("nutrition/api/log/<int:entry_id>/delete/", nv.api_log_delete, name="nutrition_api_log_delete"),
    path("nutrition/api/saved/", nv.api_saved_add, name="nutrition_api_saved_add"),
    path("nutrition/api/saved/<int:food_id>/delete/", nv.api_saved_delete, name="nutrition_api_saved_delete"),
    path("nutrition/api/water/", nv.api_water_add, name="nutrition_api_water_add"),
    path("nutrition/api/water/undo/", nv.api_water_undo, name="nutrition_api_water_undo"),
]
