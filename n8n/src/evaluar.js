// 🤖 EVALUAR CON IA — Claude analiza cada hallazgo nuevo y decide si vale la pena.
const C = $('Config').first().json;
const { fresh = [], log = [], found = 0 } = $input.first().json;

const SYSTEM = `Eres analista de productos digitales para una tienda online en español (Latinoamérica y España) que vende con anuncios de Meta.
Recibes un hallazgo (un listado de Etsy/Hotmart o una publicación de TikTok/Instagram) y devuelves SOLO un JSON válido, sin texto extra:
{
 "es_producto_digital": true|false,
 "producto": "qué se vende exactamente, en una frase",
 "titulo": "título atractivo en español para nuestra tienda (máx. 70 caracteres)",
 "frase_corta": "beneficio principal en una frase (máx. 110 caracteres)",
 "descripcion": "descripción de venta en español, 90-160 palabras: para quién es, qué incluye, formato, cómo se usa",
 "categoria": "Plantillas|Productividad|Ebooks|IA|Fotografía|Educación|Finanzas|Negocios|Hogar|Infantil|Otros",
 "emoji": "un emoji",
 "precio_sugerido": número en USD entre 3 y 29,
 "decision": "comprar_reventa" | "recrear" | "descartar",
 "derechos": "si el original menciona PLR/MRR/derechos de reventa, dilo; si no, 'sin derechos de reventa: recrear con contenido propio'",
 "por_que": "por qué está en tendencia ahora (máx. 160 caracteres)",
 "como_recrear": ["3 a 5 ideas concretas para hacer una versión propia MEJOR y distinta"],
 "riesgos": "marcas registradas, copyright, promesas de dinero/salud que Meta rechaza, o 'ninguno'",
 "anuncio": {"gancho": "primera frase de un vídeo/reel", "texto": "texto principal del anuncio (máx. 300 caracteres)", "titular": "máx. 40 caracteres"},
 "nota": número 1-10
}
Criterios de la nota: demanda real y reciente (no productos de hace años), que se pueda vender a hispanohablantes, que se pueda recrear o revender legalmente,
margen con precio bajo (impulso), facilidad para anunciar en Meta. Pon nota ≤4 y decision "descartar" si: no es un producto digital, usa marcas/personajes
con copyright, promete dinero fácil o resultados de salud, es un "curso MRR de marketing digital" tipo esquema, o es contenido personal sin producto.
Solo pon "comprar_reventa" si hay señales claras de licencia PLR/MRR/reventa.
Si el hallazgo es un VÍDEO o PUBLICACIÓN (YouTube, TikTok, Instagram) que habla de vender productos digitales, NO lo descartes por ser un vídeo:
extrae el producto concreto que muestra o recomienda (ej. "plantillas Canva para bodas", "planner de lectura") y evalúa ESE producto.
Solo descarta si el vídeo no menciona ningún producto concreto. Sé conciso: la descripcion máximo 120 palabras. Responde únicamente con el JSON.`;

// Saca el JSON de la respuesta aunque venga con ```json o texto alrededor
const parseJson = (text) => {
  const t = String(text || '').replace(/```json|```/g, '');
  const a = t.indexOf('{'), b = t.lastIndexOf('}');
  if (a < 0 || b <= a) throw new Error('la IA no devolvió JSON: ' + t.slice(0, 80));
  return JSON.parse(t.slice(a, b + 1));
};

const out = [];
for (const c of fresh.slice(0, 45)) {
  try {
    const r = await this.helpers.httpRequest({
      method: 'POST', url: 'https://api.anthropic.com/v1/messages', json: true, timeout: 120000,
      headers: { 'x-api-key': C.ANTHROPIC_API_KEY, 'anthropic-version': '2023-06-01' },
      body: {
        model: C.MODELO_RAPIDO, max_tokens: 3000, system: SYSTEM,
        messages: [{ role: 'user', content: JSON.stringify({ fuente: c.source, palabra_clave: c.keyword, titulo: c.title, texto: c.snippet,
          precio: c.price, moneda: c.currency, publicado: c.published_at, metricas: c.metrics, url: c.url }) }],
      },
    });
    const text = (r.content || []).map((b) => b.text || '').join('');
    if (r.stop_reason === 'max_tokens') throw new Error('respuesta cortada (max_tokens)');
    const ai = parseJson(text);
    const nota = Number(ai.nota) || 0;
    await this.helpers.httpRequest({
      method: 'POST', url: `${C.TIENDA_URL}/api/n8n/candidates/${c.id}`, headers: { 'x-api-key': C.TIENDA_API_KEY }, json: true,
      body: { ai_score: nota, ai, status: ai.decision === 'descartar' || !ai.es_producto_digital ? 'discarded' : 'new' },
    });
    out.push({ ...c, ai, ai_score: nota });
  } catch (e) { log.push(`IA #${c.id}: error ${e.message}`); }
}
log.push(`Evaluados por la IA: ${out.length}`);
return [{ json: { evaluated: out, log, found } }];
