// Envío de correo con Resend (API HTTP). Gratis hasta 3.000 correos/mes.
import { config } from '../config.js';

export async function sendEmail(to, subject, text, html) {
  if (!config.email.resendKey || !config.email.from) throw new Error('Correo no configurado (RESEND_API_KEY / EMAIL_FROM)');
  const res = await fetch('https://api.resend.com/emails', {
    method: 'POST',
    headers: { Authorization: `Bearer ${config.email.resendKey}`, 'content-type': 'application/json' },
    body: JSON.stringify({ from: config.email.from, to: [to], subject, text, html }),
  });
  if (!res.ok) throw new Error(`Resend ${res.status}: ${await res.text()}`);
  return res.json();
}
