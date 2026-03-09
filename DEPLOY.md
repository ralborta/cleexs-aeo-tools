# Deploy: Vercel (frontend) + Railway (backend + MySQL)

Proyecto completo: frontend Next.js en **Vercel** y backend FastAPI + MySQL en **Railway**.

---

## 1. Backend en Railway

### 1.1 Crear proyecto en Railway

1. Entra en [railway.app](https://railway.app) e inicia sesión.
2. **New Project** → **Deploy from GitHub repo** (o "Empty Project" y sube el código después).
3. Si usas repo: selecciona este repo y como **Root Directory** pon: `backend`.

### 1.2 Añadir MySQL en Railway

1. En el mismo proyecto: **+ New** → **Database** → **MySQL**.
2. Railway crea el servicio y expone variables: `MYSQL_URL` o `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_DATABASE`.
3. Si tu app usa `MYSQL_HOST`, `MYSQL_PORT`, etc., enlaza esas variables al servicio del backend (Variables del servicio backend → **Add variable** y elegir las de MySQL).

### 1.3 Variables del backend

En el servicio **backend** (FastAPI), en **Variables**, añade:

| Variable | Descripción |
|----------|-------------|
| `OPENAI_API_KEY` | API key de OpenAI |
| `GEMINI_API_KEY` | API key de Google AI (Gemini) |
| `PERPLEXITY_API_KEY` | API key de Perplexity |
| `SERP_API_KEY` | API key de SerpAPI |
| `MYSQL_HOST` | Host de MySQL (desde add-on) |
| `MYSQL_PORT` | Puerto (ej. 3306) |
| `MYSQL_DATABASE` | Nombre de la base |
| `MYSQL_USER` | Usuario MySQL |
| `MYSQL_PASSWORD` | Contraseña MySQL |

(Opcional: `WEBHOOK_URL` para notificaciones.)

Referencia de nombres en código: `backend/.env.example`.

### 1.4 Build y deploy

Opciones para que el build en Railway funcione:

- **Recomendado (evita "Error reading backend"):** Builder **Dockerfile** y **Root Directory vacío** (raíz del repo). En la raíz hay un `Dockerfile` que copia `backend/` y construye la app. Así Railway no tiene que "leer" el directorio `backend` como raíz.
- **Alternativa:** Builder **Dockerfile** y Root Directory **`backend`**. Usa el `Dockerfile` que está dentro de `backend/`.
- **Railpack:** Root Directory **`backend`** y builder por defecto. Si falla "Error creating build plan with Railpack", usa una de las opciones con Dockerfile de arriba.

### 1.5 Dominio público

1. En el servicio backend: **Settings** → **Networking** → **Generate Domain**. Copia la URL (ej. `https://xxx.up.railway.app`).
2. Esa URL es tu **API base** para el frontend (Vercel).

---

## 2. Frontend en Vercel

### 2.1 Conectar repo

1. Entra en [vercel.com](https://vercel.com) y conecta el mismo repo del proyecto.
2. Al crear el proyecto, en **Root Directory** elige: `frontend`.

### 2.2 Variables de entorno (evitar CORS con proxy)

En el proyecto de Vercel: **Settings** → **Environment Variables**:

| Name | Value |
|------|--------|
| `NEXT_PUBLIC_API_URL` | Dejar **vacío** (empty) para usar proxy same-origin y evitar CORS. |
| `BACKEND_URL` | URL del backend en Railway (ej. `https://cleexs-aeo-tools-production.up.railway.app`) |

El frontend llama a `/api/...` (mismo origen); Next.js reescribe esas peticiones a `BACKEND_URL/api/...`. Sin `/` al final en `BACKEND_URL`. Aplícalo a Production (y Preview si quieres).

### 2.3 Deploy

1. **Deploy** (o push a la rama conectada).
2. Cuando termine, la URL de Vercel (ej. `https://tu-proyecto.vercel.app`) será el frontend que llama al backend en Railway.

---

## 3. Comprobar que funciona

1. Abre la URL de Vercel.
2. Pega una URL (ej. `https://ejemplo.com`) y pulsa **Analizar todo**.
3. Si el backend está bien configurado y con API keys, deberías ver resultados (incluidas las herramientas que usan IA cuando las keys estén definidas).
4. Si algo falla: en el navegador (F12 → Network) revisa que las peticiones vayan a `NEXT_PUBLIC_API_URL` y que no den CORS/4xx/5xx.

---

## 4. Resumen de URLs

- **Frontend:** `https://tu-proyecto.vercel.app` (Vercel).
- **Backend:** `https://xxx.up.railway.app` (Railway) → esta va en `NEXT_PUBLIC_API_URL`.

CORS en el backend ya permite `*`; si en producción quieres restringir, cambia `allow_origins` en `main.py` a la URL del frontend en Vercel.
