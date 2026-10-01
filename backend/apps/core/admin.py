from django.contrib import admin
from .models import (
    Usuario,
    Fornecedor,
    Veiculo,
    Peca,
    NotaFiscal,
    Garantia,
    EventoGarantia,
    Anexo,
)

admin.site.register(Usuario)
admin.site.register(Fornecedor)
admin.site.register(Veiculo)
admin.site.register(Peca)
admin.site.register(NotaFiscal)
admin.site.register(Garantia)
admin.site.register(EventoGarantia)
admin.site.register(Anexo)
