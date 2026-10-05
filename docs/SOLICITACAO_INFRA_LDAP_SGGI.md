# SGGI — Pedido à infraestrutura

## Em poucas palavras

Estamos desenvolvendo o sistema **SGGI** (Sistema de Gestão de Garantias Improcedentes).

Queremos que as pessoas entrem no sistema com a **mesma conta e senha do computador/domínio** (Samba/AD), em vez de criar senha nova só para o SGGI.

Os dados do sistema (garantias, cadastros, etc.) continuam salvos no **MariaDB** da aplicação.  
O Samba/AD serve **somente para autenticar** (confirmar se o usuário e a senha estão corretos).

**Importante:** neste projeto **não usamos Oracle** e **não usamos Globus**.

---

## Por que estamos pedindo ajuda da infraestrutura?

Porque o servidor da aplicação precisa:

1. conseguir **falar com o Samba** de forma segura (LDAPS);
2. **confiar no certificado** do Samba;
3. ter uma **conta técnica só de leitura** para achar o usuário no diretório.

Sem isso, o login corporativo não funciona.

---

## Como o login vai funcionar (passo a passo)

1. A pessoa abre o SGGI e digita o **login do domínio** e a **senha do domínio**.
2. O SGGI pergunta ao Samba: “essa senha está correta?”.
3. Se o Samba disser que sim, a pessoa entra no sistema.
4. Se estiver errado, o acesso é negado.
5. A senha **não fica gravada** no banco do SGGI.

### Quem pode logar?

- **Qualquer usuário do domínio** que for autorizado a usar o SGGI.
- Cada um usa a **própria conta** (não é um login compartilhado).
- Exemplo de formato: `nome.sobrenome`  
  (isso é só exemplo — não é exclusivo de uma pessoa).

---

## O que cada sistema faz

| Sistema | Função no SGGI |
|---------|----------------|
| **MariaDB** | Guarda as informações do sistema (garantias, cadastros, perfil de acesso na aplicação) |
| **Samba / AD (LDAP)** | Confirma se o usuário e a senha do domínio estão corretos |
| **Oracle / Globus** | **Não entra** neste escopo |

---

## Servidores envolvidos

| Função | Servidor | IP |
|--------|----------|-----|
| Onde roda o SGGI | `srv-af-des01` | `192.168.0.100` |
| Controlador de domínio Samba | `srv-rd-ucs01` | `10.1.1.40` |
| Controlador de domínio Samba | `srv-rd-ucs02` | `10.1.1.41` |
| Domínio da empresa | `grbf.dom` | — |

Em resumo: o SGGI roda no `srv-af-des01` (Docker) e se conecta aos Samba (`ucs01` / `ucs02`) só para validar login.

### Status de rede (já testado no SRV-AF-DES01)

- DNS dos DCs: OK  
- LDAPS 636 no host: OK (ucs01 e ucs02)  
- LDAPS 636 **de dentro do container backend**: OK (ucs01 e ucs02)  
- NTP: OK  

A aplicação **não altera** o Samba (sem criar usuário/grupo/GPO/DNS).

---

## Solicitação a Infraestrutura

### 1) Porta 636 (LDAPS) — provavelmente já OK

- **De onde:** `srv-af-des01` (incluindo containers Docker)
- **Para onde:** `srv-rd-ucs01` e `srv-rd-ucs02`
- **Porta:** `636/TCP`
- Testes de conectividade TCP já passaram; confirmar se a regra de firewall fica documentada/permanente.

### 2) Enviar a CA raiz UCS (certificado)

- **Para quê:** o **container** do SGGI precisa confiar no certificado do Samba
- **Onde colocar:** arquivo `ucs-ca.crt` em `/var/www/sggi/certs/` (montado no container em `/certs/ucs-ca.crt`)
- Sem a CA, o login LDAPS pode falhar por erro de certificado.

### 3) Criar uma conta de serviço só de leitura

- **Sugestão de nome:** `svc-sggi-ldap`
- **Permissão:** somente leitura (localizar usuário no AD)
- **Não precisa:** permissão de administrador
- **Para quê:** a aplicação usa essa conta para achar o usuário no diretório e depois validar a senha dele

Essa conta **não substitui** o login das pessoas. Cada usuário continua entrando com a própria senha.

---

## Uma confirmação rápida

Qual formato de login devemos usar para **todos** os usuários?

- `nome.sobrenome`  
  **ou**
- `nome.sobrenome@grbf.dom`

Precisamos alinhar isso para o sistema aceitar o mesmo padrão do domínio.

---

## O que NÃO estamos pedindo agora

Para evitar trabalho desnecessário neste momento, **não precisamos** de:

- Oracle / Globus
- SSO com Kerberos
- criação de SPN / keytab
- alteração de GPO
- criação de grupos de permissão no AD (isso pode ser uma fase futura)

Na fase atual, o **perfil dentro do SGGI** (quem pode cadastrar, consultar, etc.) continua sendo controlado na própria aplicação (MariaDB).

---

## Contato

Fabiano Freitas — desenvolvimento SGGI
