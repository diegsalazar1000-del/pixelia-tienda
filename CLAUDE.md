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
- **Explorador 2.0** (en la tienda, `src/telegram/explorador.js`, no toca n8n): Claude con búsqueda web encuentra productos digitales vendiéndose en los últimos 3 meses (Etsy, TikTok Shop, Instagram, Hotmart, Gumroad, Pinterest, Google) rotando 16 categorías (planners y finanzas incluidos, más cursos, ebooks, presets, prompts, imprimibles, audios, kits de negocio, manualidades, recursos para creadores…), le pasa a la IA lo ya visto/vendido para no repetir, exige variedad de categoría y formato, y propone IDEAS NUEVAS derivadas. Corre solo a las 10:00 (Caracas) y con `/explorar [tema]`. Usa los mismos botones Comprar/Recrear/Descartar.
- Segundo producto fabricado: **Panel Financiero Mensual** (Excel/Google Sheets, `/home/claude/finanzas/build.py` en la sesión original; ZIP con archivo en blanco, ejemplo, guía PDF y vista previa) a $4.99.
- Tercer producto fabricado: **Lotería Baby Shower** (sesión original: `/home/claude/loteria/build.py`): 54 cartas ilustradas con Noto Color Emoji (licencia OFL), 60 tablas únicas tamaño Carta con campo rellenable del nombre del bebé, instrucciones + 54 versos, cartel ¡LOTERÍA! y fichas; $4.99. Pendiente: su video tutorial con identidad propia (pastel, música alegre, cartas animadas).
- **Radar** (n8n): YouTube API + explorador web con Claude (Apify agotado), evaluación con IA, aviso con botones Comprar/Recrear/Descartar. `/fusionar` en el bot: la IA combina productos del radar en uno mejor o en un pack y crea borradores + plan.
- **Estudio de anuncios** (contenedor `pixelia-estudio`, Python, `estudio/`): por cada reel la IA elige el **formato** que más pega con el público (Clásico, 💬 Chat de WhatsApp, 🎬 Video real de Pexels, 📱 Pantalla de móvil, ✍️ Cómo se usa, 🔀 Antes/después, 🏆 Top 3) y escribe el **guion** (4-6 escenas de 16 tipos, ver `brief.ESCENAS` y `formatos.py`), estilo (Color/Neón/Minimal/TikTok), música y voz, con subtítulos TikTok. La voz se genera ANTES del video y cada escena dura lo que su frase (no se corta). Por defecto todo lo elige la IA ("ia"); el usuario puede fijar voz/música. Botones: 🎓 Video tutorial (cómo se usa paso a paso con ejemplo, escena "pasos"), 🎲 Otra variante (siguiente formato del ranking), 🧪 4 variantes (4 formatos distintos), reel nuevo con lo marcado, solo voz/música. Pixabay (`bash configurar.sh pixabay`, gratis) SOLO cuando el usuario toca "📸 Crear con fotos y videos de Pixabay": MONTAJE rápido de 10-18 fotos reales, cada una ilustra la frase que se dice (puede ser graciosa pero relacionada), con texto por plano, cortes con golpe de zoom/destello y sonido, planos de producto intercalados; imagen A con foto real. NO un video pegado de fondo (no vende); por defecto todo queda como antes. No agregar botones ni cambiar el comportamiento por defecto sin que lo pida; sin clave, fondo animado.
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
4. Productos con /fusionar (meta: ~10 productos en una semana, empezando por 3 del mismo público que el planner para el pack). Diego manda los planes y Claude fabrica los archivos.
5. Página `/regalo` (enlace en la bio de Instagram): producto gratis a cambio del correo con casilla de consentimiento ("Acepto recibir novedades"), evento Lead del píxel para públicos similares, lista para email marketing y público personalizado en Meta. El regalo debe ser del mismo público que lo que se vende.
6. Botón "⭐ Guardar este guion" (opcional). Comandos del bot para cuidar créditos: /creditos (gasto de ElevenLabs; la clave necesita permiso User→Read), /ahorro on|off (no gastar: reutiliza voces y música guardadas), /cancelar (quita anuncios de la fila). Al probar anuncios: primero sin voz y luego "Solo voz/música" para ahorrar créditos de ElevenLabs.
7. IDEAS DE DIEGO (anotadas 6-nov): (a) anuncios inspirados en videos virales de comedia/humor: tomar el FORMATO o la idea del chiste (POV, sketch, meme) y recrearlo con nuestro producto, sin copiar clips ni audios con derechos; (b) que el explorador revise cada día las tendencias MUNDIALES (noticias, temas virales, fechas) y proponga productos que cubran una necesidad nueva que surja de ellas.
8. Copias de seguridad, quizá VPS de 2 GB, Binance automático vía proxy, traducción al inglés, WhatsApp al final.

## 2026-11-06
- Formato "comedia" (botón 😂 Anuncio de comedia, f=comedia): escena "meme" (plantillas nadie_yo / texto_arriba / expectativa / antes), foto de reacción de Pixabay o el producto, sonidos boing + ba-dum-tss. Los memes SOLO salen en formato comedia. No copiar clips/audios virales: solo la estructura del chiste.
- Explorador: sección "mundo" (noticias de la semana, virales, fechas próximas → necesidad → producto). Llegan como 🌍 TENDENCIA MUNDIAL (source idea-mundo, solo recrear). /explorar mundo = solo eso. Búsquedas por defecto: 10.
- Portadas en public/img: portada-panel-financiero.jpg y portada-loteria-baby-shower.jpg (https://pixeliadigital.app/img/...).
- Anuncios PRO (botón 🧠, opción q=1; lo normal sigue igual, 1 guion sin revisión) (estudio/director.py): investigación real con web_search 1 vez por producto (B["investigacion"], con fuentes, "no inventes"); 3 guiones en paralelo (formatos distintos, sin repetir los últimos 3) + director que califica (gancho, claridad, coherencia voz/texto/imagen, público, originalidad) y pule el ganador; revisión final con fotogramas (visión) que corrige 1 vez. Español neutro obligatorio. Apagar con AD_RESEARCH=0 / AD_DIRECTOR=0 / AD_REVIEW=0 en .env. Variantes x4 usan 1 guion por variante (single=True).
- Ideas pendientes aprobadas: aprender de resultados de Meta (cuando se conecte).
- 📹 Anuncio con video propio (ej. Gemini, gratis desde su app): Diego manda el video al bot (pie opcional con el producto) → elige producto y voz/música → opción c=<id>, archivo en storage/clips/<id>.mp4. Escena "clip" (sonido original, gancho encima en el momento que decide la IA vía describir_clip con visión), luego 2-3 escenas de producto + precio. Las imágenes estáticas usan un fotograma del clip.
- 🎬 Prompts para Gemini: botón en el selector y en "Publicaste", y /gemini. Claude escribe 2 prompts de Veo (inglés, diálogo en español neutro, mismo estilo que los 2 ejemplos que funcionaron) sin repetir ideas (storage/anuncios/<slug>/gemini-prompts.json). Ciclo: prompt → Gemini (gratis en la app) → video al bot → anuncio.
- 📤 Redes (src/telegram/redes.js): /publicar sube el kit de 9 posts (src/telegram/kit-instagram.json, imágenes en public/img/ig/) a Instagram + página de Facebook vía Graph API v23 con token de página (no vence). `bash configurar.sh redes` pide App ID, App Secret y token del Explorador, lo cambia por token de página largo y guarda META_PAGE_ID/META_PAGE_TOKEN/META_IG_ID. Siguiente: botón para publicar productos y reels.
