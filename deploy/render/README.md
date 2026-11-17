# Publicar la demo en Render (enlace permanente)

La demo publicada corre en **un solo contenedor**: la interfaz, la API (bajo `/api`) y una base SQLite cargada al
construir la imagen. Abre con el selector «Ver como» (`MODO_DEMO=true`, usuarios ficticios) y carga los casos
reales **sin su parte privada** (`CASOS_REALES_PRIVADOS=false`).

**Privacidad.** El repositorio es público, así que los CSV de la muestra no van en él. Entran a la imagen desde su
carpeta local (contexto `datos`), y por eso la imagen se sube a un registro **privado** (GitHub Container Registry).
Solo se copian los `ds*.csv`: la carpeta `casos_reales` privada nunca entra a la imagen.

**Límites del plan gratuito de Render.** El servicio se duerme tras unos 15 minutos sin visitas y tarda alrededor
de un minuto en despertar. Lo que se registre en la demo (confirmaciones, correcciones) se pierde cuando el servicio
se reinicia: siempre vuelve al estado inicial.

## 1. Construir la imagen (CMD, en `C:\yakutraza`)

```bash
git pull
```
```bash
docker build -f deploy/render/Dockerfile --build-context datos=C:\yakutraza\data -t ghcr.io/tirsab/yakutraza-demo:1 .
```

Para probarla antes de subirla, ejecute el contenedor y abra http://localhost:10080:

```bash
docker run --rm -p 10080:10000 ghcr.io/tirsab/yakutraza-demo:1
```

## 2. Subirla al registro privado de GitHub

1. En GitHub: **Settings → Developer settings → Personal access tokens → Tokens (classic) → Generate new token**,
   con el permiso `write:packages`. Copie el token (no lo guarde en el repositorio).
2. Inicie sesión (pega el token cuando lo pida como contraseña):

```bash
docker login ghcr.io -u tirsab
```
```bash
docker push ghcr.io/tirsab/yakutraza-demo:1
```

3. En GitHub, **Your profile → Packages → yakutraza-demo → Package settings**: confirme que la visibilidad es
   **Private** (es lo predeterminado en un paquete nuevo).

## 3. Crear el servicio en Render

1. Cree un segundo token (classic) solo con `read:packages`: es el que usará Render para descargar la imagen.
2. En Render: **New → Web Service → Existing Image**.
   - Image URL: `ghcr.io/tirsab/yakutraza-demo:1`
   - Credential: **Add credential** → registro GitHub, usuario `tirsab`, token de `read:packages`.
   - Instance type: **Free**.
   - No hace falta ninguna variable de entorno (vienen en la imagen). Render define `PORT` y el contenedor lo usa.
3. Cree el servicio. El enlace queda como `https://<nombre>.onrender.com`.

## 4. Revisar antes de compartir el enlace

- Abra el enlace: la portada carga y el selector «Ver como» muestra los roles.
- Abra `https://<nombre>.onrender.com/api/config`: debe decir `"casos_reales_privados": false` y todos los rastros
  privados en 0. Si no, no comparta el enlace.

## Actualizar la demo

Cambie el número de versión (`:2`, `:3`…), repita la construcción y el `push`, y en Render cambie la imagen en
**Settings → Image URL** (o use **Manual Deploy**).
