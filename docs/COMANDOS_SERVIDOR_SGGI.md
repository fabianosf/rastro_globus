# Comandos — localizar e subir SGGI no SRV-AF-DES01

## 1) Ver o que existe em /var/www

```bash
cd /var/www
ls -la
ls -la sggi 2>/dev/null || true
ls -la rastroglobus 2>/dev/null || true
```

## 2) Entrar na pasta do projeto

A pasta certa tem `docker-compose.yml`:

```bash
# tente sggi
cd /var/www/sggi && ls -la docker-compose.yml .env .git 2>&1

# se não existir, tente rastroglobus
cd /var/www/rastroglobus && ls -la docker-compose.yml .env .git 2>&1
```

## 3) Se a pasta existir mas NÃO tiver .git

Baixe/atualize o código do GitHub na pasta:

```bash
cd /var/www/sggi
# se não houver docker-compose.yml, o conteúdo pode estar incompleto
git clone https://github.com/fabianosf/rastro_globus.git .
# OU, se a pasta não estiver vazia:
# cd /var/www && sudo rm -rf sggi && sudo git clone https://github.com/fabianosf/rastro_globus.git sggi
```

## 4) Restaurar .env

Se o `.env` sumiu no rename, recrie a partir do exemplo e ajuste senhas/DB:

```bash
cd /var/www/sggi
cp .env.example .env
nano .env
```

Para **não perder o banco atual**, use:

```env
DB_NAME=rastroglobus
DB_USER=rastro
```

(e as senhas que já estavam no servidor)

## 5) Subir

```bash
cd /var/www/sggi
docker compose up -d --build
docker compose ps
```
