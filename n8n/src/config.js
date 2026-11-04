// ⚙️ CONFIGURACIÓN — rellena esto una vez (es igual en los 3 flujos).
return [{ json: {
  // Tu tienda
  TIENDA_URL: 'https://tudominio.com',          // sin barra al final
  TIENDA_API_KEY: 'pon-aqui-N8N_API_KEY',        // el mismo valor que N8N_API_KEY en el .env de la tienda

  // Bot del RADAR (un bot distinto al de la tienda; créalo con @BotFather)
  TELEGRAM_RADAR_TOKEN: '123456:ABC...',
  TELEGRAM_CHAT_ID: '123456789',                 // tu chat id (el mismo que TELEGRAM_ADMIN_CHAT_ID)

  // IA (console.anthropic.com → API Keys)
  ANTHROPIC_API_KEY: 'sk-ant-...',
  MODELO_RAPIDO: 'claude-haiku-5-5',             // para puntuar muchos productos (barato)
  MODELO_POTENTE: 'claude-sonnet-5-5',           // para guías de recreación y anuncios

  // Fuentes de datos
  APIFY_TOKEN: 'apify_api_...',                  // apify.com → Settings → API & Integrations
  ETSY_API_KEY: 'keystring:shared_secret',       // etsy.com/developers → Your Apps (se pega tal cual, con los dos puntos)
  YOUTUBE_API_KEY: 'AIza...',                    // gratis: console.cloud.google.com → YouTube Data API v3 → Credenciales
  EXPLORADOR_WEB: true,                          // Claude busca tendencias en internet (usa tu saldo de la API de Claude)
  MODELO_EXPLORADOR: 'claude-haiku-5-5',
  BUSQUEDAS_WEB_MAX: 6,                          // búsquedas por día (0,01 $ cada una)

  // Meta Ads (para el flujo de rendimiento)
  META_TOKEN: 'EAAG...',                         // token de usuario del sistema con permiso ads_management
  META_AD_ACCOUNT: 'act_1234567890',

  // ===== Qué buscar =====
  // Cada día se usa una parte de cada lista (rotando) para controlar el gasto.
  TIKTOK_BUSQUEDAS: [
    'producto digital', 'plantilla canva', 'planner digital', 'plantilla notion', 'ebook que vendo', 'plantilla excel',
    'prompts chatgpt', 'presets lightroom', 'imprimibles para vender', 'cuaderno digital goodnotes', 'derechos de reventa',
    'digital products to sell', 'canva template', 'notion template', 'digital planner', 'goodnotes planner', 'printable',
    'etsy digital download', 'ai prompts pack', 'spreadsheet template', 'faceless digital products', 'plr ebook',
  ],
  TIKTOK_HASHTAGS: [
    'productosdigitales', 'plantillascanva', 'plantillasdigitales', 'digitalproducts', 'digitaldownload', 'canvatemplate',
    'notiontemplate', 'digitalplanner', 'goodnotesplanner', 'printables', 'etsydigitalproducts', 'plrproducts', 'resellrights',
  ],
  INSTAGRAM_HASHTAGS: [
    'productosdigitales', 'plantillascanva', 'plantillasdigitales', 'digitalproducts', 'canvatemplates', 'notiontemplates',
    'digitalplanner', 'plannerdigital', 'emprendedoradigital', 'ebookdigital',
  ],
  YOUTUBE_BUSQUEDAS: [
    'productos digitales para vender', 'plantillas canva para vender', 'planner digital', 'plantilla notion', 'ebook para vender',
    'digital products to sell', 'digital products that sell', 'etsy digital products', 'canva templates to sell', 'notion templates',
    'faceless digital products', 'what digital products are trending', 'goodnotes digital planner', 'printables to sell',
  ],
  ETSY_BUSQUEDAS: [
    'digital planner 2027', 'canva template', 'notion template', 'printable planner', 'spreadsheet template', 'budget template',
    'instagram templates', 'ebook template', 'wedding planner printable', 'kids printable activities', 'resume template',
    'lightroom presets', 'ai prompts', 'goodnotes stickers', 'small business template', 'meal planner printable',
  ],
  HOTMART_BUSQUEDAS: [
    'plantillas', 'canva', 'notion', 'ebook', 'excel', 'inteligencia artificial', 'productividad', 'finanzas personales',
    'recetas', 'manualidades', 'idiomas', 'emprendimiento',
  ],

  // Cuántas palabras de cada lista usar por día y cuántos resultados por palabra
  POR_DIA: { youtube: 8, tiktok: 6, tiktok_hashtags: 3, instagram: 4, etsy: 6, hotmart: 4 },
  RESULTADOS_POR_BUSQUEDA: 20,

  // Filtros de "nuevo y en tendencia"
  MAX_DIAS_POST: 21,          // TikTok / Instagram: publicaciones de las últimas 3 semanas
  MAX_DIAS_ETSY: 120,         // Etsy: productos publicados hace menos de 4 meses
  MIN_VISTAS_TIKTOK: 20000,   // descarta vídeos con poco alcance
  MIN_FAVORITOS_ETSY: 15,
  MIN_VISTAS_YOUTUBE: 10000,
  TOP_POR_FUENTE: { youtube: 10, web: 15, tiktok: 12, instagram: 8, etsy: 15, hotmart: 8 },   // los mejores de cada fuente pasan a la IA
  NOTA_MINIMA_AVISO: 7,       // solo te avisa por Telegram si la IA le pone 7/10 o más

  // Reglas del flujo de rendimiento (Meta Ads)
  DIAS_PRUEBA: 5,             // días que un producto tiene para demostrar que vende
  GASTO_MAX_SIN_VENTA: 15,    // USD gastados en anuncios sin ninguna venta → se pausa y se retira
  ROAS_MINIMO: 1.3,           // ingresos / gasto por debajo de esto → aviso para ajustar
  ROAS_ESCALAR: 2.5,          // por encima → sugerencia de subir presupuesto
  AUTO_PAUSAR_ANUNCIOS: true, // pausa sola los anuncios perdedores
  AUTO_RETIRAR_PRODUCTOS: true,
  MAX_RETIROS_POR_DIA: 2,     // como mucho retira 2 productos al día
  MIN_PRODUCTOS_ACTIVOS: 6,   // nunca deja la tienda con menos de 6 productos
} }];
