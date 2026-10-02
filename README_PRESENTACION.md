# Cómo presentar Entre Corazones

Esta guía es para explicar el proyecto con tus propias palabras en una conversación, una exposición o una demostración. Para los pasos de instalación, consulta el [README principal](README.md); para detalles de implementación, la [guía técnica](README_TECNICO.md).

## En una frase

> Entre Corazones es una aplicación web para jugar y conversar sobre relaciones con tests, lecturas simbólicas y funciones sociales, desde una interfaz adaptable a móviles y computadoras.

## Presentación breve

> Desarrollé Entre Corazones como una página de entretenimiento alrededor de los vínculos y las relaciones. Puedes calcular un match entre nombres, hacer tests, probar una tirada de tarot o una lectura zodiacal simbólica, y comparar personajes. También tiene funciones de comunidad y, si se configura una clave, una conversación opcional con inteligencia artificial. La diseñé para que sea fácil de explorar desde el teléfono o la computadora. Los resultados son recreativos: buscan entretener y abrir conversaciones, no predecir el futuro ni medir una relación de forma científica.

## Presentación un poco más técnica

> La aplicación está construida con Python y Flask en el servidor, y HTML, CSS y JavaScript en el navegador. Organicé el servidor en rutas, servicios y una capa de infraestructura para PostgreSQL. Los juegos que no dependen de IA se calculan localmente; las funciones generativas son opcionales y se conectan con la API de OpenAI. La aplicación puede funcionar sin configurar IA y varias páginas siguen disponibles sin base de datos. También tiene navegación entre secciones, recursos de accesibilidad y una PWA que puede guardar la interfaz para abrirla sin conexión.

## Demostración sugerida

1. Muestra la página de inicio y explica que los modos están organizados en secciones.
2. Abre **Match de nombres**, escribe dos nombres y genera un resultado.
3. Señala las sugerencias, las ideas para conversar y las opciones para compartir el resultado.
4. Enseña otro modo, como tarot o compatibilidad zodiacal, aclarando que la lectura es simbólica.
5. Muestra la sección de comunidad o el chat si esa función está configurada.
6. Si tienes tiempo, cambia el tema o ajusta una opción de accesibilidad.

Si la IA, PostgreSQL o las credenciales de despliegue no están configuradas en el entorno de demostración, presenta solo las funciones locales disponibles. No compartas claves ni tokens para hacer la demostración.

## Qué destacar

- **Modos variados:** un cálculo rápido, juegos de grupo y lecturas más elaboradas.
- **Uso flexible:** la interfaz se adapta a pantallas de móvil y escritorio.
- **IA opcional:** los juegos principales no dependen de una clave de IA.
- **Experiencia cuidada:** navegación por secciones, volver, compartir resultados y preferencias de accesibilidad.
- **Privacidad consciente:** el historial del navegador se guarda localmente; la base de datos se utiliza para funciones compartidas y datos agregados.
- **Transparencia:** se aclara que los porcentajes y las lecturas son recreativos.

## Preguntas que pueden hacerte

### ¿El porcentaje indica si una pareja es compatible de verdad?

No. Es un resultado lúdico y determinista para entretener. No es una evaluación científica ni predice cómo funcionará una relación.

### ¿La inteligencia artificial es necesaria?

No. Los modos locales siguen funcionando sin ella. Para usar el chat y las interpretaciones generativas, el servidor necesita una clave de OpenAI.

### ¿Guarda las conversaciones en una base de datos?

El historial de la interfaz se guarda en el almacenamiento local de ese navegador. Las acciones de IA envían el texto necesario a OpenAI para producir una respuesta; pedir `store=False` no implica que el texto nunca salga del servicio. PostgreSQL se usa para votos comunitarios, feedback y métricas agregadas, no para perfiles o historiales de chat.

### ¿Funciona sin internet?

El Service Worker puede mantener disponible la interfaz y los archivos estáticos guardados. La IA, las votaciones y las métricas necesitan conexión.

### ¿Cómo está publicada?

La aplicación tiene un punto de entrada WSGI para Gunicorn (`gunicorn app:app`) y puede desplegarse como un servicio web, por ejemplo en Render. Las credenciales y URLs se configuran en el entorno del servidor y no se incluyen en el código.

## Cierre sugerido

> La idea principal no es decirle a nadie qué va a pasar en su relación, sino ofrecer una experiencia entretenida para jugar, compartir resultados y empezar conversaciones.
