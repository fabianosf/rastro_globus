# RastroGlobus — Especificação completa para o Cursor

Use este arquivo como fonte da verdade para construir a aplicação.

**Produto:** RastroGlobus (RG)  
**Objetivo:** rastrear o ciclo de garantia de peças da frota **sem movimentar estoque**.  
**Stack obrigatória:** React (Vite + TypeScript + Tailwind) + Django + Django REST Framework.  
**Banco no MVP:** SQLite.  
**Idioma da interface:** Português do Brasil.

---

## 0. Como o Cursor deve trabalhar

1. Leia este arquivo inteiro antes de gerar código.
2. Não invente módulo de estoque. RastroGlobus **não dá entrada, não dá baixa, não altera saldo**.
3. Não integre o ERP Globo no MVP. Apenas campos de espelho (número de NF / local de garantia).
4. Entregue um monorepo utilizável:
   - `backend/` Django pronto para `migrate` + seed
   - `frontend/` Vite React pronto para login e telas
5. Siga os nomes, status, cores e rotas abaixo sem improvisar.
6. Código em inglês (variáveis/classes). Textos de UI em português.
7. Após gerar, rode o que for possível e corrija erro de import/migração.

Comando alvo no final:

```bash
# backend
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed
python manage.py runserver

# frontend
cd frontend
npm install
npm run dev
```

Usuário seed: `admin` / `admin123`

---

## 1. Problema (origem da reunião)

Hoje o fluxo é:

1. Peça entra por NF de compra (Globo).
2. Peça é aplicada no veículo (baixa).
3. Se a mesma peça é baixada de novo dentro da garantia (dias/km), gera laudo.
4. Peça vai ao fornecedor/fabricante com **NF de remessa**.
5. Volta com **NF de retorno + laudo PDF**.
6. Resultado possível:
   - **Procedente** — entra no Globo no local de garantia (peça nova / crédito).
   - **Improcedente** — **não entra no estoque**. Fica só na planilha Excel.
   - **Cortesia comercial** — fornecedor cede sem admitir defeito. Também não é fluxo padrão de estoque.

Dor:

- Improcedente e cortesia não ficam no sistema.
- Não há associação NF remessa ↔ NF retorno.
- Relatório por peça, veículo, casa, fornecedor e status é manual.
- Excel pode ser editado/apagado por qualquer um.
- Gestão não consegue ver “garantias do ano” num clique.

RastroGlobus resolve o **processo**. O Globo continua dono do **estoque**.

Frase de produto: *O Globo controla estoque. O RastroGlobus controla o rastro da garantia.*

---

## 2. Regras de negócio (obrigatórias)

1. Status válidos:
   - `aberta` — laudo/solicitação gerada
   - `enviada` — NF de remessa emitida
   - `em_analise` — fornecedor analisando
   - `procedente`
   - `improcedente`
   - `cortesia`
   - `cancelada`

2. Protocolo único: `GAR-AAAA-000001` (ano + sequencial).

3. Toda mudança de status cria um `EventoGarantia` (timeline). Eventos **nunca** são apagados.

4. `improcedente` e `cortesia` **nunca** preenchem lógica de estoque. Campo `nf_entrada_globo` só faz sentido em `procedente`.

5. Para ir para `enviada` ou `em_analise`: exigir `nota_remessa` (número).

6. Para encerrar como `procedente`: exigir NF retorno **ou** justificativa + laudo.

7. Para encerrar como `improcedente`: exigir laudo resumido ou PDF + motivo.

8. Para `cortesia`: exigir observação comercial.

9. Perfis:
   - `oficina` — cria garantia, anexa, vê as próprias/todas do MVP
   - `compras` — vincula NFs, anexa laudo do fornecedor
   - `manutencao` — fecha status final
   - `direcao` — somente leitura + export
   - `admin` — tudo

10. No MVP todos os perfis autenticados podem ver a lista (empresa interna). Direção não altera status.

11. Filtros mínimos da lista: status, peça, veículo, fornecedor, ano.

12. Dashboard mostra:
    - contagem por status no ano
    - valor procedente / improcedente / em aberto
    - ranking de peças
    - veículos com 2+ garantias no período
    - itens parados > 45 dias

---

## 3. Arquitetura

```
RastroGlobus (satélite)
        │
        ├─ cadastros: veiculo, peca, fornecedor, usuario
        ├─ garantia + timeline + anexos
        ├─ notas fiscais (compra, remessa, retorno)
        └─ relatórios
                │
                └── NÃO fala com estoque do Globo no MVP
                    (só campo texto nf_entrada_globo se procedente)
```

Backend: Django 5 + DRF + SimpleJWT  
Frontend: Vite + React 18 + TypeScript + React Router + Tailwind  
Auth: JWT no header `Authorization: Bearer <token>`  
CORS: `http://localhost:5173`  
Media: `backend/media/` (laudos, notas, anexos)

---

## 4. Estrutura de pastas

```
rastroglobus/
├── README.md
├── backend/
│   ├── manage.py
│   ├── requirements.txt
│   ├── rastroglobus/          # projeto Django
│   │   ├── __init__.py
│   │   ├── settings.py
│   │   ├── urls.py
│   │   ├── wsgi.py
│   │   └── asgi.py
│   └── apps/
│       └── core/
│           ├── __init__.py
│           ├── apps.py
│           ├── models.py
│           ├── admin.py
│           ├── serializers.py
│           ├── views.py
│           ├── urls.py
│           ├── permissions.py
│           ├── services.py
│           ├── management/commands/seed.py
│           └── migrations/
└── frontend/
    ├── package.json
    ├── vite.config.ts
    ├── tailwind.config.js
    ├── index.html
    └── src/
        ├── main.tsx
        ├── App.tsx
        ├── index.css
        ├── api/client.ts
        ├── auth/AuthContext.tsx
        ├── layouts/AppLayout.tsx
        ├── pages/
        │   ├── Login.tsx
        │   ├── Dashboard.tsx
        │   ├── GarantiasList.tsx
        │   ├── GarantiaNova.tsx
        │   ├── GarantiaFicha.tsx
        │   └── Relatorios.tsx
        └── components/
            ├── BadgeStatus.tsx
            ├── KpiCard.tsx
            └── Timeline.tsx
```

Se preferir app Django na raiz `backend/core/` em vez de `apps/core/`, mantenha consistente.

---

## 5. Models Django (implementar exatamente)

Arquivo: `backend/apps/core/models.py`

```python
from django.db import models
from django.contrib.auth.models import AbstractUser


class Usuario(AbstractUser):
    class Perfil(models.TextChoices):
        OFICINA = "oficina", "Oficina / Depósito"
        COMPRAS = "compras", "Compras"
        MANUTENCAO = "manutencao", "Manutenção"
        DIRECAO = "direcao", "Direção"
        ADMIN = "admin", "Administrador"

    perfil = models.CharField(max_length=20, choices=Perfil.choices, default=Perfil.OFICINA)
    telefone = models.CharField(max_length=20, blank=True)


class Fornecedor(models.Model):
    razao_social = models.CharField(max_length=200)
    nome_fantasia = models.CharField(max_length=200, blank=True)
    cnpj = models.CharField(max_length=18, unique=True)
    contato = models.CharField(max_length=120, blank=True)
    email = models.EmailField(blank=True)
    telefone = models.CharField(max_length=20, blank=True)
    ativo = models.BooleanField(default=True)

    def __str__(self):
        return self.nome_fantasia or self.razao_social


class Veiculo(models.Model):
    codigo = models.CharField(max_length=30, unique=True)  # ex 47620
    placa = models.CharField(max_length=10, blank=True)
    descricao = models.CharField(max_length=200, blank=True)
    casa = models.CharField(max_length=80, blank=True)  # unidade / garagem
    ativo = models.BooleanField(default=True)

    def __str__(self):
        return self.codigo


class Peca(models.Model):
    codigo_interno = models.CharField(max_length=40, unique=True)
    descricao = models.CharField(max_length=255)
    garantia_dias = models.PositiveIntegerField(default=365)
    garantia_km = models.PositiveIntegerField(null=True, blank=True)
    ativo = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.codigo_interno} - {self.descricao}"


class NotaFiscal(models.Model):
    class Tipo(models.TextChoices):
        COMPRA = "compra", "Compra / entrada original"
        REMESSA = "remessa", "Saída para garantia"
        RETORNO = "retorno", "Retorno do fornecedor"
        ENTRADA_PROCEDENTE = "entrada_procedente", "Espelho Globo (procedente)"

    numero = models.CharField(max_length=30)
    serie = models.CharField(max_length=10, blank=True)
    tipo = models.CharField(max_length=30, choices=Tipo.choices)
    fornecedor = models.ForeignKey(Fornecedor, on_delete=models.PROTECT, null=True, blank=True)
    data_emissao = models.DateField()
    valor = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    chave_nfe = models.CharField(max_length=44, blank=True)
    arquivo_pdf = models.FileField(upload_to="notas/", blank=True, null=True)
    observacao = models.TextField(blank=True)

    class Meta:
        unique_together = ("numero", "serie", "tipo")

    def __str__(self):
        return f"NF {self.numero} ({self.tipo})"


class Garantia(models.Model):
    class Status(models.TextChoices):
        ABERTA = "aberta", "Aberta / laudo gerado"
        ENVIADA = "enviada", "Enviada ao fornecedor"
        EM_ANALISE = "em_analise", "Em análise"
        PROCEDENTE = "procedente", "Procedente"
        IMPROCEDENTE = "improcedente", "Improcedente"
        CORTESIA = "cortesia", "Cortesia comercial"
        CANCELADA = "cancelada", "Cancelada"

    protocolo = models.CharField(max_length=20, unique=True)
    peca = models.ForeignKey(Peca, on_delete=models.PROTECT)
    veiculo = models.ForeignKey(Veiculo, on_delete=models.PROTECT)
    fornecedor = models.ForeignKey(Fornecedor, on_delete=models.PROTECT)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ABERTA)

    data_compra = models.DateField(null=True, blank=True)
    nota_compra = models.ForeignKey(
        NotaFiscal, on_delete=models.SET_NULL, null=True, blank=True, related_name="garantias_compra"
    )
    km_aplicacao = models.PositiveIntegerField(null=True, blank=True)
    data_primeira_baixa = models.DateField(null=True, blank=True)
    data_segunda_baixa = models.DateField(null=True, blank=True)
    requisicao_anterior = models.CharField(max_length=40, blank=True)
    requisicao_atual = models.CharField(max_length=40, blank=True)

    nota_remessa = models.ForeignKey(
        NotaFiscal, on_delete=models.SET_NULL, null=True, blank=True, related_name="garantias_remessa"
    )
    data_envio = models.DateField(null=True, blank=True)
    nota_retorno = models.ForeignKey(
        NotaFiscal, on_delete=models.SET_NULL, null=True, blank=True, related_name="garantias_retorno"
    )
    data_retorno = models.DateField(null=True, blank=True)

    valor_peca = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    laudo_pdf = models.FileField(upload_to="laudos/", blank=True, null=True)
    laudo_resumo = models.TextField(blank=True)
    motivo_improcedente = models.TextField(blank=True)
    nf_entrada_globo = models.CharField(max_length=30, blank=True)

    criado_por = models.ForeignKey(Usuario, on_delete=models.PROTECT, related_name="garantias_criadas")
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    observacoes = models.TextField(blank=True)

    class Meta:
        ordering = ["-criado_em"]


class EventoGarantia(models.Model):
    garantia = models.ForeignKey(Garantia, on_delete=models.CASCADE, related_name="eventos")
    usuario = models.ForeignKey(Usuario, on_delete=models.PROTECT)
    data = models.DateTimeField(auto_now_add=True)
    status_anterior = models.CharField(max_length=20, blank=True)
    status_novo = models.CharField(max_length=20)
    descricao = models.TextField()
    arquivo = models.FileField(upload_to="eventos/", blank=True, null=True)

    class Meta:
        ordering = ["data"]


class Anexo(models.Model):
    garantia = models.ForeignKey(Garantia, on_delete=models.CASCADE, related_name="anexos")
    arquivo = models.FileField(upload_to="anexos/")
    descricao = models.CharField(max_length=200, blank=True)
    enviado_por = models.ForeignKey(Usuario, on_delete=models.PROTECT)
    enviado_em = models.DateTimeField(auto_now_add=True)
```

`AUTH_USER_MODEL = "core.Usuario"`

---

## 6. Serviços de domínio

Arquivo `services.py`:

```python
def proximo_protocolo() -> str:
    # GAR-2026-000001 com base no ano corrente e último protocolo

def pode_espelhar_globo(status: str) -> bool:
    return status == "procedente"

def mudar_status(garantia, novo_status, usuario, descricao, **extras):
    # valida transições
    # grava EventoGarantia
    # se procedente e nf_entrada_globo informado, só salva texto
    # NUNCA cria movimento de estoque
```

Transições permitidas:

```
aberta → enviada | cancelada
enviada → em_analise | cancelada
em_analise → procedente | improcedente | cortesia
procedente / improcedente / cortesia → (fim; só admin pode cancelar)
```

---

## 7. API

Base: `http://localhost:8000/api/`

### Auth
- `POST /api/auth/login/` `{username, password}` → `{access, refresh, user}`
- `POST /api/auth/refresh/`
- `GET /api/auth/me/`

### Cadastros
- `GET/POST /api/fornecedores/`
- `GET/POST /api/veiculos/`
- `GET/POST /api/pecas/`
- `GET /api/notas/`
- `POST /api/notas/` (multipart se PDF)

### Garantias
- `GET /api/garantias/` query: `status`, `peca`, `veiculo`, `fornecedor`, `ano`, `q`
- `POST /api/garantias/`
- `GET /api/garantias/{id}/`
- `PATCH /api/garantias/{id}/`
- `POST /api/garantias/{id}/status/` `{status, descricao, motivo_improcedente, nf_entrada_globo}`
- `POST /api/garantias/{id}/anexos/` multipart
- `POST /api/garantias/{id}/notas/` `{tipo, numero, serie, data_emissao, valor}`  
  tipos: `compra` | `remessa` | `retorno`

### Relatórios
- `GET /api/dashboard/?ano=2026`
- `GET /api/relatorios/resumo/?ano=2026`
- `GET /api/relatorios/ranking-pecas/?ano=2026`
- `GET /api/relatorios/ranking-veiculos/?ano=2026`
- `GET /api/relatorios/export.csv/?ano=2026`

Serializer da lista deve incluir:
`id, protocolo, peca_nome, veiculo_codigo, fornecedor_nome, nf_remessa, nf_retorno, status, valor_peca, criado_em, dias_aberta`

Ficha deve incluir `eventos[]` e `anexos[]`.

---

## 8. Settings Django (pontos críticos)

```python
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "corsheaders",
    "apps.core",
]
AUTH_USER_MODEL = "core.Usuario"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
CORS_ALLOW_ALL_ORIGINS = True  # MVP local
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
}
```

`requirements.txt`:

```
Django>=5.0,<6
djangorestframework
djangorestframework-simplejwt
django-cors-headers
Pillow
```

---

## 9. Seed (obrigatório)

Criar `python manage.py seed` com:

Usuários:
- admin / admin123 (perfil admin)
- manutencao / manut123 (manutencao)
- oficina / oficina123 (oficina)

Fornecedores:
- Distribuidor X — 00.000.000/0001-00
- Fabricante Y — 11.111.111/0001-11

Veículos:
- 47620 casa Matriz
- 47885 casa Matriz
- 47624 casa Matriz
- 46201 casa Anexo

Peças:
- EMB-0144 Embreagem — 365 dias
- CXA-0901 Caixa de marcha — 365 dias
- ALT-0330 Alternador — 365 dias
- BMB-0102 Bomba d'água — 365 dias

Garantias de exemplo (números da reunião):

| Protocolo | Peça | Veículo | Status | Valor | NFs |
|---|---|---|---|---|---|
| GAR-2026-0142 | Embreagem | 47620 | procedente | 1875 | remessa 88421 / retorno 5012 |
| GAR-2026-0138 | Caixa de marcha | 47885 | em_analise | 9600 | remessa 87990 / retorno vazio |
| GAR-2026-0131 | Alternador | 47624 | improcedente | 1840 | remessa 87002 / retorno 4988 |
| GAR-2026-0126 | Embreagem | 47620 | cortesia | 1875 | remessa 86810 / retorno 4971 |
| GAR-2026-0119 | Bomba d'água | 46201 | aberta | 890 | sem NFs |

Criar 2–3 eventos na timeline de cada uma.

---

## 10. Frontend — design system

Tema escuro:

```
--bg: #07111d
--panel: #0f2136
--line: #1c3a58
--text: #e8f1fb
--muted: #8aa4bd
--cyan: #22d3ee
--green: #34d399
--amber: #fbbf24
--red: #f87171
--violet: #a78bfa
```

Fonte: Inter.

Badges:
- aberta → ciano
- enviada / em_analise → âmbar
- procedente → verde
- improcedente → vermelho
- cortesia → violeta
- cancelada → cinza

Marca:
- Nome: **RastroGlobus**
- Sigla: **RG**
- Assinatura no login: “Rastro da garantia. Sem misturar com o estoque.”
- Logo: quadrado arredondado ciano com RG. Não usar globo terrestre.

Layout autenticado:
- sidebar esquerda 240px
- itens: Dashboard, Garantias, Nova garantia, Relatórios
- topo: título da página + usuário

---

## 11. Telas e rotas

| Rota | Página | Comportamento |
|---|---|---|
| `/login` | Login | username/senha → JWT → `/` |
| `/` | Dashboard | KPIs + ranking peças + veículos alerta |
| `/garantias` | Lista | filtros + tabela + clique abre ficha |
| `/garantias/nova` | Formulário | cria e vai para a ficha |
| `/garantias/:id` | Ficha | dados, NFs, timeline, ações de status, upload |
| `/relatorios` | Relatórios | tabela por status + botão export CSV |

### Login
Campos usuário e senha. Sem cadastro público.

### Nova garantia
Campos:
- veículo (select)
- peça (select)
- fornecedor (select)
- NF compra (texto)
- requisição anterior
- requisição atual
- km
- valor
- observação / defeito

Botão: **Gerar protocolo e laudo**

### Ficha
Mostrar aviso fixo se status != procedente:

> Estoque do Globo não deve ser movimentado neste status.

Ações:
- Anexar PDF
- Vincular NF remessa
- Vincular NF retorno
- Marcar procedente (se perfil permitir)
- Improcedente
- Cortesia

### Lista
Colunas: Protocolo, Peça, Veículo, Fornecedor, NF remessa, NF retorno, Status.

---

## 12. Frontend técnico

- `vite.config.ts` proxy `/api` → `http://localhost:8000`
- `src/api/client.ts` axios/fetch com token do localStorage
- `AuthContext` guarda user + token
- Rotas protegidas: se não logado, redirect `/login`
- Formulários controlados
- Sem biblioteca de UI pesada. Tailwind puro.
- Estados de loading e erro visíveis em português.

`package.json` deps:
`react react-dom react-router-dom`

devDeps:
`vite typescript @types/react @types/react-dom tailwindcss postcss autoprefixer`

---

## 13. README do repositório (gerar também)

Incluir:
- o que é RastroGlobus
- regra de não movimentar estoque
- como rodar backend e frontend
- usuários seed
- status do fluxo

---

## 14. Fora do escopo (não implementar agora)

- Integração API/arquivo com o Globo
- OCR de NF
- Assinatura digital
- App mobile nativo
- Multiempresa / SaaS billing
- Microserviços, Redis, Celery, Kubernetes
- AlphaLang / agentes

---

## 15. Critério de pronto (Definition of Done)

O Cursor só termina quando:

- [ ] `migrate` roda sem erro
- [ ] `seed` cria admin e 5 garantias
- [ ] login JWT funciona
- [ ] dashboard abre com números
- [ ] lista filtra por status
- [ ] nova garantia gera protocolo `GAR-AAAA-######`
- [ ] ficha mostra timeline
- [ ] mudar para improcedente **não** grava `nf_entrada_globo` obrigatório
- [ ] procedente permite informar `nf_entrada_globo` só como texto
- [ ] export CSV baixa arquivo
- [ ] UI em português, tema navy/ciano, marca RastroGlobus

---

## 16. Prompt curto se o Cursor pedir contexto

> Construa o monorepo RastroGlobus exatamente como RASTROGLOBUS-CURSOR-SPEC.md. Django + DRF + JWT + React Vite TS Tailwind. Não crie módulo de estoque. Improcedente e cortesia não movimentam saldo. Use os models, rotas, seed e cores do spec.

---

**Fim da especificação.**
