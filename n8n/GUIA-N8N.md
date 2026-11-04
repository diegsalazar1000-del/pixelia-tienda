# Radar de productos digitales en n8n

Tres flujos que trabajan con tu tienda:

| Flujo | Cuándo | Qué hace |
|---|---|---|
| **1 · Radar diario** | 8:00 | Busca en Etsy, TikTok, Instagram y Hotmart productos digitales **recientes y en tendencia**. La IA los puntúa y te manda a Telegram los mejores, con botones. |
| **2 · Decisiones** | Al pulsar un botón | 🛒 **Comprar y revender**: crea el borrador en la tienda y te dice qué revisar antes de pagar. 🛠️ **Recrear**: te manda un plan completo para hacer tu versión propia y crea el borrador. ❌ **Descartar**: lo quita. |
| **3 · Rendimiento** | 21:00 | Cruza las ventas de la tienda con Meta Ads, pausa los anuncios que pierden, retira los productos que no venden y te propone reemplazos del radar. |

Los botones de los reemplazos funcionan igual que los del radar, así que el ciclo se repite solo: encontrar, decidir, publicar, anunciar, medir y reemplazar.

---

## 1. Qué cuentas necesitas (y cuánto cuestan)

| Servicio | Para qué | Coste aproximado |
|---|---|---|
| **n8n** en tu VPS | Ejecutar los flujos | Gratis (versión Community autoalojada) |
| **Etsy Developers** | Buscar listados de Etsy | Gratis. Etsy tiene que aprobar tu app, lo que puede tardar unos días |
| **Apify** | Leer TikTok, Instagram y Hotmart | El plan gratis trae 5 $/mes de crédito. Con la configuración incluida, calcula unos 10–20 $/mes |
| **Anthropic (API de Claude)** | Puntuar productos y escribir planes y anuncios | Unos 3–8 $/mes. Se paga aparte de Claude Pro |
| **Bot de Telegram del radar** | Avisos y botones | Gratis |
| **Meta Business + píxel** | Medir y gestionar los anuncios | Gratis (los anuncios se pagan aparte) |

Si quieres empezar sin gastar, pon solo la clave de Etsy y la de Anthropic. Las fuentes que no tengan clave se saltan solas.

## 2. Instalar n8n en tu VPS

Telegram necesita que n8n tenga **https**, así que usa un subdominio, por ejemplo `n8n.tudominio.com`.

```bash
sudo apt install -y docker.io
sudo docker volume create n8n_data
sudo docker run -d --name n8n --restart always -p 127.0.0.1:5678:5678 \
  -e GENERIC_TIMEZONE=America/Caracas -e TZ=America/Caracas \
  -e N8N_HOST=n8n.tudominio.com -e N8N_PROTOCOL=https -e WEBHOOK_URL=https://n8n.tudominio.com/ \
  -v n8n_data:/home/node/.n8n docker.n8n.io/n8nio/n8n
```

Configura nginx para `n8n.tudominio.com` igual que hiciste con la tienda, con `proxy_pass http://127.0.0.1:5678;`. Añade también estas líneas, que hacen falta para que el editor funcione:

```
proxy_http_version 1.1;
proxy_set_header Upgrade $http_upgrade;
proxy_set_header Connection "upgrade";
```

Después ejecuta `certbot --nginx -d n8n.tudominio.com`.

## 3. Conectar la tienda

1. En el `.env` de la tienda, pon `N8N_API_KEY=` con un texto largo y aleatorio.
2. Pon también `META_PIXEL_ID` y `META_CAPI_TOKEN`.
3. Reinicia la tienda.

## 4. Importar los flujos

1. En n8n, ve a **Workflows → Import from file** e importa los tres `.json`.
2. En cada flujo, abre el nodo **Config** y rellena tus claves. Los tres llevan el mismo Config.
3. En el flujo 2, abre **Telegram Trigger** y crea la credencial con el token del **bot del radar**. Tiene que ser un bot **distinto** al de la tienda: el de la tienda ya está escuchando sus mensajes y se pisarían.
4. Escríbele cualquier cosa al bot del radar para que pueda enviarte mensajes.
5. Prueba el flujo 1 con **Test workflow**. Cuando funcione, **activa** los tres.

## 5. Cómo enlazar Meta Ads con la tienda (importante)

- Cada anuncio debe tener un **nombre que empiece con el slug del producto entre corchetes**, por ejemplo `[planner-de-boda-digital-2027] v1`. Cuando apruebas un producto, el bot te dice el nombre exacto.
- Haz que el anuncio lleve a `https://tudominio.com/p/el-slug`.
- Usa un objetivo de **Ventas** con el evento **Purchase** del píxel. La tienda ya envía los eventos `ViewContent`, `InitiateCheckout` y `Purchase` desde la página, y también por servidor (API de Conversiones).
- **Las reglas** se ajustan en Config:
  - `DIAS_PRUEBA`: días de prueba antes de juzgar un producto (5).
  - `GASTO_MAX_SIN_VENTA`: si un producto gasta 15 $ sin vender, se pausa y se retira.
  - `ROAS_MINIMO`: por debajo de 1,3 te avisa para ajustar.
  - `ROAS_ESCALAR`: por encima de 2,5 te sugiere subir presupuesto.
- **Protecciones**: retira como máximo 2 productos al día y nunca deja la tienda con menos de 6.
- **Crear los anuncios es manual, por ahora.** El bot te da el gancho, el texto y el titular, y tú creas el anuncio en Meta en 2 minutos. Así controlas lo que se publica con tu dinero, y Meta revisa cada anuncio de todas formas.
- **Token de Meta**: en Business Settings → Usuarios del sistema, crea un usuario, dale acceso a tu cuenta publicitaria y genera un token con el permiso `ads_management`.

## 6. Qué busca el radar (palabras clave)

Ya vienen puestas en Config, en español y en inglés. Cada día usa una parte distinta para no gastar de más.

**TikTok (búsquedas):**
- **Español**: producto digital · plantilla canva · planner digital · plantilla notion · ebook que vendo · plantilla excel · prompts chatgpt · presets lightroom · imprimibles para vender · cuaderno digital goodnotes · derechos de reventa
- **Inglés**: digital products to sell · canva template · notion template · digital planner · goodnotes planner · printable · etsy digital download · ai prompts pack · spreadsheet template · faceless digital products · plr ebook

**TikTok (hashtags):** #productosdigitales #plantillascanva #plantillasdigitales #digitalproducts #digitaldownload #canvatemplate #notiontemplate #digitalplanner #goodnotesplanner #printables #etsydigitalproducts #plrproducts #resellrights

**Instagram (hashtags):** #productosdigitales #plantillascanva #plantillasdigitales #digitalproducts #canvatemplates #notiontemplates #digitalplanner #plannerdigital #emprendedoradigital #ebookdigital

**Etsy:** digital planner 2027 · canva template · notion template · printable planner · spreadsheet template · budget template · instagram templates · ebook template · wedding planner printable · kids printable activities · resume template · lightroom presets · ai prompts · goodnotes stickers · small business template · meal planner printable

**Hotmart:** plantillas · canva · notion · ebook · excel · inteligencia artificial · productividad · finanzas personales · recetas · manualidades · idiomas · emprendimiento

**Cómo decide qué es "nuevo y en tendencia":**
- **TikTok e Instagram**: publicaciones de las últimas **3 semanas**, con al menos 20.000 vistas en TikTok. Se ordenan por **velocidad**: vistas, compartidos y guardados por día.
- **Etsy**: productos digitales publicados hace **menos de 4 meses** con al menos 15 favoritos. Se ordenan por favoritos por día.
- **Hotmart**: no muestra la fecha de publicación. El radar prioriza los productos con mucha "temperatura" y pocas reseñas, que suelen ser productos nuevos que están despegando.
- **La IA** descarta lo que no es un producto digital, lo que usa marcas o personajes con copyright, lo que promete dinero fácil o resultados de salud (Meta lo rechaza) y los "cursos MRR de marketing" tipo esquema.

**Consejo:** a las 2–3 semanas, mira en el panel (`/admin` → 📡 Radar) qué palabras te traen mejores hallazgos. Quita las que no aportan y añade nichos nuevos.

## 7. Reglas que conviene respetar

- **Recrear** es hacer **tu propia versión**: otro contenido, otro diseño, otro nombre. El plan de la IA te guía para eso. No copies textos, imágenes ni archivos del original.
- **Revender** solo si la licencia lo dice claramente (PLR, MRR o Resell Rights). Guarda el comprobante. Muchas licencias fijan un precio mínimo o prohíben regalar el producto.
- **Etsy**: su API es para crear herramientas. Úsala para investigar tendencias, no para copiar listados.
- **Apify** lee datos públicos de TikTok, Instagram y Hotmart. Si una de esas páginas cambia, su lector puede fallar unos días. El radar sigue funcionando con el resto de las fuentes y te lo indica en el resumen diario.

## 8. Tu rutina diaria (unos 15 minutos)

1. **Mañana**: llega el radar. Pulsa 🛒, 🛠️ o ❌ en cada propuesta.
2. **Cuando tengas el archivo** (comprado o recreado): ve a `/admin` → Productos → Editar el borrador → sube el archivo → Guardar. Con eso se publica.
3. **Crea el anuncio** en Meta con el nombre `[slug] v1` y el texto que te dio el bot.
4. **Noche**: llega el informe. Lo que pierde se pausa solo, y eliges reemplazos con los botones.
