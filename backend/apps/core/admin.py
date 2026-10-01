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
    HistoricoGarantiaMensal,
    PecaGlobus,
    VeiculoGlobus,
    FornecedorGlobus,
    CompraGlobus,
    SyncLog,
)

admin.site.register(Usuario)
admin.site.register(Fornecedor)
admin.site.register(Veiculo)
admin.site.register(Peca)
admin.site.register(NotaFiscal)
admin.site.register(Garantia)
admin.site.register(EventoGarantia)
admin.site.register(Anexo)
admin.site.register(HistoricoGarantiaMensal)
admin.site.register(PecaGlobus)
admin.site.register(VeiculoGlobus)
admin.site.register(FornecedorGlobus)
admin.site.register(CompraGlobus)
admin.site.register(SyncLog)
