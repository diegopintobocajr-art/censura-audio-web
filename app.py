import re
import io
import os
import csv
import tempfile
from pathlib import Path

import streamlit as st
from faster_whisper import WhisperModel

st.set_page_config(page_title="Censura Audio", page_icon="🎧", layout="wide")

DEFAULT_WORDS = """mierda
puta
puto
joder
coño
carajo
verga
marico
marica
pendejo
pendeja
idiota
imbécil
estúpido
estúpida
maldito
maldita
mamaguevo
hijueputa
gonorrea
culero
cabrón
cabrona"""

@st.cache_resource
def load_model(model_size: str, device: str, compute_type: str):
    return WhisperModel(model_size, device=device, compute_type=compute_type)

def parse_terms(text: str):
    return list(dict.fromkeys(
        term.strip().lower() for term in re.split(r"[\n,;]+", text)
        if term.strip()
    ))

def matches_term(word: str, terms):
    normalized = re.sub(r"^[^\wáéíóúüñ]+|[^\wáéíóúüñ]+$", "", word.lower(), flags=re.UNICODE)
    found = []
    for term in terms:
        # Match whole words/phrases, not substrings inside unrelated words.
        pattern = r"(?<!\w)" + re.escape(term) + r"(?!\w)"
        if re.search(pattern, normalized, flags=re.IGNORECASE):
            found.append(term)
    return found

def fmt_time(seconds):
    seconds = max(0.0, float(seconds))
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    if hours:
        return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"
    return f"{minutes:02d}:{secs:06.3f}"

st.title("🎧 Censura Audio")
st.caption("Transcripción local con marcas de tiempo y detección de palabras para revisar.")

with st.sidebar:
    st.header("Configuración")
    model_size = st.selectbox(
        "Modelo de transcripción",
        ["small", "base", "medium", "large-v3"],
        index=0,
        help="small ofrece un buen equilibrio. medium/large-v3 suelen ser más precisos, pero necesitan más memoria y tardan más."
    )
    device_choice = st.selectbox("Procesamiento", ["CPU", "GPU NVIDIA"], index=0)
    compute_type = "int8" if device_choice == "CPU" else "float16"
    language_choice = st.selectbox(
        "Idioma del audio", ["Español", "Detectar automáticamente", "Inglés", "Portugués", "Francés"],
        index=0
    )
    language_map = {
        "Español": "es", "Detectar automáticamente": None, "Inglés": "en",
        "Portugués": "pt", "Francés": "fr"
    }
    st.caption("La primera ejecución descarga el modelo seleccionado. Después, el audio se procesa en este ordenador.")

left, right = st.columns([1, 1])
with left:
    st.subheader("1. Audio")
    uploaded = st.file_uploader(
        "Carga un archivo de audio",
        type=["mp3", "wav", "m4a", "aac", "flac", "ogg", "wma"],
        help="Formatos comunes de audio. Para mayor compatibilidad, convierte archivos raros a WAV o MP3."
    )
    if uploaded:
        st.audio(uploaded)

with right:
    st.subheader("2. Palabras que buscar")
    terms_text = st.text_area(
        "Lista de palabras o expresiones (separadas por líneas o comas)",
        value=DEFAULT_WORDS,
        height=245,
        help="Edita la lista según las normas editoriales del programa. Se buscan palabras completas y frases."
    )
    terms = parse_terms(terms_text)
    st.caption(f"{len(terms)} términos configurados.")

st.info("Privacidad: la transcripción se ejecuta localmente. El modelo puede descargarse de internet la primera vez; el archivo de audio no se envía a un servicio de transcripción.")

if "transcript_result" not in st.session_state:
    st.session_state.transcript_result = None

if st.button("Transcribir y detectar palabras", type="primary", disabled=(uploaded is None)):
    if not terms:
        st.warning("Añade al menos una palabra a la lista de detección.")
    else:
        tmp_path = None
        try:
            suffix = Path(uploaded.name).suffix or ".audio"
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(uploaded.getbuffer())
                tmp_path = tmp.name

            with st.spinner("Cargando el modelo y transcribiendo... En la primera ejecución puede tardar más."):
                model = load_model(model_size, "cuda" if device_choice == "GPU NVIDIA" else "cpu", compute_type)
                segments, info = model.transcribe(
                    tmp_path,
                    language=language_map[language_choice],
                    word_timestamps=True,
                    vad_filter=True,
                    beam_size=5
                )
                rows = []
                transcript_segments = []
                for seg in segments:
                    words_in_seg = []
                    if seg.words:
                        for w in seg.words:
                            word_text = (w.word or "").strip()
                            found = matches_term(word_text, terms)
                            row = {
                                "start": float(w.start),
                                "end": float(w.end),
                                "word": word_text,
                                "matched_terms": ", ".join(found),
                                "flagged": bool(found)
                            }
                            rows.append(row)
                            words_in_seg.append(row)
                    # Detect multi-word expressions by matching consecutive recognized words.
                    for term in terms:
                        phrase_tokens = term.split()
                        if len(phrase_tokens) < 2 or not words_in_seg:
                            continue
                        normalized_words = [
                            re.sub(r"^[^\\wáéíóúüñ]+|[^\\wáéíóúüñ]+$", "", x["word"].lower(), flags=re.UNICODE)
                            for x in words_in_seg
                        ]
                        for start_idx in range(0, len(normalized_words) - len(phrase_tokens) + 1):
                            candidate = normalized_words[start_idx:start_idx + len(phrase_tokens)]
                            if candidate == phrase_tokens:
                                for matched_word in words_in_seg[start_idx:start_idx + len(phrase_tokens)]:
                                    matched_word["flagged"] = True
                                    existing = [x for x in matched_word["matched_terms"].split(", ") if x]
                                    if term not in existing:
                                        existing.append(term)
                                    matched_word["matched_terms"] = ", ".join(existing)
                    if words_in_seg:
                        seg_text = " ".join(x["word"] for x in words_in_seg)
                    else:
                        seg_text = (seg.text or "").strip()
                    transcript_segments.append({
                        "start": float(seg.start), "end": float(seg.end),
                        "text": seg_text, "words": words_in_seg
                    })
                st.session_state.transcript_result = {
                    "rows": rows,
                    "segments": transcript_segments,
                    "language": info.language,
                    "duration": info.duration,
                    "filename": uploaded.name,
                    "terms": terms
                }
        except Exception as e:
            st.error(f"No se pudo transcribir el archivo: {e}")
            st.caption("Si seleccionaste GPU NVIDIA y falla, prueba CPU. En Windows puede ser necesario instalar FFmpeg.")
        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.remove(tmp_path)

result = st.session_state.transcript_result
if result:
    st.divider()
    st.subheader("3. Resultados")
    flagged = [r for r in result["rows"] if r["flagged"]]
    c1, c2, c3 = st.columns(3)
    c1.metric("Idioma detectado", result["language"].upper())
    c2.metric("Palabras transcritas", len(result["rows"]))
    c3.metric("Coincidencias", len(flagged))
    st.caption(f"Archivo: {result['filename']} · Duración aproximada: {fmt_time(result['duration'])}")

    tab_hits, tab_text = st.tabs(["Coincidencias para revisar", "Transcripción completa"])
    with tab_hits:
        if not flagged:
            st.success("No se encontraron coincidencias con la lista actual. Revisa igualmente el audio: el reconocimiento no es infalible.")
        else:
            st.write("Pulsa el tiempo para localizar el fragmento en tu editor. Los tiempos corresponden a las palabras reconocidas.")
            for i, row in enumerate(flagged, 1):
                st.markdown(
                    f"**{i}. `{fmt_time(row['start'])}` – `{fmt_time(row['end'])}`**  \n"
                    f"Palabra detectada: **{row['word']}** · Coincide con: {row['matched_terms']}"
                )
        csv_buffer = io.StringIO()
        writer = csv.DictWriter(csv_buffer, fieldnames=["start", "end", "start_time", "end_time", "word", "matched_terms"])
        writer.writeheader()
        for r in flagged:
            writer.writerow({
                "start": round(r["start"], 3), "end": round(r["end"], 3),
                "start_time": fmt_time(r["start"]), "end_time": fmt_time(r["end"]),
                "word": r["word"], "matched_terms": r["matched_terms"]
            })
        st.download_button("Descargar coincidencias (CSV)", csv_buffer.getvalue().encode("utf-8-sig"),
                           file_name="coincidencias_censura.csv", mime="text/csv")

    with tab_text:
        for seg in result["segments"]:
            if seg["words"]:
                rendered = []
                for w in seg["words"]:
                    if w["flagged"]:
                        rendered.append(f"**🔴 {w['word']}**")
                    else:
                        rendered.append(w["word"])
                text_line = " ".join(rendered)
            else:
                text_line = seg["text"]
            st.markdown(f"`{fmt_time(seg['start'])}`  {text_line}")
        full_text = "\n".join(
            f"[{fmt_time(seg['start'])}] {seg['text']}" for seg in result["segments"]
        )
        st.download_button("Descargar transcripción (TXT)", full_text,
                           file_name="transcripcion.txt", mime="text/plain")

st.divider()
st.caption("Prototipo inicial: las coincidencias dependen de lo que el modelo logre reconocer. Revisa siempre los fragmentos antes de censurar; puede haber falsos positivos y palabras no detectadas.")
