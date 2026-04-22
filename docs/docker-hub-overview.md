# Burn Rate

Burn Rate es una aplicación familiar autohospedada para planear y controlar el gasto de la casa. Permite registrar presupuestos mensuales por categoría, gastos, cuentas de pago, cargos recurrentes y compras a meses sin intereses.

Está pensada para instalarse detrás de una VPN, red privada o reverse proxy con TLS. No busca ser una aplicación pública abierta a internet.

## Imagen

```bash
docker pull loomitz/burnrate:v0.1.11
```

También está disponible:

```bash
docker pull loomitz/burnrate:latest
```

La imagen soporta:

- `linux/amd64`
- `linux/arm64`

## Qué incluye

- Aplicación Vue servida desde Django bajo el mismo origen.
- API Django + Django REST Framework.
- Gunicorn como servidor de aplicación.
- WhiteNoise para archivos estáticos.
- PostgreSQL como base de datos persistente.
- Migraciones automáticas al arrancar.
- Revisión inicial de conexión, migraciones y configuración mínima antes del primer admin.
- Flujo de bienvenida para crear el primer administrador.
- Invitaciones para agregar más usuarios de la casa.
- Envío de invitaciones por SMTP si hay credenciales configuradas.
- Link copiable de invitación aunque no exista SMTP.
- Sesiones autorrenovables.
- Compras a meses con fecha del primer pago, cantidad de meses y redondeo del pago requerido al siguiente peso.
- Endpoint `/healthz/` para healthchecks.
- Categorías mensuales con historial de excedentes y categorías acumulables con saldo global.

## Instalación rápida con Docker Compose

Crea un archivo `docker-compose.yml`:

```yaml
services:
  app:
    image: loomitz/burnrate:v0.1.11
    environment:
      DB_NAME: ${DB_NAME:-burn_rate}
      DB_USER: ${DB_USER:-burn_rate}
      DB_PASSWORD: ${DB_PASSWORD:?configura DB_PASSWORD}
      DB_HOST: db
      DB_PORT: 5432

      DJANGO_SECRET_KEY: ${DJANGO_SECRET_KEY:?configura DJANGO_SECRET_KEY}
      DJANGO_DEBUG: "false"
      DJANGO_ALLOWED_HOSTS: ${DJANGO_ALLOWED_HOSTS:-localhost,127.0.0.1}
      DJANGO_CSRF_TRUSTED_ORIGINS: ${DJANGO_CSRF_TRUSTED_ORIGINS:-http://localhost:8000,http://127.0.0.1:8000}

      DJANGO_SESSION_COOKIE_AGE: ${DJANGO_SESSION_COOKIE_AGE:-2592000}
      DJANGO_SESSION_SAVE_EVERY_REQUEST: "true"
      DJANGO_SESSION_COOKIE_SAMESITE: Lax
      DJANGO_CSRF_COOKIE_SAMESITE: Lax
      DJANGO_SESSION_COOKIE_SECURE: ${DJANGO_SESSION_COOKIE_SECURE:-false}
      DJANGO_CSRF_COOKIE_SECURE: ${DJANGO_CSRF_COOKIE_SECURE:-false}
      DJANGO_TRUST_X_FORWARDED_PROTO: ${DJANGO_TRUST_X_FORWARDED_PROTO:-false}

      INVITATION_TTL_DAYS: ${INVITATION_TTL_DAYS:-14}
      BURN_RATE_PUBLIC_URL: ${BURN_RATE_PUBLIC_URL:-http://localhost:8000}
      BURN_RATE_FRONTEND_URL: ${BURN_RATE_FRONTEND_URL:-http://localhost:8000}

      EMAIL_HOST: ${EMAIL_HOST:-}
      EMAIL_PORT: ${EMAIL_PORT:-587}
      EMAIL_HOST_USER: ${EMAIL_HOST_USER:-}
      EMAIL_HOST_PASSWORD: ${EMAIL_HOST_PASSWORD:-}
      EMAIL_USE_TLS: ${EMAIL_USE_TLS:-true}
      EMAIL_USE_SSL: ${EMAIL_USE_SSL:-false}
      DEFAULT_FROM_EMAIL: ${DEFAULT_FROM_EMAIL:-}

      RUN_MIGRATIONS: "true"
      COLLECT_STATIC: "true"
      WAIT_FOR_DB: "true"
      GUNICORN_WORKERS: ${GUNICORN_WORKERS:-3}
      GUNICORN_TIMEOUT: ${GUNICORN_TIMEOUT:-60}
    ports:
      - "${APP_BIND:-127.0.0.1}:${APP_PORT:-8000}:8000"
    depends_on:
      db:
        condition: service_healthy
    restart: unless-stopped

  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: ${DB_NAME:-burn_rate}
      POSTGRES_USER: ${DB_USER:-burn_rate}
      POSTGRES_PASSWORD: ${DB_PASSWORD:?configura DB_PASSWORD}
    volumes:
      - burn_rate_postgres:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER:-burn_rate} -d ${DB_NAME:-burn_rate}"]
      interval: 5s
      timeout: 5s
      retries: 10
    restart: unless-stopped

volumes:
  burn_rate_postgres:
```

Crea un archivo `.env` junto al compose:

```env
APP_BIND=127.0.0.1
APP_PORT=8000

DB_NAME=burn_rate
DB_USER=burn_rate
DB_PASSWORD=usa-una-password-real

DJANGO_SECRET_KEY=usa-un-secreto-largo-y-aleatorio
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
DJANGO_CSRF_TRUSTED_ORIGINS=http://localhost:8000,http://127.0.0.1:8000

BURN_RATE_PUBLIC_URL=http://localhost:8000
BURN_RATE_FRONTEND_URL=http://localhost:8000
```

Levanta la aplicación:

```bash
docker compose up -d
```

Abre:

```text
http://127.0.0.1:8000
```

## Primer uso

En una base de datos limpia, Burn Rate primero revisa que la conexión a PostgreSQL, las migraciones y la configuración inicial estén listas. Si algo falla, muestra una lista sencilla con el punto bloqueado y un botón para volver a revisar después de corregir Docker Compose o reiniciar el contenedor.

Cuando esa revisión pasa, Burn Rate muestra el flujo de bienvenida para crear el primer administrador desde el navegador.

Ese primer usuario captura:

- Email
- Nombre completo
- Nombre visible dentro de la app
- Password

Después de crear el primer admin, se puede entrar a `Ajustes > Invitar` para generar invitaciones a otras personas de la casa. El admin solo captura el email y si la persona tendrá permisos de admin; la persona invitada completa su nombre, alias visible y password al aceptar.

## Invitaciones

Las invitaciones siempre generan un link copiable.

Si además configuras SMTP y `BURN_RATE_PUBLIC_URL`, Burn Rate puede enviar el email de invitación automáticamente.

Variables SMTP opcionales:

```env
EMAIL_HOST=smtp.tu-proveedor.com
EMAIL_PORT=587
EMAIL_HOST_USER=usuario-smtp
EMAIL_HOST_PASSWORD=password-smtp
EMAIL_USE_TLS=true
EMAIL_USE_SSL=false
DEFAULT_FROM_EMAIL=Burn Rate <burnrate@tu-dominio.local>
```

## Healthcheck

La imagen expone:

```text
/healthz/
```

Ejemplo:

```bash
curl http://127.0.0.1:8000/healthz/
```

Respuesta esperada:

```json
{"status":"ok"}
```

## Actualización

Burn Rate está diseñado para actualizarse reemplazando el contenedor. Los datos viven en PostgreSQL.

```bash
docker compose pull app
docker compose up -d
```

Si `RUN_MIGRATIONS=true`, el contenedor aplica migraciones pendientes al arrancar.

## Seguridad

Burn Rate está pensado para uso familiar autohospedado detrás de VPN o red privada.

Recomendaciones:

- No expongas PostgreSQL al host ni a internet.
- Usa una `DJANGO_SECRET_KEY` larga y privada.
- Usa HTTPS si lo expones detrás de reverse proxy.
- Activa cookies seguras cuando uses HTTPS:

```env
DJANGO_SESSION_COOKIE_SECURE=true
DJANGO_CSRF_COOKIE_SECURE=true
DJANGO_TRUST_X_FORWARDED_PROTO=true
```

La imagen `v0.1.11` fue revisada y publicada para `linux/amd64` y `linux/arm64`.

## Código fuente

Repositorio:

```text
https://github.com/loomitz/burn-rate
```

## Tags

- `v0.1.11`: colores e iconos de categoría en compromisos recurrentes y compras a meses.
- `v0.1.10`: ajustes visuales de Plan y Cargos, compromisos segmentados en categorías, formulario homogéneo de cargos y resúmenes por tab.
- `v0.1.9`: categorías acumulables, historial de excedentes por ciclo y cambios de presupuesto con fecha efectiva.
- `v0.1.8`: flujo de compras a meses por fecha del primer pago y meses, redondeo requerido por defecto y edición de categoría.
- `v0.1.7`: redondeo opcional del pago requerido en compras a meses y soporte multi-arquitectura.
- `v0.1.6`: edición segura de compromisos, eliminación solo para admins, logo de documentación actualizado y soporte multi-arquitectura.
- `v0.1.5`: MSI iniciadas, comercios compartidos en compromisos y soporte multi-arquitectura.
- `v0.1.4`: invitaciones simplificadas, edición de categorías, edición de cuentas/personas y soporte multi-arquitectura.
- `v0.1.3`: invitaciones simplificadas, edición de categorías y soporte multi-arquitectura.
- `latest`: apunta a la versión estable más reciente.
