"""Un solo Chromium (Playwright) por corrida, compartido por las fuentes que lo necesitan; se abre al primer uso."""
import atexit
import os

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
_estado: dict = {}


def contexto():
    if "ctx" not in _estado:
        from playwright.sync_api import sync_playwright   # import tardío: solo si alguna fuente lo usa

        pw = sync_playwright().start()
        ruta = os.getenv("PLAYWRIGHT_CHROMIUM_PATH")   # opcional: Chromium ya instalado en otra ruta
        navegador = pw.chromium.launch(executable_path=ruta) if ruta else pw.chromium.launch()
        _estado.update(pw=pw, navegador=navegador,
                       ctx=navegador.new_context(user_agent=UA, locale="en-US"))
        atexit.register(cerrar)
    return _estado["ctx"]


def cerrar() -> None:
    if "ctx" in _estado:
        try:
            _estado["navegador"].close()
            _estado["pw"].stop()
        except Exception:
            pass
        _estado.clear()
