"""Paroisse courante de la requête en cours.

Portée par une ContextVar (et non un threading.local) pour rester correcte
sous un serveur ASGI/async futur. Positionnée par
`ParoisseCouranteMiddleware` au début de chaque requête et réinitialisée à
la fin — voir apps/comptes/middleware.py.
"""

from contextvars import ContextVar

_paroisse_courante: ContextVar = ContextVar("paroisse_courante", default=None)


def definir_paroisse_courante(paroisse):
    return _paroisse_courante.set(paroisse)


def obtenir_paroisse_courante():
    return _paroisse_courante.get()


def reinitialiser_paroisse_courante(jeton):
    _paroisse_courante.reset(jeton)
