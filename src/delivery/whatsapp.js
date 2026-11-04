// Envío por WhatsApp Cloud API (Meta). Para escribir primero a un cliente, Meta exige
// una plantilla aprobada. La plantilla debe tener 1 variable en el cuerpo: {{1}} = enlace.
import { config } from '../config.js';

export async function sendWhatsApp(phone, link) {
  const { token, phoneId, template, templateLang } = config.whatsapp;
  if (!token || !phoneId) throw new Error('WhatsApp no configurado');
  const to = String(phone).replace(/[^\d]/g, '');
  const res = await fetch(`https://graph.facebook.com/v21.0/${phoneId}/messages`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}`, 'content-type': 'application/json' },
    body: JSON.stringify({
      messaging_product: 'whatsapp', to, type: 'template',
      template: { name: template, language: { code: templateLang },
        components: [{ type: 'body', parameters: [{ type: 'text', text: link }] }] },
    }),
  });
  if (!res.ok) throw new Error(`WhatsApp ${res.status}: ${await res.text()}`);
  return res.json();
}

export const whatsappEnabled = () => !!(config.whatsapp.token && config.whatsapp.phoneId);
