# Censura Audio — prototipo local

Aplicación local para transcribir audio en español y marcar palabras o expresiones configurables con marcas de tiempo.

## Requisitos
- Python 3.10–3.12 recomendado.
- Conexión a internet la primera vez para descargar el modelo Whisper seleccionado.
- Espacio libre para el modelo. `small` es el punto de partida recomendado.
- En Windows, si FFmpeg da problemas, instala FFmpeg y añádelo al PATH. `faster-whisper` incluye normalmente las bibliotecas necesarias para decodificar audio mediante PyAV.

## Instalación

Abre una terminal en esta carpeta y ejecuta:

```bash
python -m venv .venv
```

Windows:
```powershell
.venv\Scripts\Activate.ps1
```

macOS/Linux:
```bash
source .venv/bin/activate
```

Después:
```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
streamlit run app.py
```

Se abrirá la aplicación en el navegador, normalmente en `http://localhost:8501`. La interfaz y el procesamiento se ejecutan en tu ordenador.

## Uso
1. Carga MP3, WAV, M4A, AAC, FLAC u OGG.
2. Edita la lista de palabras a buscar.
3. Pulsa “Transcribir y detectar palabras”.
4. Revisa los tiempos y descarga CSV/TXT.

## Privacidad y límites
El audio no se envía a una API de transcripción. La primera vez, el modelo elegido se descarga desde internet y queda guardado en la caché local. La transcripción puede equivocarse, especialmente con voces superpuestas, música, mala calidad o insultos pronunciados rápidamente. Las marcas de tiempo de palabra son aproximadas: escucha el fragmento antes de censurar.

## Próximas mejoras
- Botón para reproducir cada coincidencia con unos segundos de margen.
- Normalización para detectar variantes con/sin tildes y algunas formas conjugadas.
- Lista de reglas guardable por programa.
- Exportación EDL/XML o marcadores para Final Cut Pro.
