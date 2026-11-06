# Pixelia — notas del proyecto (léelas antes de trabajar)

## Quién y cómo
- Dueño: Diego (Venezuela, zona America/Caracas). **No es técnico**: explicar en español sencillo, **paso a paso, una cosa a la vez**.
- Comandos para el servidor siempre así (su terminal mete basura al pegar): `echo inicio; cd /opt/pixelia && …; echo fin`
- Actualizar el servidor: `bash update.sh` (git pull + reinicia `pixelia` y `pixelia-estudio`).
- **Nunca pedir claves/tokens por el chat.** Que las copie en sus notas; los scripts (`configurar.sh`) las leen ocultas.
- Cuidar créditos (ElevenLabs, API de Anthropic) y el límite del plan Pro: conversaciones cortas, reutilizar lo hecho.

## No tocar
- Su **n8n** (contenedor y su WEBHOOK_URL con túnel trycloudflare): tiene otro trabajo ahí. Los botones del radar los atiende la tienda (long polling en `src/telegram/radar.js`).
- Otros contenedores del VPS: lector, gotenberg, caddy del sitio sslip.io, mi-tunel. Proyectos de Google "Mi Radar de Nichos Virales" y "Default Gemini Project".
- Binance API: solo lectura, IP 162.33.179.6, sin trading ni retiros.

## Infraestructura
- VPS 162.33.179.6 (EE. UU., 1 GB RAM). Código en `/opt/pixelia`. Caddy en `/root/lector/Caddyfile`.
- Dominio **pixeliadigital.app** (Cloudflare, DNS sin proxy). Panel: `/admin`.
- Repo: `diegsalazar1000-del/pixelia-tienda` (rama main). Commits con las líneas de atribución.
- Instagram: @pixelia.digitalstore. Bots: tienda (Telegram, Stars) y **@PixeliaRadarBot** (radar + estudio).

## Qué hay construido
- **Tienda** Node 22 sin dependencias (`src/`), SQLite. Pagos: PayPal live (incluye tarjeta Visa/Mastercard), Binance semi-automático (la API da "restricted location" desde EE. UU.; él confirma con botón), Telegram Stars. Entrega por correo (Resend, `hola@mail.pixeliadigital.app`), Telegram y enlace firmado. Meta Pixel + Conversions API.
- **Packs**: producto con `bundle_ids` (ej. 3 × $4.99 → pack $9.99). Caja "Llévate los 3" en cada producto y oferta "Completa tu pack" tras comprar (precio = pack − lo pagado). Un pack no se publica si a un producto le falta archivo.
- **Cupón 15%** a cambio del correo (tabla `subscribers`), un uso, no aplica a packs. Lista descargable en /admin.
- **Radar** (n8n): YouTube API + explorador web con Claude (Apify agotado), evaluación con IA, aviso con botones Comprar/Recrear/Descartar. `/fusionar` en el bot: la IA combina productos del radar en uno mejor o en un pack y crea borradores + plan.
- **Estudio de anuncios** (contenedor `pixelia-estudio`, Python, `estudio/`): por cada reel la IA elige el **formato** que más pega con el público (Clásico, 💬 Chat de WhatsApp, 🎬 Video real de Pexels, 📱 Pantalla de móvil, ✍️ Cómo se usa, 🔀 Antes/después, 🏆 Top 3) y escribe el **guion** (4-6 escenas de 16 tipos, ver `brief.ESCENAS` y `formatos.py`), estilo (Color/Neón/Minimal/TikTok), música y voz, con subtítulos TikTok. La voz se genera ANTES del video y cada escena dura lo que su frase (no se corta). Por defecto todo lo elige la IA ("ia"); el usuario puede fijar voz/música. Botones: 🎲 Otra variante (siguiente formato del ranking), 🧪 4 variantes (4 formatos distintos), reel nuevo con lo marcado, solo voz/música. Videos reales necesitan `bash configurar.sh pexels` (clave gratis); sin clave, fondo animado.
- El usuario NO quiere que se cambie el estilo base sin pedírselo: un chat aparte añadió un estilo "Impacto 3D" que no le gustó y se deshizo (commit 5ef9f5e). Imágenes 1:1, 4:5, 9:16. Franja "Paga con PayPal · Visa · Mastercard · Binance" (texto, sin logos de marcas). Menú en Telegram: reel nuevo / solo cambiar voz-música / 4 variantes (V1-V4) para A/B en Meta. Nombres en Meta: `[slug] A/B/C/reel/V1…`.
- **Voz y música**: ElevenLabs plan Starter (voz natural + Eleven Music, licencia comercial). Máx. 3 canciones por género y luego se reutilizan; caché de voces en `storage/voz-cache`. Respaldo gratis: Piper + música sintetizada. Versión "sin música" para la biblioteca de Meta. Gemini no se puede usar (Google no acepta Venezuela).
- Producto publicado: **Mi Año en Mini · Planner Digital 2027** a $4.99 (antes $9.99).

## Decisiones de negocio
- Precios $3-10 (principal $4.99), packs de 3 a $9.99, presupuesto de anuncios ~$10/día, validar 1-2 semanas con poco presupuesto antes de escalar.
- Productos recreados: idea sí, copiar diseño/textos no (salvo licencia PLR/MRR). Nada de reseñas inventadas ni urgencia falsa en anuncios.
- Siguiente producto: 2 más del mismo público (organización: finanzas/ahorro, hábitos) para armar el pack.

## Pendiente (en orden aproximado)
1. Que Diego pruebe el reel con guion nuevo y ajustar.
2. Identidad de Instagram (logo, bio, primeras publicaciones, video de presentación) y página de Facebook.
3. Meta: Business Manager, cuenta publicitaria (riesgo de tarjeta venezolana), píxel+CAPI con `bash configurar.sh meta`, luego botón "📤 Subir a Meta" (campaña PAUSADA) y optimización semanal con datos del píxel.
4. 4-5 productos gratis para captar seguidores/correos; botón "⭐ Guardar este guion" (opcional).
5. Copias de seguridad, quizá VPS de 2 GB, Binance automático vía proxy, traducción al inglés, WhatsApp al final.
