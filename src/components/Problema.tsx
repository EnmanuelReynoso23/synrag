import { Seccion } from './ui';

// Salidas reales sobre Flask (commit d086db8), 17-oct-2026. Tamaños = caracteres / 4.
const SIN = `> grep -rn "open_session" src/
src/flask/sessions.py:104:  :meth:\`open_session\` and :meth:\`save_session\`...
src/flask/sessions.py:107:  The session object returned by the :meth:\`open_session\`...
src/flask/sessions.py:115:  If :meth:\`open_session\` returns \`\`None\`\` Flask will...
src/flask/sessions.py:249:  def open_session(self, app, request) -> SessionMixin | None:
src/flask/sessions.py:323:  def open_session(self, app, request) -> SecureCookieSession | None:
src/flask/testing.py:165:   sess = app.session_interface.open_session(...)
src/flask/ctx.py:388:       self._session = si.open_session(self.app, self.request)
...

> leer src/flask/sessions.py      ~3.700 tokens
> leer src/flask/ctx.py           ~4.600 tokens
> ¿cuál de las dos es? otra búsqueda, otra lectura...`;

const CON = `> search_desktop("SecureCookieSessionInterface open_session")

src/flask/sessions.py:323-335 method open_session
def open_session(self, app, request) -> SecureCookieSession | None:
    s = self.get_signing_serializer(app)
    if s is None:
        return None
    val = request.cookies.get(self.get_cookie_name(app))
    if not val:
        return self.session_class()
    max_age = int(app.permanent_session_lifetime.total_seconds())
    try:
        data = s.loads(val, max_age=max_age)
        return self.session_class(data)
    except BadSignature:
        return self.session_class()
Usos: sessions.py:104 SessionInterface, :107, :115
Otros:
- src/flask/sessions.py:249-261 method open_session | def open_session(...)
- src/flask/app.py:247-251 class Flask | session_interface = SecureCookieSessionInterface()
- docs/api.rst:92-121 section Session Interface | API > Session Interface`;

export const Problema: React.FC = () => (
  <Seccion
    id="problema"
    etiqueta="El problema"
    titulo="Los agentes gastan la mayor parte de sus tokens orientándose"
    intro={
      <>
        <p>
          Para cambiar una función, un agente de código busca con <code className="text-[#E6EDF3]">grep</code>, abre archivos enteros
          para entender el contexto, vuelve a buscar y vuelve a leer. Todo eso entra en el historial de la conversación, y el historial
          se reenvía completo en cada turno: lo que se leyó al principio se paga una y otra vez.
        </p>
        <p className="mt-3">
          SynRAG cambia ese primer paso. En lugar de líneas sueltas o archivos completos, devuelve el bloque sintáctico exacto (la
          función, el método o el tipo entero), una línea con dónde se usa y, debajo, el resto de coincidencias en una línea cada una.
        </p>
      </>
    }
  >
    <div className="grid gap-6 lg:grid-cols-2">
      <figure className="syn-card overflow-hidden rounded-xl">
        <figcaption className="flex items-center justify-between border-b border-[#30363D] px-4 py-3 text-sm">
          <span className="font-semibold text-white">Sin SynRAG</span>
          <span className="font-mono text-xs text-[#F85149]">buscar, leer, repetir</span>
        </figcaption>
        <pre className="overflow-x-auto p-4 font-mono text-[12px] leading-relaxed text-[#8B949E]">{SIN}</pre>
      </figure>
      <figure className="syn-card overflow-hidden rounded-xl">
        <figcaption className="flex items-center justify-between border-b border-[#30363D] px-4 py-3 text-sm">
          <span className="font-semibold text-white">Con SynRAG</span>
          <span className="font-mono text-xs text-[#3FB950]">una llamada, el bloque justo</span>
        </figcaption>
        <pre className="overflow-x-auto p-4 font-mono text-[12px] leading-relaxed text-[#E6EDF3]">{CON}</pre>
      </figure>
    </div>
    <p className="mt-4 text-xs text-[#8B949E]">
      Salidas reales sobre el repositorio público de Flask (recortadas a lo ancho). Con dos palabras, "Clase miembro", SynRAG
      entrega el método de esa clase y no el de la clase base que está en el mismo archivo.
    </p>
  </Seccion>
);
