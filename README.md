# Pixelia: tienda digital (web app + bot de Telegram)

Tienda de productos digitales con entrega automática.

- **Web app** moderna e interactiva: catálogo, buscador, ficha de producto y checkout. Funciona también como **Mini App de Telegram**.
- **Pagos**:
  - **PayPal**: automático.
  - **Binance Pay (USDT)**: semiautomático. Se confirma con un botón en Telegram, o solo si añades una API key de solo lectura.
  - **Telegram Stars**: dentro del bot y de la Mini App.
- **Entrega**: un enlace de descarga firmado, que caduca y tiene un límite de descargas. Se envía por **correo**, **Telegram** y/o **WhatsApp**.
- **Panel `/admin`**: ventas, pedidos, confirmar pagos Binance, reenviar entregas y subir productos con su archivo.
- **No usa dependencias externas**: solo Node.js (22.13 o superior). Usa la base de datos SQLite que trae Node, en el archivo `data/tienda.db`.

## Probarlo en tu PC

```bash
cp .env.example .env      # rellena al menos ADMIN_PASSWORD y APP_SECRET
npm run seed              # carga 6 productos de ejemplo (puedes borrarlos luego)
npm start                 # abre http://localhost:3000  y el panel en /admin
```

## Configurar cada servicio (en `.env`)

| Servicio | Qué hacer |
|---|---|
| **Telegram** | Crea el bot con @BotFather y copia el token en `TELEGRAM_BOT_TOKEN`. Pon el usuario del bot en `TELEGRAM_BOT_USERNAME`. Arranca la tienda, escríbele `/id` al bot y pon ese número en `TELEGRAM_ADMIN_CHAT_ID`. |
| **Mini App** | Necesita `https` (tu dominio). En @BotFather → *Bot Settings → Menu Button*, pon `https://tudominio.com/?tg=1`. |
| **PayPal** | En developer.paypal.com crea una app y copia el *Client ID* y el *Secret*. Prueba con `PAYPAL_MODE=sandbox` y, cuando todo funcione, cambia a `live` con las claves live. |
| **Binance** | Pon tu Pay ID en `BINANCE_PAY_ID`. Si quieres verificación automática, crea una API key de **solo lectura** (sin permisos de retiro ni de trading) y rellena `BINANCE_API_KEY` y `BINANCE_API_SECRET`. |
| **Correo** | Crea una cuenta en resend.com (gratis hasta 3.000 correos al mes), verifica tu dominio y rellena `RESEND_API_KEY` y `EMAIL_FROM`. |
| **WhatsApp** | Usa la WhatsApp Cloud API (Meta for Developers). Crea y haz aprobar una plantilla llamada `entrega_pedido` con una variable `{{1}}` para el enlace. Necesitas una cuenta de Meta Business. |

## Comandos del bot

- **Clientes**: `/start`, `/catalogo`, `/mispedidos` (enlaces de descarga nuevos), `/paysupport`, `/terminos`.
- **Admin** (solo desde tu chat): `/pendientes`, `/ventas`, `/entregar CODIGO`, `/reembolso CODIGO` (devuelve un pago en Stars).

## Reglas importantes

1. **Telegram**: si vendes productos digitales *dentro* del bot o de la Mini App, el cobro tiene que ser **solo con Stars**. Por eso:
   - el bot solo cobra en Stars;
   - la Mini App solo muestra el botón de Stars;
   - PayPal y Binance aparecen únicamente en la web normal.

   Telegram también exige `/paysupport` y una política de privacidad (`/legal`), y las dos ya están incluidas.
2. **Licencias PLR/MRR**: guarda el comprobante de cada licencia y anótalo en "Nota de licencia". Lee bien qué permite cada una. Muchas prohíben regalar el producto o venderlo por debajo de cierto precio, y algunas solo permiten venderlo con cambios. Lo ideal es cambiarles portada, título y formato para que el producto sea tuyo.
3. **`/legal` es una plantilla**: revísala y adáptala antes de vender.

## Subirlo a tu VPS

```bash
# 1. En el VPS (Ubuntu): instala Node 22
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo bash - && sudo apt install -y nodejs nginx

# 2. Clona tu repo de GitHub
git clone https://github.com/TU_USUARIO/tienda-digital.git /opt/tienda && cd /opt/tienda
cp .env.example .env && nano .env

# 3. Servicio que arranca solo y se reinicia si falla
sudo tee /etc/systemd/system/tienda.service >/dev/null <<'EOF'
[Unit]
Description=Tienda Digital
After=network.target
[Service]
WorkingDirectory=/opt/tienda
ExecStart=/usr/bin/node --no-warnings src/server.js
Restart=always
User=www-data
[Install]
WantedBy=multi-user.target
EOF
sudo chown -R www-data /opt/tienda && sudo systemctl enable --now tienda
journalctl -u tienda -f        # ver logs
```

**Cuando tengas el dominio**, configura nginx y el certificado https:

```nginx
# /etc/nginx/sites-available/tienda
server {
  server_name tudominio.com www.tudominio.com;
  client_max_body_size 100M;
  location / { proxy_pass http://127.0.0.1:3000; proxy_set_header Host $host; }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/tienda /etc/nginx/sites-enabled/ && sudo nginx -t && sudo systemctl reload nginx
sudo apt install -y certbot python3-certbot-nginx && sudo certbot --nginx -d tudominio.com -d www.tudominio.com
# Luego pon BASE_URL=https://tudominio.com en .env y reinicia: sudo systemctl restart tienda
```

**Para actualizar**: `cd /opt/tienda && git pull && sudo systemctl restart tienda`.

**Copias de seguridad**: guarda las carpetas `data/` (pedidos y productos) y `storage/products/` (archivos). No se suben a GitHub.

## Estructura

```
src/server.js            servidor web + API + descargas
src/db.js                base de datos (productos, pedidos)
src/telegram/bot.js      bot (catálogo, Stars, admin)
src/payments/            paypal.js, binance.js
src/delivery/            correo, whatsapp y enlaces firmados
public/                  web app (index, producto, pedido, legal, admin)
```

## Radar de tendencias y Meta Ads (n8n)

La carpeta `n8n/` trae los tres flujos listos para importar: el radar diario, las decisiones por Telegram y el rendimiento con Meta Ads. Los pasos de montaje y la lista de palabras clave están en **`n8n/GUIA-N8N.md`**.

En el panel `/admin`, la pestaña **📡 Radar** muestra todo lo que ha encontrado el radar, y **Productos** muestra las visitas, los intentos de compra y las ventas de los últimos 7 días.

WhatsApp queda **apagado** si dejas vacías sus variables. Las compras se hacen en la web y el producto llega por correo y por Telegram.

## Próximas fases

- **Crear anuncios de Meta automáticamente** desde n8n, con plantillas de creativos.
- **Traducción al inglés**: la interfaz ya trae ES/EN. Los productos admiten traducción en el campo `i18n`; falta añadir los textos en inglés en el panel.
- **Carrito y packs**: comprar varios productos en un solo pago.
