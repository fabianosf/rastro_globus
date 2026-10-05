# Checklist — homologação login LDAP (SGGI)

Host: `SRV-AF-DES01` · Path: `/var/www/sggi`  
Escopo: autenticação Samba/LDAPS + dados no MariaDB. **Não altera** o Samba.

## Pré-requisitos

- [ ] Rede OK (já validado): LDAPS 636 host + container → `10.1.1.40` e `10.1.1.41`
- [ ] CA UCS em `certs/ucs-ca.crt` no servidor
- [ ] Conta serviço somente leitura (`svc-sggi-ldap` ou equivalente) no `.env`
- [ ] Formato de login confirmado (padrão: `sAMAccountName` = `nome.sobrenome`)
- [ ] Código com LDAP deployado (`docker compose build backend && up -d`)

## Configuração (.env)

```env
AD_LDAP_ENABLED=1
AD_LDAP_URI=ldaps://srv-rd-ucs01.grbf.dom:636
AD_LDAP_URI_FAILOVER=ldaps://srv-rd-ucs02.grbf.dom:636
AD_LDAP_BASE_DN=DC=grbf,DC=dom
AD_LDAP_BIND_DN=...
AD_LDAP_BIND_PASSWORD=...
AD_LDAP_USER_FILTER=(sAMAccountName=%(user)s)
AD_LDAP_CA_CERT_PATH=/certs/ucs-ca.crt
AD_LDAP_REQUIRE_CERT=demand
```

```bash
cd /var/www/sggi
docker compose build backend
docker compose up -d backend
docker compose exec backend ls -l /certs/ucs-ca.crt
```

## Testes

### 1) Flag desligada — login local (emergência)

- [ ] `AD_LDAP_ENABLED=0`, restart backend
- [ ] Login `admin` / senha local seed → OK
- [ ] JWT retornado; app abre

### 2) Flag ligada — usuário de domínio

- [ ] `AD_LDAP_ENABLED=1`, restart backend
- [ ] Login com conta corporativa (`nome.sobrenome` + senha Samba) → OK
- [ ] Usuário novo aparece no MariaDB com `perfil=direcao` (ajustar no admin se precisar)
- [ ] Usuário já existente mantém o `perfil` anterior

### 3) Fallback admin local com LDAP ligado

- [ ] Login `admin` local ainda funciona (ModelBackend)

### 4) Negativos

- [ ] Senha errada → 401 sem vazar detalhes
- [ ] Usuário inexistente no AD → 401
- [ ] Logs do backend **não** contêm senha

## Rollback rápido

```env
AD_LDAP_ENABLED=0
```

```bash
docker compose up -d backend
```

Volta ao login só com senha MariaDB.
