from django.contrib.auth.views import LoginView

from .forms import ConnexionForm


class ConnexionView(LoginView):
    template_name = "comptes/connexion.html"
    form_class = ConnexionForm
    redirect_authenticated_user = True
