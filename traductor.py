# =============================================================================
# MÓDULO: TRADUCTOR ONTOLOGÍA → EXPERTA + SISTEMA EXPERTO
# Práctica 1 – Introducción a la IA (3010476) – UNAL Medellín
# =============================================================================

import rdflib
from rdflib.namespace import RDF, RDFS, OWL, XSD
import owlrl


import collections.abc
if not hasattr(collections, 'Mapping'):
    collections.Mapping = collections.abc.Mapping


# ── Importación COMPLETA de Experta ──────────────────────────────────────────
# Bug original: solo se importaba Fact y KnowledgeEngine
from experta import (
    Fact, KnowledgeEngine, Rule, AS, MATCH, W, NOT, TEST,
    DefFacts, OR, AND
)

# =============================================================================
# NAMESPACES DE LA ONTOLOGÍA
# =============================================================================
EX   = rdflib.Namespace("http://example.org/seguros#")
FOAF = rdflib.Namespace("http://xmlns.com/foaf/0.1/")
DC   = rdflib.Namespace("http://purl.org/dc/elements/1.1/")


# =============================================================================
# 1. CLASES DE HECHOS
#    Requisito: mínimo 5. Se definen TODAS las necesarias ANTES del motor,
#    incluyendo las que las reglas referencian pero estaban ausentes.
# =============================================================================

class OntoTriple(Fact):
    """Tripleta genérica del grafo RDF inferido (s, p, o).
    Cumple el requisito de traducir TODAS las tripletas sin excepción."""
    pass  # campos: s (str), p (str), o (str|int|float|bool)

class Cliente(Fact):
    """Persona que contrata la póliza (ex:Cliente)."""
    pass  # campos: id, nombre, edad, puntaje_salud, ingreso_mensual

class Persona(Fact):
    """
    Hecho de persona para las reglas del motor.
    Combina datos demográficos y de estilo de vida en un solo hecho
    para que las reglas sean legibles.
    """
    pass  # campos: id, nombre, edad, tieneHabitoFumador, ingresosMensuales,
          #         indice_estilo_vida, indice_riesgo_laboral

class SeguroVida(Fact):
    """Contrato de seguro de vida (ex:SeguroVida)."""
    pass  # campos: id, identificador, costo

class Poliza(Fact):
    """Póliza que formaliza el seguro (ex:Poliza)."""
    pass  # campos: id, cliente_id, suma_asegurada, fecha_inicio

class RequisitoSeguro(Fact):
    """
    Agrupa coberturas y datos del seguro para las reglas financieras.
    Bug original: la clase se usaba en las reglas pero no estaba definida.
    """
    pass  # campos: id, montoAsegurado, duracionContrato

class CondicionSalud(Fact):
    """
    Estado de salud / enfermedad previa de un cliente.
    Bug original: clase usada en reglas pero nunca definida.
    Deriva gradoSeveridad desde tieneIndiceSalud de la ontología.
    """
    pass  # campos: id, indiceSalud, esCronica, gradoSeveridad (Bajo/Medio/Alto)

class EstadoSalud(Fact):
    """Instancia de ex:EstadoSalud de la ontología (raw)."""
    pass  # campos: id, label, indica_salud

class EstiloVida(Fact):
    """Instancia de ex:EstiloVida de la ontología (raw)."""
    pass  # campos: id, label, indice_estilo_vida, es_fumador

class Trabajo(Fact):
    """Instancia de ex:Trabajo de la ontología (raw)."""
    pass  # campos: id, label, indice_riesgo_laboral

class Beneficiario(Fact):
    """Beneficiario del seguro (ex:Beneficiario)."""
    pass  # campos: id, nombre

class PerfilDeRiesgoOnto(Fact):
    """Instancia de ex:PerfilDeRiesgo de la ontología (raw)."""
    pass  # campos: id, label, indice_riesgo

class PerfilRiesgo(Fact):
    """
    Perfil de riesgo calculado por el motor de reglas durante la inferencia.
    Bug original: clase usada en reglas (salience 50/10) pero no definida.
    """
    pass  # campos: puntuacion, estado, factorMultiplicadorPrecio, procesado

class RecomendacionFinal(Fact):
    """
    Decisión final del sistema experto.
    Bug original: clase usada en reglas finales pero no definida.
    """
    pass  # campos: decision, motivo

class PerfilRiesgoDifuso(Fact):
    """Salida crisp de la lógica difusa (Scikit-Fuzzy → Experta)."""
    pass  # campos: etiqueta (str), valor (float 0-100)


# =============================================================================
# 2. UTILIDADES DE NORMALIZACIÓN DE URI
# =============================================================================

def uri_a_curie(grafo: rdflib.Graph, uri) -> str:
    """
    Convierte una URI a notación prefijada (CURIE).
    Ej: http://example.org/seguros#Cliente  →  ex:Cliente

    Bug original: se llamaba a normalizeUri() que NO existe en rdflib.
    El método correcto es compute_qname() que devuelve (prefix, ns, nombre).
    """
    if isinstance(uri, rdflib.Literal):
        return str(uri)
    try:
        prefix, _, nombre = grafo.namespace_manager.compute_qname(str(uri))
        return f"{prefix}:{nombre}"
    except Exception:
        # URI fuera de los namespaces registrados → usar la URI completa
        return str(uri)


def literal_a_python(valor):
    """
    Convierte un Literal RDF a su tipo Python nativo.
    rdflib.Literal tiene .toPython() pero lanza excepciones en algunos casos;
    esta función añade manejo de errores.
    """
    if isinstance(valor, rdflib.Literal):
        try:
            return valor.toPython()
        except Exception:
            return str(valor)
    return str(valor)


# =============================================================================
# 3. CARGA Y RAZONAMIENTO SEMÁNTICO
# =============================================================================

def preparar_ontologia(archivo_turtle: str) -> rdflib.Graph:
    """
    Carga el archivo Turtle y aplica razonamiento RDFS con OWL-RL.
    El grafo resultante contiene tanto las tripletas originales como
    todas las inferidas (subClassOf, subPropertyOf, dominio/rango, etc.).
    """
    g = rdflib.Graph()

    # Registrar prefijos para que compute_qname() funcione correctamente
    g.bind("ex",   EX)
    g.bind("foaf", FOAF)
    g.bind("dc",   DC)
    g.bind("xsd",  XSD)
    g.bind("owl",  OWL)
    g.bind("rdfs", RDFS)
    g.bind("rdf",  RDF)

    g.parse(archivo_turtle, format="turtle")
    tripletas_antes = len(g)

    # Razonador OWL-RL con semántica RDFS (requisito de la práctica)
    owlrl.DeductiveClosure(owlrl.RDFS_Semantics).expand(g)

    tripletas_despues = len(g)
    print(f"[Ontología] Tripletas antes del razonamiento : {tripletas_antes}")
    print(f"[Ontología] Tripletas después del razonamiento: {tripletas_despues}")
    print(f"[Ontología] Nuevas tripletas inferidas        : {tripletas_despues - tripletas_antes}")
    return g


# =============================================================================
# 4. TRADUCTOR: ONTOLOGÍA → HECHOS DE EXPERTA
#    Requisito: TODAS las tripletas deben traducirse sin excepción.
#    Estrategia de dos pasadas:
#      Pasada 1 – Recolectar propiedades de cada sujeto en un diccionario.
#      Pasada 2 – Declarar OntoTriple genérico + Facts específicos por tipo.
# =============================================================================

def _derivar_grado_severidad(indice_salud: float) -> str:
    """
    Mapea el índice de salud (0-100) a un grado de severidad para CondicionSalud.
    La lógica se invierte: alto índice de salud → bajo grado de riesgo.
    """
    if indice_salud >= 70:
        return "Bajo"
    elif indice_salud >= 40:
        return "Medio"
    else:
        return "Alto"


def _es_fumador_por_estilo(indice_estilo: float, label: str) -> bool:
    """
    Infiere si un estilo de vida corresponde a hábito fumador.
    Usa la etiqueta de la ontología o un umbral bajo del índice.
    """
    label_lower = label.lower()
    return "fumador" in label_lower or indice_estilo <= 30


def traductor_ontologia_a_experta(engine: KnowledgeEngine,
                                  grafo: rdflib.Graph) -> None:
    """
    Convierte el grafo RDF inferido en hechos del motor Experta.

    ── PASADA 1: Recolección ──────────────────────────────────────────────────
    Construye un diccionario  sujeto → {predicado: [objetos]}
    procesando cada tripleta (s, p, o) del grafo.

    ── PASADA 2: Declaración ──────────────────────────────────────────────────
    a) OntoTriple genérico para CADA tripleta  (cumple requisito de la práctica)
    b) Fact específico según el rdf:type del sujeto
    c) Facts compuestos (Persona, CondicionSalud, RequisitoSeguro) que
       las reglas del motor necesitan
    """
    print(f"\n[Traductor] Iniciando traducción de {len(grafo)} tripletas...")

    # ── PASADA 1 ──────────────────────────────────────────────────────────────
    props: dict[str, dict] = {}   # sujeto_curie → {pred_curie: último_objeto}
    tipos: dict[str, list] = {}   # sujeto_curie → [curie_tipo, ...]

    for s, p, o in grafo:
        sujeto    = uri_a_curie(grafo, s)
        predicado = uri_a_curie(grafo, p)
        objeto    = (literal_a_python(o)
                     if isinstance(o, rdflib.Literal)
                     else uri_a_curie(grafo, o))

        # ── a) DECLARACIÓN GENÉRICA (sin excepción) ──────────────────────────
        engine.declare(OntoTriple(s=sujeto, p=predicado, o=objeto))

        # Acumular propiedades por sujeto
        if sujeto not in props:
            props[sujeto] = {}
        props[sujeto][predicado] = objeto   # última asignación prevalece

        # Acumular tipos
        if predicado in ("rdf:type", "a"):
            tipos.setdefault(sujeto, []).append(objeto)

    total_tripletas = len(grafo)
    print(f"[Traductor] {total_tripletas} OntoTriple declarados.")

    # ── PASADA 2: Declaración de Facts específicos ────────────────────────────
    clientes_declarados   = 0
    condiciones_declaradas = 0
    requisitos_declarados = 0

    for sujeto, atributos in props.items():
        tipo_list = tipos.get(sujeto, [])

        # ── CLIENTE / PERSONA ─────────────────────────────────────────────────
        if any("Cliente" in t for t in tipo_list):
            nombre        = atributos.get("foaf:name", "Desconocido")
            edad          = atributos.get("ex:tieneEdad", 0)
            puntaje_salud = atributos.get("ex:tienePuntajeSalud", 50)
            ingreso       = atributos.get("ex:ingresosMensuales", 5000)

            # Inferir hábito fumador: si el estilo de vida vinculado tiene
            # bajo índice o etiqueta "fumador" en sus propiedades
            estilo_uri  = atributos.get("ex:tieneEstiloVida", "")
            estilo_props = props.get(estilo_uri, {})
            indice_ev   = estilo_props.get("ex:tieneIndiceEstiloVida", 80)
            label_ev    = str(estilo_props.get("rdfs:label", ""))
            es_fumador  = _es_fumador_por_estilo(
                float(indice_ev) if indice_ev else 80, label_ev
            )

            # Inferir riesgo laboral desde el Trabajo vinculado
            trabajo_uri  = atributos.get("ex:trabajaEn", "")
            trabajo_props = props.get(trabajo_uri, {})
            indice_rl    = trabajo_props.get("ex:tieneIndiceRiesgoLaboral", 0)

            engine.declare(Cliente(
                id            = sujeto,
                nombre        = nombre,
                edad          = int(edad) if edad else 0,
                puntaje_salud = int(puntaje_salud) if puntaje_salud else 50,
                ingreso_mensual = float(ingreso),
            ))

            # Hecho Persona (el que las reglas del motor usan directamente)
            engine.declare(Persona(
                id                   = sujeto,
                nombre               = nombre,
                edad                 = int(edad) if edad else 0,
                tieneHabitoFumador   = es_fumador,
                ingresosMensuales    = float(ingreso),
                indice_estilo_vida   = float(indice_ev) if indice_ev else 80,
                indice_riesgo_laboral = float(indice_rl) if indice_rl else 0,
            ))
            clientes_declarados += 1

        # ── SEGURO DE VIDA ────────────────────────────────────────────────────
        elif any("SeguroVida" in t for t in tipo_list):
            engine.declare(SeguroVida(
                id           = sujeto,
                identificador = atributos.get("dc:identifier", ""),
                costo        = float(atributos.get("ex:costoSeguro", 0)),
            ))

        # ── PÓLIZA ────────────────────────────────────────────────────────────
        elif any("Poliza" in t for t in tipo_list):
            engine.declare(Poliza(
                id             = sujeto,
                cliente_id     = atributos.get("ex:aseguraA", ""),
                suma_asegurada = float(atributos.get("ex:sumaAseguradaTotal", 0)),
                fecha_inicio   = str(atributos.get("ex:fechaInicio", "")),
            ))

        # ── COBERTURA → RequisitoSeguro ───────────────────────────────────────
        elif any("Cobertura" in t for t in tipo_list):
            monto = atributos.get("ex:montoAsegurado", 0)
            engine.declare(RequisitoSeguro(
                id               = sujeto,
                montoAsegurado   = float(monto) if monto else 0,
                duracionContrato = int(atributos.get("ex:duracionContrato", 10)),
            ))
            requisitos_declarados += 1

        # ── ESTADO DE SALUD → CondicionSalud ─────────────────────────────────
        elif any("EstadoSalud" in t for t in tipo_list):
            indice = atributos.get("ex:tieneIndiceSalud", 50)
            indice_f = float(indice) if indice else 50
            engine.declare(EstadoSalud(
                id           = sujeto,
                label        = str(atributos.get("rdfs:label", "")),
                indice_salud = indice_f,
            ))
            # CondicionSalud es el hecho que usan las reglas del motor
            engine.declare(CondicionSalud(
                id             = sujeto,
                indiceSalud    = indice_f,
                esCronica      = indice_f < 50,   # índice bajo = condición crónica
                gradoSeveridad = _derivar_grado_severidad(indice_f),
            ))
            condiciones_declaradas += 1

        # ── ENFERMEDAD PREVIA → CondicionSalud crónica ───────────────────────
        elif any("EnfermedadPrevia" in t for t in tipo_list):
            engine.declare(CondicionSalud(
                id             = sujeto,
                indiceSalud    = 30,        # enfermedad previa = índice bajo
                esCronica      = True,
                gradoSeveridad = "Alto",
            ))
            condiciones_declaradas += 1

        # ── ANTECEDENTE FAMILIAR → CondicionSalud no crónica ─────────────────
        elif any("AntecedenteFamiliar" in t for t in tipo_list):
            engine.declare(CondicionSalud(
                id             = sujeto,
                indiceSalud    = 60,
                esCronica      = False,
                gradoSeveridad = "Medio",
            ))
            condiciones_declaradas += 1

        # ── ESTILO DE VIDA ────────────────────────────────────────────────────
        elif any("EstiloVida" in t for t in tipo_list):
            indice_ev = atributos.get("ex:tieneIndiceEstiloVida", 50)
            label_ev  = str(atributos.get("rdfs:label", ""))
            engine.declare(EstiloVida(
                id                = sujeto,
                label             = label_ev,
                indice_estilo_vida = float(indice_ev) if indice_ev else 50,
                es_fumador        = _es_fumador_por_estilo(
                    float(indice_ev) if indice_ev else 50, label_ev
                ),
            ))

        # ── TRABAJO ───────────────────────────────────────────────────────────
        elif any("Trabajo" in t for t in tipo_list):
            indice_rl = atributos.get("ex:tieneIndiceRiesgoLaboral", 0)
            engine.declare(Trabajo(
                id                    = sujeto,
                label                 = str(atributos.get("rdfs:label", "")),
                indice_riesgo_laboral = float(indice_rl) if indice_rl else 0,
            ))

        # ── BENEFICIARIO ──────────────────────────────────────────────────────
        elif any("Beneficiario" in t for t in tipo_list):
            engine.declare(Beneficiario(
                id     = sujeto,
                nombre = str(atributos.get("foaf:name", "")),
            ))

        # ── PERFIL DE RIESGO (ontología) ──────────────────────────────────────
        elif any("PerfilDeRiesgo" in t for t in tipo_list):
            engine.declare(PerfilDeRiesgoOnto(
                id           = sujeto,
                label        = str(atributos.get("rdfs:label", "")),
                indice_riesgo = int(atributos.get("ex:tieneIndiceRiesgo", 0)),
            ))

    print(f"[Traductor] Clientes/Personas declarados : {clientes_declarados}")
    print(f"[Traductor] CondicionSalud declaradas    : {condiciones_declaradas}")
    print(f"[Traductor] RequisitoSeguro declarados   : {requisitos_declarados}")
    print("[Traductor] Traducción completa.\n")


# =============================================================================
# 5. MOTOR DE REGLAS – SISTEMA EXPERTO
# =============================================================================

class RecomendadorSeguroVida(KnowledgeEngine):

    # ─────────────────────────────────────────────────────────────────────────
    # NIVEL ALTO – salience=100 (Filtros críticos y exclusiones)
    # Mecanismos: Especificidad (Regla 1), LIFO implícito (Regla 2)
    # ─────────────────────────────────────────────────────────────────────────

    @Rule(
        AS.p << Persona(tieneHabitoFumador=True),
        CondicionSalud(esCronica=True, gradoSeveridad="Alto"),
        salience=100
    )
    def riesgo_critico_salud(self, p):
        """Regla 1 (Especificidad): Fumador + Enfermedad crónica grave."""
        self.declare(PerfilRiesgo(
            puntuacion=100, estado="Critico",
            factorMultiplicadorPrecio=2.5, procesado=False
        ))
        print("REGLA 1 [salience=100]: Riesgo crítico — Fumador + Enfermedad Grave.")

    @Rule(
        Persona(ingresosMensuales=MATCH.ingresos),
        RequisitoSeguro(montoAsegurado=MATCH.monto),
        TEST(lambda ingresos, monto: monto > (ingresos * 120)),
        salience=100
    )
    def riesgo_financiero_extremo(self):
        """Regla 2 (LIFO): Desproporción entre ingresos y cobertura."""
        self.declare(PerfilRiesgo(
            puntuacion=80, estado="Riesgo Financiero",
            factorMultiplicadorPrecio=1.0, procesado=False
        ))
        print("REGLA 2 [salience=100]: Riesgo financiero — monto excesivo vs. ingresos.")

    @Rule(
        CondicionSalud(gradoSeveridad="Alto", esCronica=True),
        salience=100
    )
    def enfermedad_severa_unitaria(self):
        """Regla 3: Enfermedad crónica severa por sí sola."""
        self.declare(PerfilRiesgo(
            puntuacion=70, estado="Riesgo Salud",
            factorMultiplicadorPrecio=1.8, procesado=False
        ))
        print("REGLA 3 [salience=100]: Gravedad de salud — enfermedad severa.")

    # ─────────────────────────────────────────────────────────────────────────
    # NIVEL MEDIO – salience=40-50 (Ajustes y riesgo moderado)
    # Mecanismo anti-bucle: Lock-Fact (procesado=False → True)
    # ─────────────────────────────────────────────────────────────────────────

    @Rule(
        AS.f << PerfilRiesgo(puntuacion=MATCH.ptos, procesado=False),
        Persona(tieneHabitoFumador=True),
        salience=50
    )
    def ajuste_fumador(self, f, ptos):
        """Regla 4 (Lock-Fact): Ajuste por tabaquismo, se ejecuta UNA sola vez."""
        self.modify(f, puntuacion=ptos + 20,
                    factorMultiplicadorPrecio=1.5, procesado=True)
        print("REGLA 4 [salience=50]: Ajuste tabaquismo (+20 pts). Lock-Fact activado.")

    @Rule(
        AS.f << PerfilRiesgo(puntuacion=MATCH.ptos, procesado=False),
        CondicionSalud(esCronica=True, gradoSeveridad="Bajo"),
        salience=50
    )
    def ajuste_cronico_leve(self, f, ptos):
        """Regla 5 (Lock-Fact): Enfermedad crónica pero leve."""
        self.modify(f, puntuacion=ptos + 15,
                    factorMultiplicadorPrecio=1.2, procesado=True)
        print("REGLA 5 [salience=50]: Ajuste condición crónica leve (+15 pts).")

    @Rule(
        AS.f << PerfilRiesgo(puntuacion=MATCH.ptos, procesado=False),
        RequisitoSeguro(duracionContrato=MATCH.d),
        TEST(lambda d: d > 20),
        salience=50
    )
    def ajuste_largo_plazo(self, f, ptos):
        """Regla 6 (Lock-Fact): Contrato de muy larga duración."""
        self.modify(f, puntuacion=ptos + 10, procesado=True)
        print("REGLA 6 [salience=50]: Ajuste contrato largo plazo (+10 pts).")

    @Rule(
        Persona(ingresosMensuales=MATCH.i),
        TEST(lambda i: i > 10000),
        salience=50
    )
    def cliente_premium_financiero(self):
        """Regla 7: Ingresos altos → baja percepción de riesgo de impago."""
        self.declare(PerfilRiesgo(
            puntuacion=0, estado="Solvente",
            factorMultiplicadorPrecio=0.9, procesado=False
        ))
        print("REGLA 7 [salience=50]: Alta solvencia detectada.")

    @Rule(
        CondicionSalud(gradoSeveridad="Medio"),
        NOT(Persona(tieneHabitoFumador=True)),
        salience=50
    )
    def salud_intermedia_no_fumador(self):
        """Regla 8 (Especificidad): Salud media + no fumador → riesgo moderado."""
        self.declare(PerfilRiesgo(
            puntuacion=30, estado="Moderado",
            factorMultiplicadorPrecio=1.1, procesado=False
        ))
        print("REGLA 8 [salience=50]: Riesgo moderado — salud media, no fumador.")

    @Rule(
        Persona(tieneHabitoFumador=False),
        CondicionSalud(gradoSeveridad="Bajo"),
        salience=40
    )
    def perfil_saludable_base(self):
        """Regla 9: Perfil de bajo riesgo en salud."""
        self.declare(PerfilRiesgo(
            puntuacion=5, estado="Saludable",
            factorMultiplicadorPrecio=1.0, procesado=False
        ))
        print("REGLA 9 [salience=40]: Perfil saludable base.")

    @Rule(
        RequisitoSeguro(montoAsegurado=MATCH.m),
        TEST(lambda m: m < 50000),
        salience=40
    )
    def cobertura_baja(self):
        """Regla 10: Coberturas bajas → baja exposición para la aseguradora."""
        self.declare(PerfilRiesgo(
            puntuacion=0, estado="Baja Exposicion",
            factorMultiplicadorPrecio=1.0, procesado=False
        ))
        print("REGLA 10 [salience=40]: Baja exposición de capital.")

    # ─────────────────────────────────────────────────────────────────────────
    # REGLAS DE INTEGRACIÓN CON LÓGICA DIFUSA
    # Alimentan el motor con el resultado de Scikit-Fuzzy
    # ─────────────────────────────────────────────────────────────────────────

    @Rule(
        PerfilRiesgoDifuso(etiqueta="Muy Alto", valor=MATCH.v),
        salience=95   # Alta prioridad, por debajo de las exclusiones absolutas
    )
    def difuso_muy_alto(self, v):
        """Regla 11D: Resultado difuso 'Muy Alto' → incorporar al perfil."""
        self.declare(PerfilRiesgo(
            puntuacion=int(v), estado="Difuso-MuyAlto",
            factorMultiplicadorPrecio=2.0, procesado=False
        ))
        print(f"REGLA 11D [salience=95]: Perfil difuso MUY ALTO ({v:.1f}).")

    @Rule(
        PerfilRiesgoDifuso(etiqueta="Alto", valor=MATCH.v),
        salience=90
    )
    def difuso_alto(self, v):
        """Regla 12D: Resultado difuso 'Alto'."""
        self.declare(PerfilRiesgo(
            puntuacion=int(v), estado="Difuso-Alto",
            factorMultiplicadorPrecio=1.7, procesado=False
        ))
        print(f"REGLA 12D [salience=90]: Perfil difuso ALTO ({v:.1f}).")

    @Rule(
        PerfilRiesgoDifuso(etiqueta="Medio", valor=MATCH.v),
        salience=85
    )
    def difuso_medio(self, v):
        """Regla 13D: Resultado difuso 'Medio'."""
        self.declare(PerfilRiesgo(
            puntuacion=int(v), estado="Difuso-Medio",
            factorMultiplicadorPrecio=1.3, procesado=False
        ))
        print(f"REGLA 13D [salience=85]: Perfil difuso MEDIO ({v:.1f}).")

    @Rule(
        PerfilRiesgoDifuso(etiqueta="Bajo", valor=MATCH.v),
        salience=80
    )
    def difuso_bajo(self, v):
        """Regla 14D: Resultado difuso 'Bajo'."""
        self.declare(PerfilRiesgo(
            puntuacion=int(v), estado="Difuso-Bajo",
            factorMultiplicadorPrecio=1.0, procesado=False
        ))
        print(f"REGLA 14D [salience=80]: Perfil difuso BAJO ({v:.1f}).")

    # ─────────────────────────────────────────────────────────────────────────
    # NIVEL BAJO – salience=1-10 (Recomendación final)
    # ─────────────────────────────────────────────────────────────────────────

    @Rule(
        PerfilRiesgo(puntuacion=MATCH.p),
        TEST(lambda p: p >= 70),
        NOT(RecomendacionFinal()),      # Recencia: solo si aún no hay decisión
        salience=10
    )
    def recomendacion_rechazo(self, p):
        """Regla 15: Riesgo >= 70 → NO APROBAR."""
        self.declare(RecomendacionFinal(
            decision="NO APROBAR", motivo="Riesgo potencial muy alto"
        ))
        print(f"REGLA 15 [salience=10]: No aprobado — puntuación {p}.")

    @Rule(
        PerfilRiesgo(puntuacion=MATCH.p),
        TEST(lambda p: 30 < p < 70),
        NOT(RecomendacionFinal()),
        salience=10
    )
    def recomendacion_estudio(self, p):
        """Regla 16: 30 < riesgo < 70 → ESTUDIO MANUAL."""
        self.declare(RecomendacionFinal(
            decision="ESTUDIO MANUAL", motivo="Riesgo intermedio"
        ))
        print(f"REGLA 16 [salience=10]: Revisión manual — puntuación {p}.")

    @Rule(
        PerfilRiesgo(puntuacion=MATCH.p),
        TEST(lambda p: p <= 30),
        NOT(RecomendacionFinal()),
        salience=10
    )
    def recomendacion_aprobacion(self, p):
        """Regla 17: Riesgo <= 30 → APROBAR."""
        self.declare(RecomendacionFinal(
            decision="APROBAR", motivo="Riesgo bajo/aceptable"
        ))
        print(f"REGLA 17 [salience=10]: Aprobación recomendada — puntuación {p}.")

    @Rule(
        AS.r << RecomendacionFinal(decision="APROBAR"),
        PerfilRiesgo(factorMultiplicadorPrecio=MATCH.f),
        salience=5
    )
    def calcular_precio_final(self, r, f):
        """Regla 18: Calcular factor de precio solo para aprobados."""
        print(f"REGLA 18 [salience=5]: Factor de precio final: {f:.2f}x")

    @Rule(
        RecomendacionFinal(decision=MATCH.d, motivo=MATCH.m),
        salience=1
    )
    def imprimir_resultado(self, d, m):
        """Regla 19: Cierre del proceso — imprime la decisión final."""
        print(f"\n{'='*60}")
        print(f"  RESULTADO DEL SISTEMA EXPERTO")
        print(f"  Decisión : {d}")
        print(f"  Motivo   : {m}")
        print(f"{'='*60}\n")


# =============================================================================
# 6. FLUJO HÍBRIDO COMPLETO
# =============================================================================

def ejecutar_sistema_hibrido(
    archivo_turtle: str = "seguros.ttl",
    valor_difuso: float = 60.8,
    etiqueta_difusa: str = "Alto"
) -> None:
    """
    Orquesta los tres componentes del sistema híbrido:
      1. Ontología RDF/RDFS → razonamiento OWL-RL
      2. Lógica difusa (recibe resultado crisp de Scikit-Fuzzy como parámetro)
      3. Sistema experto Experta
    """
    print("=" * 60)
    print("  SISTEMA HÍBRIDO DE IA – SEGURO DE VIDA")
    print("=" * 60)

    # ── Componente 1: Ontología ───────────────────────────────────────────────
    grafo_rdf = preparar_ontologia(archivo_turtle)

    # ── Componente 3: Motor Experto ───────────────────────────────────────────
    engine = RecomendadorSeguroVida()
    engine.reset()

    # ── Integración 1→3: Ontología alimenta al motor ──────────────────────────
    traductor_ontologia_a_experta(engine, grafo_rdf)

    # ── Integración 2→3: Lógica difusa alimenta al motor ─────────────────────
    # En el sistema completo, este valor viene de la defuzzificación de Scikit-Fuzzy.
    # El etiquetado se hace según los umbrales de las variables difusas del avance:
    #   0-25  → "Bajo" | 25-50 → "Medio" | 50-75 → "Alto" | 75-100 → "Muy Alto"
    engine.declare(PerfilRiesgoDifuso(etiqueta=etiqueta_difusa, valor=valor_difuso))
    print(f"[Lógica Difusa] Resultado crisp: {valor_difuso:.1f} → etiqueta '{etiqueta_difusa}'")

    # ── Ejecutar inferencia ───────────────────────────────────────────────────
    print("\n--- Iniciando motor de inferencia ---\n")
    engine.run()


# =============================================================================
# PUNTO DE ENTRADA
# =============================================================================
if __name__ == "__main__":
    ejecutar_sistema_hibrido(
        archivo_turtle   = "seguros.ttl",
        valor_difuso     = 60.8,
        etiqueta_difusa  = "Alto"
    )