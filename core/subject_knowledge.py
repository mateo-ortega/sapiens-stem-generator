"""
Base de datos curada de conocimiento verificado por área temática.

Provee constantes físicas, datos del mundo real, contextos industriales
y concepciones erróneas comunes para alimentar la generación de problemas
con datos verosímiles y pedagógicamente útiles.
"""

# ---------------------------------------------------------------------------
# Constantes físicas fundamentales (CODATA 2018)
# ---------------------------------------------------------------------------

PHYSICAL_CONSTANTS = {
    "velocidad_de_la_luz": {"valor": 2.998e8, "unidad": "m/s", "símbolo": "c"},
    "constante_de_Planck": {"valor": 6.626e-34, "unidad": "J·s", "símbolo": "h"},
    "constante_de_Boltzmann": {"valor": 1.381e-23, "unidad": "J/K", "símbolo": "k_B"},
    "número_de_Avogadro": {"valor": 6.022e23, "unidad": "mol⁻¹", "símbolo": "N_A"},
    "constante_de_gases": {"valor": 8.314, "unidad": "J/(mol·K)", "símbolo": "R"},
    "carga_del_electrón": {"valor": 1.602e-19, "unidad": "C", "símbolo": "e"},
    "constante_gravitacional": {"valor": 6.674e-11, "unidad": "N·m²/kg²", "símbolo": "G"},
    "gravedad_terrestre": {"valor": 9.807, "unidad": "m/s²", "símbolo": "g"},
    "constante_de_Faraday": {"valor": 96485, "unidad": "C/mol", "símbolo": "F"},
    "constante_de_Stefan_Boltzmann": {"valor": 5.670e-8, "unidad": "W/(m²·K⁴)", "símbolo": "σ"},
    "permitividad_del_vacío": {"valor": 8.854e-12, "unidad": "F/m", "símbolo": "ε₀"},
    "permeabilidad_del_vacío": {"valor": 1.257e-6, "unidad": "H/m", "símbolo": "μ₀"},
}

# ---------------------------------------------------------------------------
# Datos del mundo real verificados
# ---------------------------------------------------------------------------

REAL_WORLD_DATA = {
    "tierra": {
        "radio_medio": {"valor": 6.371e6, "unidad": "m"},
        "masa": {"valor": 5.972e24, "unidad": "kg"},
        "distancia_al_sol": {"valor": 1.496e11, "unidad": "m"},
        "presión_atmosférica_nivel_del_mar": {"valor": 101325, "unidad": "Pa"},
        "temperatura_media_superficie": {"valor": 288, "unidad": "K"},
    },
    "agua": {
        "densidad_a_20C": {"valor": 998.2, "unidad": "kg/m³"},
        "calor_específico": {"valor": 4186, "unidad": "J/(kg·K)"},
        "calor_de_vaporización": {"valor": 2.257e6, "unidad": "J/kg"},
        "calor_de_fusión": {"valor": 3.34e5, "unidad": "J/kg"},
        "punto_de_ebullición": {"valor": 373.15, "unidad": "K"},
        "punto_de_fusión": {"valor": 273.15, "unidad": "K"},
        "viscosidad_a_20C": {"valor": 1.002e-3, "unidad": "Pa·s"},
        "conductividad_térmica": {"valor": 0.606, "unidad": "W/(m·K)"},
    },
    "aire": {
        "densidad_a_20C_1atm": {"valor": 1.204, "unidad": "kg/m³"},
        "calor_específico_cp": {"valor": 1005, "unidad": "J/(kg·K)"},
        "viscosidad_a_20C": {"valor": 1.825e-5, "unidad": "Pa·s"},
        "conductividad_térmica": {"valor": 0.0257, "unidad": "W/(m·K)"},
        "masa_molar_promedio": {"valor": 0.02897, "unidad": "kg/mol"},
    },
    "materiales_comunes": {
        "acero_densidad": {"valor": 7850, "unidad": "kg/m³"},
        "acero_resistencia_tracción": {"valor": 400e6, "unidad": "Pa"},
        "cobre_conductividad_eléctrica": {"valor": 5.96e7, "unidad": "S/m"},
        "cobre_conductividad_térmica": {"valor": 401, "unidad": "W/(m·K)"},
        "aluminio_densidad": {"valor": 2700, "unidad": "kg/m³"},
        "vidrio_conductividad_térmica": {"valor": 1.05, "unidad": "W/(m·K)"},
        "concreto_resistencia_compresión": {"valor": 30e6, "unidad": "Pa"},
    },
}

# ---------------------------------------------------------------------------
# Niveles educativos canónicos (orden de menor a mayor complejidad)
# ---------------------------------------------------------------------------

LEVEL_KEYS = ["primaria", "secundaria", "preparatoria", "universitario", "avanzado"]


def normalize_level_key(level: str) -> str:
    """
    Normaliza una entrada de nivel (texto libre o canónica) a una de las claves de LEVEL_KEYS.

    Acepta tanto la forma exacta del dropdown ("Primaria", "Universitario") como
    texto libre legacy ("univ", "bachillerato", "posgrado"). Cae a "universitario"
    como default seguro.
    """
    s = (level or "").lower().strip()
    if not s:
        return "universitario"
    if s in LEVEL_KEYS:
        return s
    for key in LEVEL_KEYS:
        if key in s:
            return key
    if any(t in s for t in ("univ", "pregrado")):
        return "universitario"
    if any(t in s for t in ("posgrado", "doctorado", "máster", "master", "phd")):
        return "avanzado"
    if any(t in s for t in ("bachill", "media", "preuniv")):
        return "preparatoria"
    if any(t in s for t in ("school", "elemental", "kinder", "infantil")):
        return "primaria"
    return "universitario"


# ---------------------------------------------------------------------------
# Contextos reales por (área × nivel)
#
# Estructura: INDUSTRIAL_CONTEXTS[area][level_key] -> list[str]
# - primaria:      cotidianos + ciencia muy básica (lenguaje sencillo)
# - secundaria:    cotidianos avanzados + ciencia escolar
# - preparatoria:  introducción a contextos profesionales accesibles
# - universitario: contextos profesionales/industriales reales
# - avanzado:      investigación de frontera, posgrado, casos de estudio
# ---------------------------------------------------------------------------

INDUSTRIAL_CONTEXTS = {
    "science": {
        "primaria": [
            "El ciclo del agua — cómo la lluvia llega a los ríos y vuelve a las nubes",
            "Las estaciones del año — por qué hace más frío en algunos meses",
            "Los planetas del sistema solar — tamaños y distancias en el patio del colegio",
            "Animales del zoológico — qué comen y cuánto pesan",
            "La fotosíntesis — cómo las plantas usan la luz del sol para crecer",
            "El cuerpo humano — cuántos huesos, cuántos litros de sangre, cuántos latidos por minuto",
            "Los estados del agua — hielo, agua líquida y vapor en la cocina",
            "Mascotas comunes en Colombia — perros, gatos, peces y sus cuidados",
        ],
        "secundaria": [
            "Laboratorio escolar de química — medición de pH con papel tornasol en jugos y bebidas",
            "Experimento de péndulo simple — medir la gravedad con un cronómetro y una cuerda",
            "Reciclaje en el hogar — separación de residuos y kilos de plástico por familia/mes",
            "Calentamiento global — temperatura promedio de Medellín en los últimos 20 años",
            "Sistema solar — comparación de gravedades entre la Tierra, la Luna y Marte",
            "Reacciones cotidianas — vinagre con bicarbonato, oxidación del clavo en agua",
            "Energía en deportes — calorías que gasta un ciclista en El Poblado",
            "Microscopio escolar — observación de células de la cebolla y de la mejilla",
        ],
        "preparatoria": [
            "Caída libre — medición del tiempo de caída desde el segundo piso del colegio",
            "Estequiometría en el laboratorio — combustión del magnesio y rendimiento real",
            "Biología — extracción de ADN de una fresa con sal y alcohol",
            "Física del sonido — frecuencia de notas musicales y longitud de onda",
            "Energía solar — eficiencia de un panel pequeño en el techo de la casa",
            "Genética mendeliana — color de ojos en una familia y proporciones esperadas",
            "Termodinámica — calor cedido por un café caliente en un termo",
            "Ecología local — biodiversidad del Parque Arví o de un bosque cercano",
        ],
        "universitario": [
            "Reactor de fusión ITER en Cadarache, Francia — confinamiento de plasma a 150 millones de K",
            "Telescopio James Webb — detección de exoatmósferas y espectroscopia infrarroja",
            "CERN — colisiones protón-protón a 13.6 TeV en el LHC",
            "Estación Espacial Internacional — experimentos de microgravedad en cristalización de proteínas",
            "Laboratorio de bioseguridad nivel 4 — estudio de virus emergentes con PCR en tiempo real",
            "Planta desalinizadora por ósmosis inversa — producción de 500,000 m³/día de agua potable",
            "Reactor nuclear de agua presurizada (PWR) — generación de 1000 MW eléctricos",
            "Síntesis de amoniaco Haber-Bosch — 450°C, 200 atm, catalizador de hierro",
        ],
        "avanzado": [
            "Espectroscopia ATTO-segundo — observación de dinámica electrónica en moléculas",
            "Biología sintética — circuitos genéticos en E. coli para producción de insulina",
            "Materiales 2D — propiedades electrónicas del grafeno y del MoS₂ monocapa",
            "Detección de ondas gravitacionales — interferómetro LIGO con sensibilidad de 10⁻²¹ m",
            "Computación cuántica — corrección de errores en qubits superconductores (IBM Eagle, 127 qubits)",
            "CRISPR-Cas9 terapéutico — ensayos clínicos en anemia falciforme",
            "Metagenómica del microbioma intestinal — secuenciación de 16S rRNA en cohortes humanas",
            "Catálisis heterogénea avanzada — síntesis de Fischer-Tropsch con catalizadores de cobalto nanoestructurado",
        ],
    },
    "engineering": {
        "primaria": [
            "Cómo funciona una rueda — bicicletas, carros de juguete y patinetas",
            "Construir un puente sencillo con palitos de paleta",
            "El molino de viento — cómo el aire mueve las aspas",
            "Cómo se construye una casa — paredes, techo y cimientos",
            "El semáforo — cómo se coordinan los carros en una esquina",
            "Cómo funciona un ascensor — poleas y contrapesos en edificios sencillos",
            "Una linterna casera — pilas, cables y bombillo",
            "Construcción de un cohete de papel — alas y centro de gravedad",
        ],
        "secundaria": [
            "Robótica escolar con LEGO Mindstorms — programar un robot para seguir una línea",
            "Energía en una bicicleta — engranajes y multiplicación de velocidad",
            "Sistemas de riego en un huerto escolar — caudal y presión",
            "Construcción de un puente de espagueti — máxima carga antes de fallar",
            "Aerogenerador casero — turbina con vasos plásticos y motor de juguete",
            "Carro solar — panel pequeño moviendo un motor DC",
            "Sistema de filtración de agua casero — capas de arena, grava y carbón",
            "Catapulta de mesa — ángulo y alcance del proyectil",
        ],
        "preparatoria": [
            "Diseño de un puente Warren con cargas distribuidas — maqueta de feria de ciencias",
            "Circuito Arduino — sensor de temperatura controlando un ventilador",
            "Impresión 3D escolar — diseño de una pieza en Tinkercad y FDM en PLA",
            "Drone DIY — balance de fuerzas en vuelo estacionario",
            "Sistema de bombeo solar — caudal vs. radiación solar a lo largo del día",
            "Brazo robótico con servomotores — grados de libertad y cinemática inversa básica",
            "Reactor casero de biodiesel — transesterificación de aceite usado",
            "Estación meteorológica con Raspberry Pi — temperatura, humedad y presión",
        ],
        "universitario": [
            "Refinería de Ecopetrol en Barrancabermeja — destilación de crudo a 350°C",
            "Planta de tratamiento de aguas residuales — reactor de lodos activados, 50,000 m³/día",
            "Turbina eólica Vestas V164 — rotor de 164 m de diámetro, 9.5 MW nominales",
            "Intercambiador de calor de carcasa y tubos — 500 tubos de 25.4 mm OD, 6 m de largo",
            "Columna de destilación fraccionada — 40 platos, reflujo 2.5:1, alimentación en plato 20",
            "Reactor CSTR para polimerización de etileno — volumen 2 m³, T=80°C, P=30 bar",
            "Puente atirantado — luz principal de 890 m, cables de acero de alta resistencia",
            "Planta fotovoltaica de 100 MW — 300,000 paneles monocristalinos, eficiencia 22%",
        ],
        "avanzado": [
            "Reactor de membrana para deshidrogenación catalítica — selectividad >95% con paladio",
            "Sistemas microelectromecánicos (MEMS) — acelerómetros piezoeléctricos en smartphones",
            "Plataforma offshore flotante — análisis de fatiga estructural por oleaje irregular",
            "Captura y almacenamiento de CO₂ (CCS) — proyecto Sleipner en Noruega, 1 Mt/año",
            "Reactor SMR (Small Modular Reactor) — diseño NuScale de 77 MWe modular",
            "Manufactura aditiva metálica (DMLS) — turbinas de aviación con superaleaciones",
            "Vehículos autónomos nivel 4 — fusión sensorial LIDAR + cámara + radar",
            "Hidrógeno verde por electrólisis PEM — eficiencia 70%, costo objetivo <2 USD/kg",
        ],
    },
    "math": {
        "primaria": [
            "Comprar dulces en la tienda escolar — sumas, restas y dar vueltas en pesos colombianos",
            "Repartir una pizza entre amigos — fracciones simples y partes iguales",
            "Contar pasos al ir al colegio — distancias y promedios sencillos",
            "Mediciones en clase de educación física — saltos, lanzamientos y tiempos",
            "Una receta de torta — duplicar y reducir cantidades de ingredientes",
            "Edades de la familia — diferencias y comparaciones",
            "El reloj y los horarios escolares — cuánto dura el recreo en minutos",
            "Conteo de votos en el salón — porcentajes simples sobre 30 estudiantes",
        ],
        "secundaria": [
            "Presupuesto familiar mensual — porcentajes de mercado, transporte y servicios",
            "Estadísticas deportivas — promedio de goles del Atlético Nacional en la Liga",
            "Geometría en el barrio — área de la cancha de fútbol del colegio",
            "Descuentos en centro comercial — 30% off + 10% adicional, ¿cuánto se paga?",
            "Probabilidad en juegos — sacar una carta roja de la baraja",
            "Crecimiento de una planta — gráfica de altura vs. días",
            "Conversión de monedas — pesos colombianos a dólares con tasa del día",
            "Encuesta en el colegio — distribución de gustos musicales en gráfica de torta",
        ],
        "preparatoria": [
            "Movimiento parabólico — alcance máximo de un balón de fútbol",
            "Interés compuesto — ahorrar 100,000 pesos al mes durante 5 años al 6%",
            "Estadística descriptiva — calificaciones del salón con media, mediana y desviación",
            "Funciones trigonométricas — altura del sol a lo largo del día",
            "Combinatoria — número de placas vehiculares posibles en Colombia",
            "Modelación lineal — pronóstico de población de Medellín",
            "Áreas con integrales básicas — superficie de un terreno irregular",
            "Probabilidad condicional — pruebas médicas y falsos positivos",
        ],
        "universitario": [
            "Análisis de series temporales financieras — predicción de volatilidad del S&P 500",
            "Optimización de rutas logísticas — problema del viajante con 50 ciudades (TSP)",
            "Modelado epidemiológico SIR — propagación de COVID-19, R₀ = 2.5",
            "Criptografía RSA — factorización de semiprimos de 2048 bits",
            "Tomografía computarizada — reconstrucción de imagen por transformada de Radon",
            "Machine learning — regresión logística para clasificación de tumores (dataset Wisconsin)",
            "Dinámica de fluidos computacional — ecuaciones de Navier-Stokes discretizadas por volúmenes finitos",
            "Análisis de Fourier — procesamiento de señales sísmicas para detección de terremotos",
        ],
        "avanzado": [
            "Criptografía post-cuántica — esquemas basados en retículos (Kyber, Dilithium)",
            "Geometría diferencial en relatividad general — métricas de Schwarzschild y Kerr",
            "Optimización combinatoria de gran escala — branch-and-cut en TSP de 100,000 ciudades",
            "Teoría de categorías aplicada a tipos dependientes en programación funcional",
            "Procesos estocásticos — ecuación de Fokker-Planck para difusión en fluidos turbulentos",
            "Topología algebraica — análisis topológico de datos (TDA) en biología computacional",
            "Sistemas dinámicos no lineales — atractores extraños y exponentes de Lyapunov",
            "Inferencia bayesiana variacional — modelos jerárquicos en epidemiología espacial",
        ],
    },
    "cs": {
        "primaria": [
            "Cómo un robot sigue instrucciones — adelante, derecha, izquierda como pasos",
            "Juegos de computadora sencillos — niveles, vidas y puntaje",
            "Organizar libros en la biblioteca — orden alfabético como un algoritmo",
            "El semáforo y los estados — rojo, amarillo, verde como una secuencia",
            "Búsqueda en un diccionario impreso — buscar una palabra abriendo por la mitad",
            "Receta de cocina como algoritmo — pasos en orden para hacer un sándwich",
            "Pasos para vestirse — primero medias, después zapatos (orden importa)",
            "Cómo Google Maps muestra el camino al colegio — punto A al punto B",
        ],
        "secundaria": [
            "Programación con Scratch — animar un personaje con bloques de eventos",
            "Lógica básica — verdadero/falso en un detector de spam sencillo",
            "Hojas de cálculo — fórmulas para calcular el promedio del salón en Excel",
            "Internet — qué es una URL, un dominio y cómo viaja un mensaje",
            "Redes sociales — cómo se cifra un mensaje de WhatsApp (idea general)",
            "Videojuegos sencillos — coordenadas X-Y para mover un personaje",
            "Inteligencia artificial cotidiana — recomendaciones de YouTube y Spotify",
            "Bases de datos escolares — tabla de estudiantes con nombre, edad y curso",
        ],
        "preparatoria": [
            "Primer programa en Python — calculadora de IMC en consola",
            "Algoritmo de ordenamiento burbuja — ordenar 10 números enteros paso a paso",
            "HTML/CSS — primera página web personal con encabezados y enlaces",
            "Estructuras de datos básicas — listas y diccionarios para gestionar inventario",
            "Lógica booleana — operadores AND, OR, NOT en un sistema de luces",
            "Bases de datos con SQL básico — SELECT de tabla de empleados con filtro",
            "Introducción a APIs — consumir clima desde OpenWeather con una request HTTP",
            "Arduino + sensor — encender LED cuando la temperatura supere 25 °C",
        ],
        "universitario": [
            "Motor de búsqueda Google — PageRank con grafos de 100 mil millones de páginas",
            "Base de datos distribuida Cassandra — consistencia eventual en 1000 nodos",
            "Algoritmo de recomendación de Netflix — filtrado colaborativo con 200 millones de usuarios",
            "Compilador LLVM — optimización de código intermedio (IR) para múltiples arquitecturas",
            "Red neuronal GPT — transformer con 175 mil millones de parámetros, 570 GB de texto",
            "Blockchain Ethereum — consenso Proof-of-Stake, 30 transacciones/segundo",
            "Sistema operativo Linux — scheduler CFS con O(log n) para millones de procesos",
            "Protocolo TCP/IP — control de congestión CUBIC en redes de 100 Gbps",
        ],
        "avanzado": [
            "Modelos de lenguaje grandes — entrenamiento distribuido en miles de GPUs H100",
            "Bases de datos vectoriales — búsqueda ANN con HNSW en embeddings de 1536 dim",
            "Verificación formal de software crítico — Coq/Isabelle en aviónica DO-178C",
            "Computación neuromórfica — chips Loihi 2 de Intel con neuronas espigantes",
            "Sistemas de consenso bizantino — HotStuff y BFT en blockchains de tercera generación",
            "Reinforcement Learning con feedback humano (RLHF) — alineación de LLMs",
            "Compiladores diferenciables — JAX/XLA para optimización end-to-end",
            "Privacidad diferencial — análisis de datos del censo con ε-DP garantizado",
        ],
    },
    "humanities": {
        "primaria": [
            "Fiestas tradicionales colombianas — Feria de las Flores en Medellín, Carnaval de Barranquilla",
            "Cuentos clásicos infantiles — Caperucita Roja, Pinocho y sus enseñanzas",
            "La historia del propio colegio — fundación, símbolos y personas importantes",
            "Mi familia — árbol genealógico de tres generaciones",
            "Símbolos patrios de Colombia — bandera, himno y escudo",
            "Países vecinos de Colombia — ubicación en un mapa sencillo",
            "Trabajos en mi barrio — tendero, profesor, médico, conductor",
            "Reglas de convivencia en el salón — respeto, turnos para hablar",
        ],
        "secundaria": [
            "Independencia de Colombia (1810) — el grito del 20 de julio y sus protagonistas",
            "Literatura juvenil colombiana — 'María' de Jorge Isaacs como retrato regional",
            "Geografía humana — distribución de la población por regiones de Colombia",
            "Mitos y leyendas colombianas — La Llorona, El Mohán, La Patasola",
            "Constitución de 1991 — derechos fundamentales en lenguaje claro",
            "Música popular — historia del vallenato y la cumbia como identidad cultural",
            "Conflicto armado en Colombia — versión introductoria con énfasis en víctimas y memoria",
            "Migración rural-urbana — crecimiento de Medellín en el siglo XX",
        ],
        "preparatoria": [
            "Filosofía introductoria — el mito de la caverna de Platón",
            "Historia universal — Revolución Francesa y derechos humanos",
            "Literatura latinoamericana — boom y realismo mágico (introducción)",
            "Economía básica — oferta y demanda en el mercado de Plaza Minorista",
            "Sociología — clases sociales y movilidad en Colombia",
            "Ética aplicada — dilemas de redes sociales y privacidad adolescente",
            "Geopolítica — recursos naturales de Colombia y comercio internacional",
            "Psicología del aprendizaje — memoria a corto y largo plazo en estudio",
        ],
        "universitario": [
            "Revolución Industrial en Manchester (1760-1840) — transición de taller a fábrica",
            "El contrato social de Rousseau — soberanía popular vs. monarquía absoluta",
            "Cien años de soledad de García Márquez — realismo mágico como narrativa latinoamericana",
            "Crisis económica de 2008 — hipotecas subprime y riesgo sistémico",
            "Neuropsicología del aprendizaje — plasticidad sináptica y memoria de largo plazo",
            "Conflicto armado colombiano — Acuerdos de La Habana 2016 y justicia transicional",
            "Ética de la inteligencia artificial — sesgo algorítmico y equidad en decisiones automatizadas",
            "Urbanización en Medellín — metrocable como modelo de movilidad sostenible e inclusión social",
        ],
        "avanzado": [
            "Filosofía analítica — debate Kripke vs. Lewis sobre semántica de mundos posibles",
            "Hermenéutica gadameriana — fusión de horizontes en interpretación de textos jurídicos",
            "Economía del comportamiento — Kahneman y Tversky aplicados a política pública",
            "Estudios de memoria histórica — Comisión de la Verdad en Colombia (informe 2022)",
            "Antropología decolonial — pensamiento de Aníbal Quijano sobre colonialidad del poder",
            "Teoría crítica de la tecnología — Yuk Hui y la cosmotécnica",
            "Historia ambiental — Antropoceno y huella humana en sistemas terrestres",
            "Lingüística computacional — sintaxis distribucional y modelos de transformers",
        ],
    },
}


def get_contexts_for(area: str, level_key: str, fallback_level: str = "universitario") -> list:
    """
    Devuelve la lista de contextos para (area, level_key), con fallback robusto.

    Args:
        area: clave de área (science/engineering/math/cs/humanities)
        level_key: clave de nivel (primaria/secundaria/preparatoria/universitario/avanzado)
        fallback_level: nivel a usar si la combinación pedida no existe
    Returns:
        lista de contextos (strings)
    """
    if area not in INDUSTRIAL_CONTEXTS:
        return []
    area_dict = INDUSTRIAL_CONTEXTS[area]
    if level_key in area_dict:
        return list(area_dict[level_key])
    return list(area_dict.get(fallback_level, []))

# ---------------------------------------------------------------------------
# Concepciones erróneas comunes (para distractores en selección múltiple)
# ---------------------------------------------------------------------------

COMMON_MISCONCEPTIONS = {
    "math": [
        "Creer que $\\sqrt{a+b} = \\sqrt{a} + \\sqrt{b}$",
        "Pensar que multiplicar por un negativo no cambia la desigualdad",
        "Confundir correlación con causalidad en estadística",
        "Asumir que $0/0 = 1$ o que $0^0 = 0$",
        "Creer que la probabilidad de un evento cambia por resultados previos (falacia del jugador)",
        "Pensar que derivar e integrar siempre se cancelan sin considerar constantes",
        "Confundir media, mediana y moda en distribuciones asimétricas",
    ],
    "science": [
        "Creer que los objetos más pesados caen más rápido en vacío",
        "Pensar que el calor y la temperatura son lo mismo",
        "Asumir que los electrones orbitan el núcleo como planetas alrededor del sol",
        "Creer que las reacciones endotérmicas no ocurren espontáneamente",
        "Pensar que la evolución tiene una dirección o propósito",
        "Confundir masa y peso en contextos fuera de la Tierra",
        "Creer que los ácidos siempre son peligrosos (vinagre, ácido cítrico son ácidos débiles)",
        "Pensar que la corriente eléctrica se 'gasta' al pasar por una resistencia",
    ],
    "engineering": [
        "Asumir flujo ideal (sin fricción) en cálculos de tuberías reales",
        "Ignorar las pérdidas por accesorios en sistemas de bombeo",
        "Confundir eficiencia termodinámica con eficiencia mecánica",
        "Asumir que un intercambiador más grande siempre es mejor (rendimientos decrecientes)",
        "Ignorar el factor de incrustación (fouling) en diseño de intercambiadores",
        "Creer que un factor de seguridad alto siempre es deseable (sobredimensionamiento)",
        "Confundir esfuerzo y deformación en análisis de materiales",
    ],
    "cs": [
        "Creer que O(n) siempre es más rápido que O(n log n) para cualquier n",
        "Pensar que más hilos de ejecución siempre mejoran el rendimiento",
        "Asumir que Python es 'lento' para todo (ignora numpy, JIT, etc.)",
        "Confundir autenticación con autorización",
        "Creer que HTTPS encripta la URL completa (el dominio es visible en DNS)",
        "Pensar que NoSQL es siempre más rápido que SQL",
        "Ignorar la ley de Amdahl al paralelizar código",
    ],
    "humanities": [
        "Creer que la Edad Media fue un periodo de oscurantismo total",
        "Confundir democracia directa con democracia representativa",
        "Pensar que el PIB mide el bienestar de una sociedad",
        "Asumir que la inflación siempre es negativa para la economía",
        "Confundir derechos naturales con derechos positivos",
        "Creer que la historia es una narrativa lineal de progreso",
    ],
}


def get_subject_knowledge(area: str, level_key: str = "universitario") -> str:
    """
    Retorna un bloque de texto con conocimiento curado para inyectar en el prompt.

    Args:
        area: clave del área ("math", "science", "engineering", "cs", "humanities", "default")
        level_key: nivel educativo (primaria/secundaria/preparatoria/universitario/avanzado).
            Filtra los contextos para que sean apropiados al nivel cognitivo del estudiante.
    Returns:
        texto formateado con constantes, datos y contextos relevantes
    """
    sections = []

    # Constantes físicas: solo desde preparatoria en adelante (para primaria/secundaria
    # son innecesarias y desvían al LLM hacia problemas demasiado técnicos).
    show_constants = (
        area in ("science", "engineering", "math")
        and level_key in ("preparatoria", "universitario", "avanzado")
    )
    if show_constants:
        constants_text = "CONSTANTES FÍSICAS DISPONIBLES (usa valores reales):\n"
        for name, data in PHYSICAL_CONSTANTS.items():
            constants_text += f"  - {name}: {data['símbolo']} = {data['valor']} {data['unidad']}\n"
        sections.append(constants_text)

    # Datos del mundo real: solo desde preparatoria en adelante.
    show_real_data = (
        area in ("science", "engineering")
        and level_key in ("preparatoria", "universitario", "avanzado")
    )
    if show_real_data:
        data_text = "DATOS DEL MUNDO REAL VERIFICADOS:\n"
        for category, props in REAL_WORLD_DATA.items():
            data_text += f"  [{category}]\n"
            for prop_name, prop_data in props.items():
                data_text += f"    - {prop_name}: {prop_data['valor']} {prop_data['unidad']}\n"
        sections.append(data_text)

    # Contextos reales filtrados por nivel
    if area in INDUSTRIAL_CONTEXTS:
        contexts = get_contexts_for(area, level_key)
        if contexts:
            ctx_text = "CONTEXTOS REALES PARA INSPIRAR PROBLEMAS (escoge los relevantes al tema):\n"
            for ctx in contexts:
                ctx_text += f"  • {ctx}\n"
            sections.append(ctx_text)
    elif area == "default":
        # Mezcla pequeña de contextos del mismo nivel
        ctx_text = "CONTEXTOS REALES DISPONIBLES:\n"
        for a in ["science", "engineering", "math"]:
            for ctx in get_contexts_for(a, level_key)[:2]:
                ctx_text += f"  • {ctx}\n"
        sections.append(ctx_text)

    # Concepciones erróneas: solo aportan valor desde secundaria en adelante.
    if area in COMMON_MISCONCEPTIONS and level_key != "primaria":
        misc_text = "CONCEPCIONES ERRÓNEAS COMUNES (úsalas como distractores en selección múltiple):\n"
        for misc in COMMON_MISCONCEPTIONS[area]:
            misc_text += f"  - {misc}\n"
        sections.append(misc_text)

    return "\n".join(sections) if sections else ""
