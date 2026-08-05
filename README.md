# Zendesk MCP Connector (local)

Conector MCP **local**: Claude Desktop o Claude Code lo levanta como subproceso solo cuando lo necesita (al abrir el chat / al llamar a una herramienta) y lo cierra después. No hay que dejar ningún servidor corriendo.

Expone cuatro herramientas:

- `get_ticket(ticket_id)` — trae un ticket de Zendesk por ID, con su hilo completo de comentarios, listo para usarse como contexto del chat.
- `search_tickets(query, max_results)` — busca tickets con la sintaxis de búsqueda de Zendesk (texto libre, `status:open`, `requester:email@...`, etc.).
- `search_help_center(query, max_results)` — busca artículos del Help Center por palabra clave.
- `get_help_center_article(article_id)` — trae un artículo del Help Center por ID, con el cuerpo completo en texto plano, listo para usarse como contexto del chat.

## Paso a paso: instalación

### 1. Instalar dependencias

```bash
cd "C:\Users\<Username>\Ruta\Al\Conector\"
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

(Si ya ves una carpeta `.venv` en esta misma carpeta, este paso ya está hecho.)

### 2. Conseguir el API token de Zendesk

En Zendesk: **Admin Center → Apps and integrations → APIs → Zendesk API → Add API token**. Copia el token en ese momento — no se vuelve a mostrar después.

Anota también:
- tu **subdominio** (si tu Zendesk es `acme.zendesk.com`, el subdominio es `acme`)
- el **email** de la cuenta de agente que vas a usar para autenticar

### 3. Registrar el conector en Claude Desktop

1. Abre `claude_desktop_config.json`. En Windows está en:
   ```
   %APPDATA%\Claude\claude_desktop_config.json
   ```
   (pégalo en la barra de direcciones del Explorador de archivos, o ábrelo con un editor de texto). Si no existe, créalo.
2. Añade (o fusiona si ya tienes otros `mcpServers`) este bloque, reemplazando los tres valores de `env` por los tuyos:

   ```json
   {
     "mcpServers": {
       "zendesk": {
         "command": "C:\\Users\\<Username>\\Ruta\\Al\connector\\.venv\\Scripts\\python.exe",
         "args": [
           "C:\\Users\\\\Users\\<Username>\\Ruta\\Al\connector\\server.py"
         ],
         "env": {
           "ZENDESK_SUBDOMAIN": "tu-subdominio",
           "ZENDESK_EMAIL": "tu-email@empresa.com",
           "ZENDESK_API_TOKEN": "tu-token"
         }
       }
     }
   }
   ```
3. Guarda el archivo y **reinicia Claude Desktop** por completo (cerrar y volver a abrir, no solo la ventana).
4. Verifica que cargó: en Claude Desktop, icono de herramientas/conectores (⚙️ o el ícono de martillo junto al chat) debería listar "zendesk" con `get_ticket` y `search_tickets`.

Claude Desktop arranca el proceso Python automáticamente al abrir una conversación y lo cierra al terminarla — no queda nada corriendo en segundo plano.

### 4. Alternativa: registrar el conector en Claude Code

Desde una terminal, en cualquier directorio:

```bash
claude mcp add zendesk \
  --env ZENDESK_SUBDOMAIN=tu-subdominio \
  --env ZENDESK_EMAIL=tu-email@empresa.com \
  --env ZENDESK_API_TOKEN=tu-token \
  -- "C:\Users\<Username>\Ruta\Al\Conector\.venv\Scripts\python.exe" "C:\Users\<Username>\Ruta\Al\Conector\server.py"
```

Esto guarda la configuración (por defecto, a nivel usuario, disponible en todos tus proyectos). Verifica con:

```bash
claude mcp list
```

o, dentro de una sesión de Claude Code, con el comando `/mcp`.

### 5. Probar

Pregúntale a Claude algo como: *"Trae el ticket 12345 de Zendesk"*, *"Busca tickets abiertos de fulano@cliente.com"* o *"Busca en el Help Center artículos sobre restablecer contraseña"*. Claude debería invocar la herramienta correspondiente automáticamente y mostrarte el resultado.

## Notas

- Las credenciales quedan solo en tu `claude_desktop_config.json` local (o en la config de Claude Code) — no se suben a ningún servidor. Trátalos como archivos sensibles.
- `.env` / `.env.example` documentan las variables necesarias por si quieres probar el servidor suelto con `python server.py` y un cliente MCP de prueba (p. ej. `mcp dev server.py`), pero no hace falta para el uso normal — las variables reales van en la config de Claude.
