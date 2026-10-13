# Comandos — localizar e subir SGGI no SRV-AF-DES01

> **Nunca apagar `.env` nem `media/` (laudos e anexos).**

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

## 3) Atualizar o código (sem apagar a pasta)

Sempre faça backup de `.env` e `media/` antes:

```bash
cd /var/www/sggi
sudo tar -czf /var/backups/sggi-env-media-$(date +%Y%m%d%H%M).tar.gz .env media/
```

Com repositório Git já presente:

```bash
cd /var/www/sggi
git fetch origin
git reset --hard origin/main
```

Se a pasta **não** tiver `.git` (ou quiser instalação limpa), clone em pasta **nova** e preserve `.env` / `media/`:

```bash
cd /var/www
sudo git clone https://github.com/fabianosf/rastro_globus.git sggi-new
# copiar segredos e anexos da pasta antiga (se existir)
sudo cp sggi/.env sggi-new/.env 2>/dev/null || true
sudo cp -a sggi/media/. sggi-new/media/ 2>/dev/null || true
# só depois de validar, troque o symlink/nome (sem apagar media/.env)
# sudo mv sggi sggi-old && sudo mv sggi-new sggi
```

## 4) Restaurar / conferir .env

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
