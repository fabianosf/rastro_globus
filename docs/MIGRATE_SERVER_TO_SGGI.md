# Renomear deploy no servidor: rastroglobus → sggi

Host: `SRV-AF-DES01`  
Objetivo: pasta e projeto Docker passam a se chamar **sggi**.  
O pacote Django interno `rastroglobus` (Python) permanece — só o nome de deploy muda.

## 1) Parar containers atuais

```bash
cd /var/www/rastroglobus
docker compose down
```

## 2) Renomear pasta

```bash
sudo mv /var/www/rastroglobus /var/www/sggi
cd /var/www/sggi
```

## 3) Atualizar código e .env

```bash
git pull
```

No `.env`, mantenha o banco **já existente** se não for migrar dados:

```env
DB_NAME=rastroglobus
DB_USER=rastro
```

(ou, se for instalação nova / banco novo: `DB_NAME=sggi` / `DB_USER=sggi`)

## 4) Subir com o novo nome do projeto

O `docker-compose.yml` define `name: sggi` → containers ficam `sggi-backend-1`, etc.

```bash
docker compose up -d --build
docker compose ps
```

## 5) Conferir

- App: `http://srv-af-des01:8888`
- `docker compose ps` mostra projeto/serviço `sggi`
- Login local ainda funciona com `AD_LDAP_ENABLED=0`

## Observação sobre volumes Docker

Volumes nomeados antigos (`rastroglobus_db_data`, etc.) podem continuar existindo.  
Se após o rename o MariaDB subir **vazio**, associe o volume antigo ou restaure backup — não apague volumes sem backup.
