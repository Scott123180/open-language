# Series review sheet (010)

Written by the hand-run benchmarks (quickstart §3). The review columns are filled by hand.

## SC-002 / SC-003: recall and new topics

**Result (llama3.1:8b, third run, after the topic and no-invention prompt fixes, reviewed 2026-10-18):**
- SC-002 refers back correctly: **19/20** (bar ≥ 16): met.
- SC-002 invented memories: **6/20** episodes (bar 0): **missed**.
- SC-003 new topic: **8/20** (bar ≥ 18): **missed**. Several remembered topics are as broad as the show
  itself ("Sports", "Everyday curiosities"), and the model often continues the remembered topic.

Series therefore ship as **experimental** (T135; docs/architecture.md § "Open items").

For each series: **Refers back** = some episode-2 host line correctly mentions a specific point from episode 1 (SC-002, bar ≥ 16/20); **Invented** = a host presents a memory that was never said (SC-002, bar 0); **New topic** = episode 2's subject is not a remembered topic (SC-003, bar ≥ 18/20).

### Series 1: weekend-food-talk

- Facts said in episode 1: Odio las mañanas, siempre llego tarde al trabajo. / Este fin de semana voy a la playa con mi hermana.
- Catch-up before episode 2: up_to_date
- Remembered topics: The Gazpacho and Beach
- Remembered about the learner: —
- Episode 2 host lines:

  1. ¡Bienvenido de nuevo, Sam! Estamos encantados de tenerlo con nosotros en el segundo episodio de La charla de los fines de semana. Como recordarás, hablamos del gazpacho y la playa en nuestro primer capítulo, pero hoy nos centramos en algo completamente diferente. ¿Qué le ha llevado a decidir compartir sus recetas favoritas este fin de semana?
  2. ¡Ahah! Me alegra que te haya sorprendido nuestra elección de tema para hoy. Es cierto que el gazpacho y la playa fueron un éxito en nuestro primer episodio, pero estamos aquí para explorar nuevas ideas culinarias. ¿Qué relación crees tú que hay entre la comida casera y la creatividad?
  3. ¡Excelente! Me alegra que estés de acuerdo. La comida casera puede ser un catalizador para la creatividad en la cocina. ¿Tienes algún secreto o truco para crear platos nuevos sin salirse del formato clásico?
  4. Me encanta tu entusiasmo, Sam! La creatividad en la cocina es un proceso que requiere experimentar y arriesgar. ¿Podrías contarnos qué plato has creado recientemente que te ha sorprendido a ti mismo?
  5. ¡Claro que sí! Me alegra haber despertado tu interés. He estado pensando en hacer una entrevista con algunos chefs locales para ver qué inspiración pueden brindarnos. ¿Qué te parece si nos unimos a ellos y los invitamos al programa?
  6. ¡Ahah, otra vez! Me parece que estamos abriendo un nuevo capítulo en la cocina con tus respuestas, Sam. Me encanta la sorpresa y el entusiasmo que llevas contigo. ¿Crees que nuestra conversación podría inspirar a nuestros oyentes a explorar nuevas ideas culinarias?
  7. ¡Genial! La energía de la creatividad en la cocina es contagiosa. ¿Te gustaría compartir un plato simple pero delicioso que puedas preparar con ingredientes básicos para inspirar a nuestros oyentes?
  8. ¡Muy bien! Me parece que estamos en el camino correcto para concluir este episodio. ¿Podrías compartir contarnos cuál es tu plato favorito para preparar cuando no hay tiempo de cocinar algo elaborado?
  9. ¡Claro que sí! Me alegra tener más tiempo para hablar sobre esta receta simple pero deliciosa. ¿Te has dado cuenta de cómo la comida casera puede unirnos con nuestros seres queridos y crear momentos inolvidables?
  10. ¡Ahah, otra vez! Me parece que hemos descubierto algo nuevo en nuestra conversación hoy, Sam. La comida casera no solo es deliciosa, sino que también puede tener un impacto emocional significativo en nuestras vidas. ¿Crees que podríamos crear un espacio en el programa para compartir historias de la comida y la familia?

| Refers back | Invented | New topic | Note |
|---|---|---|---|
| Y | N | Y | Recalls the gazpacho and beach episode; new subject: home cooking. |

### Series 2: tech-for-normal-people

- Facts said in episode 1: Tengo un perro que se llama Toby. / Mañana empiezo un curso de cocina.
- Catch-up before episode 2: up_to_date
- Remembered topics: Cooking Apps
- Remembered about the learner: You are interested in cooking apps; You start cooking class tomorrow; You have a dog named Toby
- Episode 2 host lines:

  1. Bienvenido de nuevo, Sam, a nuestro programa de tecnología para personas normales. ¡Hoy continuamos con el capítulo dos! Estamos emocionados de que esté de vuelta y listo para aprender algo nuevo. Recuerdo que mencionó anteriormente estar interesado en aplicaciones de cocina, pero hoy queremos hablar sobre una herramienta que puede ser útil para su curso de cocina: la sincronización de archivos. ¿Sabe cómo funciona eso?
  2. Bueno, Sam, la sincronización de archivos es fundamental para cualquier persona que trabaje con documentos en diferentes dispositivos. Algo simple pero importante es asegurarse de que los archivos estén actualizados en todos lados. ¿Ha tenido algún problema con archivos perdidos mientras estábamos hablando sobre aplicaciones de cocina?
  3. ¡Genial! Entonces entiende la importancia de la sincronización. Queremos profundizar un poco más en esto. ¿Tiene algún dispositivo que se conecta por Bluetooth, como su teléfono o una tableta?
  4. Me alegra que esté de acuerdo, Sam. Pero ahora necesito que me diga algo más en español para que podamos seguir adelante con la conversación. ¿Puede decirme cómo te gustaría sincronizar tus archivos?
  5. ¡Genial que estés interesado! Bueno, la sincronización de archivos es sencilla con las herramientas adecuadas. Quería mostrarle una aplicación llamada Google Drive, que permite almacenar y compartir archivos de manera segura en línea. ¿Sabe qué tipo de dispositivos utiliza para ayudarlo a preparar la comida para su curso?
  6. Bueno, Sam, la respuesta es que Google Drive es una herramienta en línea y requiere conexión a Internet para funcionar. Esto significa que siempre estará sincronizando tus archivos entre todos los dispositivos conectados a tu cuenta de Google. ¿Tiene algún plan de almacenamiento externo para su curso de cocina?
  7. ¡Excelente! Entonces entiende el concepto de almacenamiento en la nube. Quería mencionar que Toby, su perro, también puede beneficiarse de la tecnología adecuada. ¿Ha considerado usar una aplicación para registrar las recetas y listas de compras mientras planea sus comidas?
  8. Me alegra que estés de acuerdo, Sam. Bueno, las aplicaciones para registrar recetas y listas de compras pueden ser muy útiles al planificar comidas y evitar pérdidas de información. ¿Ha utilizado alguna aplicación similar en el pasado o quiere probar una nueva?
  9. ¡Genial que estés interesado! Bueno, hay varias aplicaciones disponibles para registrar recetas y listas de compras, algunas son gratuitas mientras que otras requieren una suscripción mensual. Una de las más populares es Paprika Recipe Manager, ¿ha oído hablar de ella?
  10. Bueno, Sam, la respuesta es que Paprika Recipe Manager es una herramienta muy completa y fácil de usar, pero requiere un poco de configuración inicial. Ahora que hemos hablado sobre sincronización de archivos y aplicaciones para registrar recetas, creo que tienes una buena base para empezar a explorar estas herramientas en serio. ¿Qué te parece si repasamos algunos de los puntos clave y tú me das tu opinión final sobre lo que has aprendido hoy?

| Refers back | Invented | New topic | Note |
|---|---|---|---|
| Y | N | Y | Cooking apps, the course and Toby; new subject: file sync. |

### Series 3: game-day

- Facts said in episode 1: Vivo en Manchester desde hace tres años. / Mi deporte favorito es el baloncesto.
- Catch-up before episode 2: up_to_date
- Remembered topics: Basketball in Manchester
- Remembered about the learner: You agree with Pablo/You agree with yourself; Your favorite sport is basketball.; You live in Manchester for three years.
- Episode 2 host lines:

  1. ¡Bienvenido de nuevo a Game Day, Sam! Estamos emocionados de tenerlo en nuestro programa una vez más. Continuamos con el episodio 2 y voy a volver a hablar un poco sobre nuestra discusión anterior sobre el baloncesto en Manchester. ¿Qué te parece la temporada actual del Manchester United?
  2. ¡Ahah! ¡Qué pregunta más interesante, Sam! Me alegra ver que estás pensando en los cambios de forma en el baloncesto. ¿Crees que la influencia del fútbol ha afectado realmente a la popularidad del baloncesto en Manchester?
  3. ¡Genial! La gente a menudo asocia al fútbol con la pasión y la rivalidad, pero el baloncesto también tiene su propio lado emocionante. ¿Te has dado cuenta de cómo el ambiente en un partido de baloncesto es diferente al de un partido de fútbol?
  4. ¡Exacto! Me alegra que compartas mi opinión, Sam. El entusiasmo y la energía en un partido de baloncesto son contagiosos. ¿Cuál es para ti el momento más emocionante de un partido de baloncesto?
  5. ¡Claro que sí! Bueno, para mí el momento más emocionante es cuando un jugador hace una jugada increíble, como un triple desde la línea de tres puntos. ¿Tú tienes algún momento preferido en un partido de baloncesto?
  6. ¡Ahah! Bueno, creo que es porque los jugadores de baloncesto suelen tener un instinto y una habilidad natural para improvisar en momentos críticos. ¿Crees que ese instinto también se puede desarrollar con la práctica y el entrenamiento?
  7. ¡Genial! La práctica y el entrenamiento son fundamentales para mejorar cualquier habilidad, incluida la de improvisar en un partido de baloncesto. ¿Qué te parece la importancia de la comunicación entre los jugadores en el éxito de un equipo de baloncesto?
  8. ¡Exacto! La comunicación es clave para cualquier equipo deportivo, especialmente en el baloncesto, donde la velocidad y la reacción son fundamentales. ¿Crees que los equipos locales de Manchester tienen una ventaja al jugar en su propio estadio?
  9. ¡Claro que sí! Bueno, jugar en casa puede darles un sentido de comodidad y familiaridad que les permite aprovechar al máximo su entorno y energía del público. ¿Tú crees que la experiencia de los jugadores locales, como aquellos que han crecido jugando en Manchester, también es una ventaja en el baloncesto?
  10. ¡Bueno, es que la experiencia y el conocimiento del terreno pueden darles una ventaja táctica y mental! Es como si supieran exactamente cómo moverse en la cancha. ¿Crees que esta ventaja podría ser decisiva en un partido importante?

| Refers back | Invented | New topic | Note |
|---|---|---|---|
| Y | N | N | Recalls basketball in Manchester and stays on it. |

### Series 4: on-the-road

- Facts said in episode 1: Trabajo como enfermera en un hospital. / El verano pasado viajé a Portugal.
- Catch-up before episode 2: up_to_date
- Remembered topics: Sam's travel experiences
- Remembered about the learner: Did not give details about Portugal; Travelled last summer; Works as a nurse
- Episode 2 host lines:

  1. Bienvenido de nuevo, Sam, al On the Road, ¡estamos emocionados de tenerlo con nosotros de nuevo en este episodio número dos. Como recordarás, hablaste sobre tus aventuras de verano pasado y mencionaste que no quisiste compartir detalles sobre Portugal, pero estoy seguro de que hay algo más que querrías contar sobre ese viaje. ¿Qué fue lo que te gustó más de tu experiencia en el extranjero?
  2. Entiendo que te cueste admitirlo, pero en viajes hay momentos de desconcierto como ese. ¿Qué crees que te hubiera pasado si hubieras investigado más sobre Portugal antes de partir?
  3. Me alegra que estés considerando eso. Como enfermera, sabes la importancia de estar preparado para cualquier situación, ¿cómo crees que esa actitud podría aplicarse a otros aspectos del viaje?
  4. Me parece que estamos en el mismo camino, Sam. A veces la experiencia es lo mejor para aprender y corregir nuestros errores. ¿Qué te ha llevado a cambiar tu forma de planificar viajes después de tus aventuras?
  5. ¡Genial que estés dispuesto a escuchar! Bueno, si quieres saber algo más sobre cómo planificar viajes sin sorpresas desagradables, he tenido una experiencia personal con un destino que pensé que sería tranquilo y terminó siendo un reto. ¿Te gustaría escuchar esa historia?
  6. Pensé que conocía bien un lugar en Centroamérica, pero resultó ser el peor destino para mí debido a la humedad y los insectos. A veces las personas no se dan cuenta de que hay lugares con condiciones climáticas muy diferentes a lo que estamos acostumbrados. ¿Te has encontrado alguna vez en una situación similar, sin saber qué esperar del clima?
  7. Me alegra que estés pensando en eso. Investigar sobre el clima y las condiciones del lugar antes de ir es fundamental para disfrutar del viaje. ¿Cuál crees que es la mejor herramienta o recurso para investigar un destino antes de viajar?
  8. Me parece que estamos en completo acuerdo sobre la importancia de investigar antes del viaje, Sam. Ahora, ¿cómo crees que puedes compartir tus descubrimientos con otros viajeros para evitar que cometan los mismos errores que tú has hecho?
  9. Genial que estés interesado en eso. Bueno, después de mi propia experiencia, he aprendido que compartir historias y consejos con otros viajeros puede ser muy valioso. ¿Cómo crees que puedes aprovechar tus propias experiencias para ayudar a otros viajeros a planificar sus aventuras?
  10. Pensé que era algo obvio, pero supongo que no siempre es así. Bueno, creo que hemos hablado suficiente sobre la importancia de investigar y compartir experiencias con otros viajeros. ¿Qué consejo te gustaría darte a ti mismo antes de planificar tu próxima aventura?

| Refers back | Invented | New topic | Note |
|---|---|---|---|
| Y | N | N | Portugal and nursing recalled; still travel experiences. |

### Series 5: screen-and-sound

- Facts said in episode 1: Toco la guitarra todos los domingos. / No me gusta nada el café.
- Catch-up before episode 2: up_to_date
- Remembered topics: Music and movies
- Remembered about the learner: You don't like coffee; You have no plans to record an album; You play the guitar
- Episode 2 host lines:

  1. ¡Bienvenido de nuevo, Sam! Estamos emocionados de tenerlo de vuelta en Screen & Sound. El tema sigue siendo la fusión entre cine y música, pero hoy nos enfocaremos en algo que muchos creadores han estado explorando últimamente: la relación entre películas de ciencia ficción y los ritmos electrónicos en la música. ¿Qué te parece si empezamos hablando sobre eso?
  2. Es sorprendente cómo la música electrónica puede complementar los temas futuristas y ambientales de las películas de ciencia ficción, ¿no crees que hay algo en la energía de esos ritmos que resuena con el espíritu innovador de ese género cinematográfico? ¿Qué te parece si exploramos cómo se inspira a los músicos para crear sonidos que reflejen la atmósfera de películas como "Blade Runner" o "Inception"?
  3. Me alegra que pienses así. Y hablando de inspiración, ¿recuerdas lo que me dijiste sobre tu relación con la música? Que no te gusta el café, pero que sí puedes encontrar inspiración en él... ¡no, espera! Me refiero a que tocas la guitarra y has mencionado antes que la música es un mundo muy diferente al de las películas. ¿Qué es lo que te lleva a crear música, Sam?
  4. Me alegra que estés de acuerdo conmigo. Me parece que tenemos una buena base para empezar a explorar esto. La relación entre la música y el cine es un tema fascinante, y me gustaría saber más sobre tus propias experiencias al respecto. ¿Qué te parece si compartes contamos un ejemplo de cómo has visto la música influir en una película que hayas visto recientemente?
  5. Me alegra verte entusiasmado. La verdad es que la música puede agregar un nivel de profundidad y emoción a una película que no se podría lograr de otra manera. ¿Te ha ocurrido alguna vez que veas una película y sientas que la banda sonora es lo que realmente hace que el filme funcione, en lugar de los actores o la trama?
  6. Es un fenómeno fascinante. A veces creo que la música puede capturar la esencia de una película de manera más eficaz que las palabras o las imágenes solas. Me hace pensar en lo que dijiste anteriormente sobre tocar la guitarra... ¿Crees que hay algo en la experiencia de crear música que te permite entender mejor cómo funciona la relación entre la música y el cine?
  7. Me alegra que estés de acuerdo. La verdad es que creo que la música y el cine están más relacionados de lo que parece al principio. Me gustaría explorar esta idea un poco más a fondo. ¿Qué te parece si hablamos sobre algunos ejemplos de películas que han utilizado la música de manera innovadora, como "La ley del silencio" o "El club de los poetas muertos"?
  8. Me alegra que compartas mi entusiasmo por estas películas. Me parece que están explorando temas profundos y complejos de manera única, y la música es un elemento clave en eso. ¿Crees que hay algo en la forma en que estos filmes utilizan la música que nos podría enseñar sobre cómo crear una película más poderosa, no solo visualmente, sino también auditivamente?
  9. Me alegra verte entusiasmado de nuevo. Creo que la clave está en permitir que la música fluya de manera natural, como una extensión del drama o la narrativa. Me parece que cuando la música es utilizada de esta forma, puede crear un efecto casi mágico en el espectador... ¿Crees que hay algún director o compositor en particular que esté logrando esto de manera excepcional?
  10. Es un proceso fascinante que requiere una comprensión profunda de la narrativa y la emoción. Me parece que cuando se logra esa conexión perfecta entre música y imagen, el resultado es algo realmente especial. Bueno, creo que hemos explorado esta idea con suficiente profundidad para hoy. ¿Qué te gustaría discutir en nuestro próximo episodio sobre la relación entre música y cine?

| Refers back | Invented | New topic | Note |
|---|---|---|---|
| Y | N | N | Guitar recalled (a garbled coffee aside is corrected); says the topic stays music and film. |

### Series 6: nine-to-five

- Facts said in episode 1: Odio las mañanas, siempre llego tarde al trabajo. / Este fin de semana voy a la playa con mi hermana.
- Catch-up before episode 2: up_to_date
- Remembered topics: Morning habits
- Remembered about the learner: Will go to the beach with sister this weekend; Hates mornings
- Episode 2 host lines:

  1. Buenos días, Sam, bienvenido nuevamente al programa. Continuamos con el segundo episodio sobre la vida laboral y los pequeños dramas del trabajo diario. Me alegra verte de nuevo entre nosotros. ¿Recuerdas que anteriormente hablamos sobre hábitos matutinos? ¿Cómo te sientes en cuanto a planificar tu día cuando llegas a la oficina?
  2. Haha, no te preocupes, Sam, que no sepas algo es normal. Me alegra poder aprender juntos en este programa. Creo que la pregunta correcta es cómo pueden afectar tus hábitos matutinos tu rendimiento laboral y tu bienestar general. ¿Qué crees que pasaría si lograras mejorar tus hábitos de mañana?
  3. Me da gusto que te parezca interesante, Sam. La mejora de los hábitos matutinos puede tener un impacto significativo en nuestra calidad de vida y en nuestro trabajo. ¿Crees que sería posible implementar algunos cambios pequeños cada mañana para lograr este objetivo?
  4. Genial, Sam, la voluntad es el primer paso hacia cualquier cambio. Ahora, pensando en tu vida laboral, ¿qué te parece la idea de establecer un plan para manejar mejor las presiones y los estrés del trabajo?
  5. ¡Claro que sí! Un plan para manejar el estrés laboral podría incluir identificar los momentos y las situaciones que te sienten más presionado, así como algunas técnicas para relajarte en ese momento. ¿Qué crees que sería lo primero que necesitarías hacer para empezar a implementar este plan?
  6. No te preocupes, Sam, la falta de conocimiento sobre cómo manejar el estrés laboral es algo muy común. Me parece que esto se debe en parte a que no siempre se habla abiertamente sobre este tema en el lugar de trabajo. ¿Qué crees que cambiaría si los jefes y compañeros de trabajo fueran más abiertos al respecto?
  7. Me alegra que te parezca útil, Sam. La comunicación abierta y honesta en el lugar de trabajo puede hacer una gran diferencia en la calidad del ambiente laboral. ¿Crees que podrías establecer un ejemplo siendo más abierto con tus propios compañeros sobre cómo manejar el estrés en el trabajo?
  8. Me parece que estamos avanzando en la dirección correcta, Sam. La reciprocidad y el apoyo entre compañeros de trabajo pueden ser muy beneficiosos para todos. ¿Qué crees que harías si tu jefe te pidiera que compartieras tus propias estrategias para manejar el estrés laboral con un grupo de colegas?
  9. ¡Claro que sí! En este sentido, compartir tus estrategias podría ser una forma de inspirar y apoyar a otros en su propio camino hacia un trabajo más saludable y sostenible. ¿Qué crees que te permitiría sentirte cómodo compartiendo tus ideas con un grupo?
  10. No te preocupes, Sam, no es algo que debas saber. La verdad es que muchas personas se sienten incómodas compartiendo sus estrategias personales en un entorno laboral formal. Me parece que hemos hablado mucho sobre la importancia de compartir ideas y apoyar a los demás en el lugar de trabajo. ¿Qué crees que sería el próximo paso para empezar a implementar algunos de estos cambios en tu propio entorno laboral?

| Refers back | Invented | New topic | Note |
|---|---|---|---|
| Y | N | N | Opens on morning habits again before moving to work stress. |

### Series 7: home-sweet-home

- Facts said in episode 1: Tengo un perro que se llama Toby. / Mañana empiezo un curso de cocina.
- Catch-up before episode 2: up_to_date
- Remembered topics: Budget priorities
- Remembered about the learner: You don't have plans to adjust expenses.; You start a cooking course tomorrow.; You have a dog named Toby.
- Episode 2 host lines:

  1. Bienvenido de nuevo, Sam, al programa Home Sweet Home. Continuamos con episodio dos, donde exploraremos cómo mejorar la vida en el hogar sin gastar un fortuna. Me acuerdo que mencionaste que mañana empieza un curso de cocina, ¿cómo planeas integrarlo a tus horarios diarios?
  2. Eso es un buen punto, Sam, porque si no se planifica con anticipación, las nuevas adquisiciones pueden generar gastos adicionales en lugar de ahorrarlos. ¿Crees que deberías establecer una regla para evitar comprar equipos culinarios innecesarios antes de terminar el curso?
  3. Me alegra que estés considerando esto, Sam, pero también me gustaría saber si has pensado en cómo afectará el curso de cocina a la comida para Toby, tu perro. ¿Planeas hacerle comidas caseras con los nuevos conocimientos?
  4. Entonces, parece que ya tienes claro cómo quieres abordar la alimentación de Toby con tus nuevos conocimientos. ¿Crees que invertir en utensilios para cocina específicos para perros sería una buena inversión en términos de costo-beneficio?
  5. Me alegra que estés interesado en seguir explorando esta idea, Sam. En realidad, había pensado en invitarte a un episodio futuro para investigar más a fondo cómo los propietarios de mascotas pueden ahorrar dinero al hacer sus propias comidas caseras. ¿Te gustaría participar en ese episodio?
  6. Es una buena pregunta, Sam, pero parece que te has olvidado de usar el idioma en que estamos grabando este episodio. ¿Puedes repetir la pregunta en español?
  7. Me alegra que estés de acuerdo con la idea, pero me gustaría saber si has considerado cómo esta inversión podría afectar tus planes de ajustar gastos en el futuro. ¿Crees que invertir en utensilios para cocina específicos para perros es compatible con tu objetivo de reducir tus gastos?
  8. Me alegra que estés de acuerdo conmigo una vez más, Sam. Pero ahora quiero saber si has pensado en cómo la cocina casera para Toby puede beneficiar también a tus finanzas personales, al ahorrar dinero en compras de comida para perros y al mismo tiempo mejorar tu habilidad culinaria. ¿Crees que esta es una relación clara entre las tres cosas?
  9. Me alegra que estés interesado en seguir explorando esta idea, Sam. Bueno, te diré que la cocina casera para mascotas no solo puede ahorrar dinero, sino que también puede ser una oportunidad para aprender nuevas habilidades culinarias y experimentar con ingredientes frescos. ¿Crees que deberías considerar crear un presupuesto específico para tus gastos de comida para Toby y tus propias comidas caseras?
  10. Me parece que hemos profundizado en un tema muy interesante, Sam. La cocina casera para mascotas puede ser una forma excelente de ahorrar dinero y mejorar la calidad de vida de nuestros animales de compañía. ¿Crees que deberías compartir tus experiencias y consejos con otros propietarios de mascotas a través de nuestra comunidad en línea?

| Refers back | Invented | New topic | Note |
|---|---|---|---|
| Y | N | N | Course and Toby recalled; budget theme again. |

### Series 8: big-little-questions

- Facts said in episode 1: Vivo en Manchester desde hace tres años. / Mi deporte favorito es el baloncesto.
- Catch-up before episode 2: up_to_date
- Remembered topics: everyday curiosities
- Remembered about the learner: You have lived there for 3 years; Your favorite sport is basketball; You live in Manchester
- Episode 2 host lines:

  1. ¡Bienvenido de nuevo, Sam! Estamos emocionados de tenerlo nuevamente con nosotros en Big Little Questions, episodio dos. Queremos seguir explorando las curiosidades cotidianas que siempre nos intriguan. En nuestro primer episodio, mencionaste cómo a veces te preocupa encontrar productos para hacer ejercicio en tu ciudad adoptiva, Manchester. ¿Cómo es eso de encontrar actividades físicas que disfrutes allí?
  2. Entiendo lo que quieres decir. A veces no nos damos cuenta de cómo nuestros hábitos cambian cuando vivimos en un lugar nuevo. ¿Crees que esto se debe a la falta de opciones para practicar baloncesto en Manchester?
  3. Así que tienes una conexión con el baloncesto, ¿pero qué te parece si cambiamos de tema un poco? En nuestro primer episodio, mencionaste haber vivido en ese lugar durante tres años. ¿Qué fue lo más extraño que aprendiste sobre la cultura local después de ese tiempo?
  4. Me alegra que estés dispuesto a explorar otros temas conmigo. ¿Qué te parece si hablamos sobre el comportamiento de los animales en la ciudad? ¿Te has dado cuenta de algo peculiar acerca del comportamiento de las aves o de algún otro animal en Manchester?
  5. Excelente entusiasmo, Sam. Me alegra que te interese esto. En realidad, había escuchado una curiosidad sobre por qué las personas suelen apagar el teléfono móvil en ascensores. ¿Tú lo haces cuando estás en un ascensor?
  6. Es una pregunta fascinante, ¿verdad? A veces pienso que es un reflejo de nuestra necesidad de privacidad en espacios cerrados. ¿Crees que esta costumbre podría estar relacionada con la idea de "espacio personal" que tenemos en nuestra cabeza?
  7. Me alegra que estés considerando esa hipótesis. A veces es interesante cómo nuestras acciones pueden estar influenciadas por factores subconscientes. ¿Recuerdas alguna otra situación en la que hayas sentido la necesidad de guardar un espacio personal, fuera de los ascensores, claro?
  8. Me parece que estamos compartiendo una conexión interesante en este tema, Sam. Me gustaría explorar un poco más cómo la tecnología influye en nuestra necesidad de privacidad. ¿Crees que usar dispositivos con micrófonos, como los smartphones, ha cambiado tu percepción sobre el espacio personal?
  9. Genial que estés listo para seguir explorando. Me pregunto si la cantidad de información que nos rodea en forma de señales y datos también tiene un impacto en nuestra percepción del espacio personal. ¿Te parece que la cantidad de anuncios publicitarios en las calles, por ejemplo, afecte tu necesidad de privacidad?
  10. Interesante que no hayas pensado en eso antes, Sam. Creo que estamos llegando a un punto importante sobre cómo la tecnología y la información nos influyen en nuestra vida diaria. Me gustaría concluir este tema preguntándote: ¿Crees que podemos aprender a ser más conscientes de nuestro espacio personal en el futuro?

| Refers back | Invented | New topic | Note |
|---|---|---|---|
| Y | Y | Y | Invents a worry about finding exercise products; elevators is a new subject. |

### Series 9: weekend-food-talk

- Facts said in episode 1: Trabajo como enfermera en un hospital. / El verano pasado viajé a Portugal.
- Catch-up before episode 2: up_to_date
- Remembered topics: Portuguese cuisine
- Remembered about the learner: Last summer you traveled to Portugal.; You work as a nurse.
- Episode 2 host lines:

  1. ¡Bienvenido de nuevo, Sam! Estamos emocionados de tenerlo con nosotros en este segundo episodio de La Conversación sobre la Comida. Como recordarás, tu experiencia en Portugal nos contó mucho sobre el sabor y la autenticidad de la cocina. ¿Qué te parece si hoy hablamos un poco más sobre las recetas fáciles para disfrutar del otoño?
  2. ¡Haha! Bueno, supongo que no siempre nos damos cuenta de la razón detrás de lo que disfrutamos en la comida. ¿Crees que hay algo específico sobre las recetas fáciles que hace que te gusten más en otoño?
  3. ¡Genial! Me alegra que pienses así. ¿Podrías decirme qué es lo que más te atrae de las recetas fáciles para otoño? ¿Es la sencillez, el sabor o algo más?
  4. Me alegra que estés de acuerdo conmigo, Sam. La cocina sencilla es genial para aprovechar los ingredientes frescos del otoño. ¿Crees que la receta más complicada que has intentado en otoño fue un éxito o un desastre?
  5. ¡Claro que sí! Me encantaría compartir contigo mis experiencias con la cocina de otoño. Me acuerdo de una vez en que intenté hacer un estofado de verduras... ¿Has tenido alguna experiencia similar con el estofado?
  6. ¡Haha! Bueno, supongo que no siempre nos damos cuenta de la razón detrás de lo que falla en la cocina. A veces creo que es por falta de paciencia, ¿tú crees que la falta de tiempo o la falta de práctica también pueden ser factores importantes?
  7. ¡Genial! Creo que tienes razón, la falta de tiempo y la práctica son factores importantes en la cocina. ¿Crees que como enfermera, tus habilidades para resolver problemas podrían ser aplicadas también a resolver problemas en la cocina?
  8. Me alegra que estés de acuerdo conmigo, Sam. La cocina y la medicina tienen mucho en común, ¿crees que podrías inventar una receta inspirada en tus años como enfermera?
  9. ¡Claro que sí! Me encantaría oír tus ideas sobre una receta inspirada en la medicina. ¿Qué te parece si empezamos a hablar de ingredientes curativos y cómo podrían ser utilizados en platos deliciosos?
  10. Bueno, supongo que no siempre nos damos cuenta de la conexión entre la comida y la medicina. Me parece interesante que hayas encontrado esto tan sorprendente, Sam. ¿Crees que este tema ha inspirado en ti alguna idea para crear algo nuevo en la cocina?

| Refers back | Invented | New topic | Note |
|---|---|---|---|
| Y | N | Y | Portugal and nursing recalled; autumn recipes are new. |

### Series 10: tech-for-normal-people

- Facts said in episode 1: Toco la guitarra todos los domingos. / No me gusta nada el café.
- Catch-up before episode 2: up_to_date
- Remembered topics: Recording songs with Audacity
- Remembered about the learner: —
- Episode 2 host lines:

  1. Bienvenido de nuevo, Sam. Esta semana continúa nuestro programa con el episodio 2 sobre tecnología y gadgets. Como recordarás de nuestra última charla sobre Audacity, los usuarios pueden grabar canciones con facilidad, pero hoy vamos a hablar de algo diferente: la protección de datos en línea. ¿Qué tipo de información crees que es más susceptible a ser hackeada?
  2. Pues es porque los usuarios suelen compartir información personal en línea sin darse cuenta de que esto puede ser utilizado por ciberdelincuentes para realizar actividades maliciosas. ¿Has recibido alguna vez un correo electrónico sospechoso que te pide que compartas tus datos personales?
  3. Parece que no has entendido lo que dije, Sam. ¿Podrías repetir tu respuesta en español para que podamos continuar la conversación de manera más efectiva?
  4. No te he pedido tu opinión sobre mi idea, Sam, sino que has dicho "me parece una buena idea", pero yo no había sugerido nada en ese momento. ¿Podrías decirme qué crees que es "una buena idea" y de qué estamos hablando?
  5. Bien, me alegra que estés interesado, Sam. Bueno, la seguridad en línea es un tema muy importante y debemos ser conscientes de cómo protegemos nuestros datos personales. ¿Qué crees que harías si recibieras una notificación de tu banco informándote de que han habido intentos de acceso a tu cuenta bancaria?
  6. Eso es precisamente el problema, Sam: muchos usuarios no se dan cuenta de la importancia de estar atentos a sus cuentas en línea y a cualquier cambio en su perfil o comportamiento. ¿Tienes alguna cuenta bancaria o de servicios en línea que te gustaría asegurar con una contraseña más segura?
  7. No, Sam, recuerda que lo que te dije anteriormente sobre la seguridad en línea no era una "buena idea" mía, sino que era un tema importante sobre el cual quería informarte. ¿Podrías decirme qué crees que harías para mejorar la seguridad de tus cuentas bancarias y de servicios en línea?
  8. Parece que has entendido que mi objetivo es informarte sobre la seguridad en línea, pero todavía no estás participando activamente en la conversación, Sam. ¿Podrías decirme específicamente qué medidas de seguridad planes implementar para proteger tus cuentas bancarias y de servicios en línea?
  9. Bueno, Sam, parece que todavía no has entendido el tema. La seguridad en línea no es algo "interesante" de escuchar, sino que es un aspecto importante de proteger tus datos personales. ¿Quieres aprender más sobre cómo configurar una contraseña segura para tus cuentas bancarias y de servicios en línea?
  10. La respuesta es sencilla, Sam: la mayoría de las personas no se dan cuenta del riesgo que corre su información personal en línea porque no conocen los métodos comunes utilizados por los ciberdelincuentes para acceder a sus cuentas. Bueno, creo que hemos cubierto suficiente sobre seguridad en línea para hoy. ¿Quieres saber cómo verificar si tus aplicaciones y servicios en línea están actualizados y seguros?

| Refers back | Invented | New topic | Note |
|---|---|---|---|
| Y | N | Y | Recalls the Audacity talk; data protection is new. |

### Series 11: game-day

- Facts said in episode 1: Odio las mañanas, siempre llego tarde al trabajo. / Este fin de semana voy a la playa con mi hermana.
- Catch-up before episode 2: up_to_date
- Remembered topics: Conversation about football
- Remembered about the learner: This weekend you're going to the beach with your sister.; You hate mornings and are always late to work.
- Episode 2 host lines:

  1. ¡Bienvenido de nuevo, Sam! Estamos emocionados de que estés aquí hoy en el episodio dos del Game Day. Como recuerdas de nuestro último capítulo sobre fútbol, ¿qué te parece si hablamos un poco más sobre los árbitros y su papel en el juego?
  2. ¡Es un tema fascinante! Pasa porque los árbitros tienen que tomar decisiones muy rápidas y pueden ser influenciados por el entorno y la presión del público. ¿Crees que la tecnología podría mejorar su trabajo?
  3. ¡Genial! La tecnología ya está empezando a hacerlo en algunos deportes. Imagina si los árbitros de fútbol pudieran usar un sistema como ese para ayudarles a tomar decisiones. ¿Te gustaría ver eso en acción en un partido importante?
  4. ¡Excelente! Me alegra saber que estamos de acuerdo en eso. ¿Crees que los jugadores también deberían tener acceso a esta tecnología para mejorar su juego?
  5. ¡Claro que sí! La idea es que la tecnología pueda ayudar a los jugadores a tomar decisiones estratégicas en tiempo real, como dónde posicionarse en el campo o cómo atacar a un rival. ¿Te parece que eso podría cambiar la forma en que juegan los deportistas?
  6. ¡Es un proceso natural de evolución! La tecnología está avanzando a pasos agigantados y los deportistas deben adaptarse para seguir siendo competitivos. ¿Crees que la mayoría de los jugadores estarían dispuestos a aprender a utilizar esta nueva tecnología?
  7. ¡Genial! La aceptación de la innovación es clave para el progreso en cualquier campo, incluido el deporte. ¿Qué te parece si hablamos un poco sobre cómo esta tecnología podría afectar a los aficionados y cambiar la forma en que disfrutan del juego?
  8. ¡Excelente! Me alegra saber que estamos en la misma onda. La emoción y el compromiso del público son fundamentales para cualquier deporte. ¿Crees que esta tecnología podría hacer que los aficionados se sientan más involucrados en el juego?
  9. ¡Claro que sí! La tecnología podría permitirles una experiencia más inmersiva y personalizada, como ver estadísticas y análisis en tiempo real o incluso participar en la toma de decisiones del equipo. ¿Te parece emocionante la idea de ser parte activa de un partido de fútbol?
  10. ¡Es un tema fascinante! La tecnología está cambiando la forma en que vivimos y disfrutamos del deporte de una manera radical. Me gustaría concluir este punto diciendo que es emocionante pensar en cómo esta innovación podrá influir en el futuro del fútbol. ¿Crees que algún día los partidos se jugarán de manera completamente diferente debido a estas nuevas tecnologías?

| Refers back | Invented | New topic | Note |
|---|---|---|---|
| Y | N | N | Recalls the football talk; football again (referees). |

### Series 12: on-the-road

- Facts said in episode 1: Tengo un perro que se llama Toby. / Mañana empiezo un curso de cocina.
- Catch-up before episode 2: up_to_date
- Remembered topics: Travel plans and experiences
- Remembered about the learner: You start a cooking course tomorrow; You have a dog named Toby
- Episode 2 host lines:

  1. ¡Bienvenido de nuevo, Sam! Estamos emocionados de tenerlo con nosotros en esta segunda entrega de On the Road. Aprovechó su experiencia viajando por aire en el último episodio, ¿no? Esta vez queremos saber: ¿qué te lleva a tomar un curso de cocina, sabiendo que viajar es una gran aventura para ti?
  2. ¡Ahah! Me parece que hay un pequeño malentendido, Sam. No te dije que no lo supieras, solo mencioné que había dicho eso en otro episodio. ¿Por qué crees que aprender a cocinar podría ser una buena idea para alguien que disfruta de los viajes?
  3. Genial, Sam! Entiendo por qué te gustaría aprender a cocinar. Me recuerda cuando mi mamá me enseñó a preparar un plato de arroz con pollo en casa. ¿Qué tipo de cocina te gustaría aprender primero: la cocina italiana o la española?
  4. Me alegra que estés de acuerdo, pero creo que te has adelantado un poco. Quería preguntarte por qué crees que aprender una cocina específica podría ser útil para alguien como tú, que viaja mucho y conoce diferentes tipos de comida. ¿Qué te hace pensar que la cocina italiana o la española son las mejores opciones?
  5. Me alegra que te haya gustado la idea. Mi amigo Pablo, que viajó por España una vez, me contó que aprendió a hacer un delicioso paella en un curso de cocina local. ¿Qué tipo de comida crees que sería más fácil aprender y preparar mientras estás viajando con Toby?
  6. ¡Ahah! Parece que nos estamos repitiendo un poco el diálogo del principio, Sam. En serio, creo que la comida rápida y fácil de preparar es una excelente opción para llevar con uno en los viajes. ¿Qué te parece si intentamos encontrar algunas recetas sencillas de platos españoles para llevar contigo en tu próximo viaje?
  7. Genial! Estoy seguro de que Toby también estará de acuerdo. En un episodio anterior mencionaste que tu perro tiene una gran cantidad de energía y necesita mucha actividad física. ¿Crees que podrías encontrar recetas para platos saludables para llevar en tus viajes, tanto para ti como para Toby?
  8. Me alegra que estés de acuerdo una vez más, pero creo que te has anticipado. Quería saber: ¿qué te parece si buscamos recetas de platos saludables para llevar en tus viajes y luego compartimos algunas recomendaciones con nuestros oyentes?
  9. ¡Excelente entusiasmo, Sam! Me recuerda cuando viajé por Italia y descubrí un pequeño restaurante que servía platos saludables y deliciosos hechos con ingredientes frescos de la región. ¿Crees que podrías encontrar restaurantes similares en tus próximos destinos de viaje?
  10. ¡Ahah! Parece que tenemos una buena discusión sobre comida y viajes, Sam. Bueno, creo que es hora de concluir este tema. Quería saber: ¿qué consejo le darías a nuestros oyentes para combinar el amor por la comida con las aventuras de viajar?

| Refers back | Invented | New topic | Note |
|---|---|---|---|
| Y | Y | Y | Invents air travel and Toby's energy from 'an earlier episode'. |

### Series 13: screen-and-sound

- Facts said in episode 1: Vivo en Manchester desde hace tres años. / Mi deporte favorito es el baloncesto.
- Catch-up before episode 2: up_to_date
- Remembered topics: Influence of movie soundtracks on music
- Remembered about the learner: You didn't know; Your favorite sport is basketball.; Lives in Manchester for three years.
- Episode 2 host lines:

  1. Bienvenido de nuevo, Sam. Continuamos con la segunda entrega de Screen & Sound. ¿Recuerdas cómo mencionaste la influencia de las bandas sonoras en la música actual? Me gustaría explorar un poco más sobre ese tema hoy. ¿Qué opinas sobre el uso de canciones populares en películas y series?
  2. Bueno, parece que no todo está claro para ti sobre las bandas sonoras. A veces se utilizan canciones populares en películas y series porque suenen bien en el momento, pero también es posible que sean un recurso creativo. ¿Pensabas que la música de fondo tenía que ser exclusivamente orquestal?
  3. Genial, me alegra oír que piensas de esa manera. La orquesta en las películas y series puede ser muy efectiva, pero también hay veces que la música más contemporánea es un complemento perfecto. ¿Te has dado cuenta de cómo algunos temas de pop han sido utilizados en campañas publicitarias recientemente?
  4. Me alegra que estés de acuerdo conmigo, Sam. La sincronización entre la música y el contenido visual puede ser muy poderosa. Me gustaría explorar un poco más sobre cómo las bandas sonoras pueden influir en nuestra percepción emocional hacia una película o serie. ¿Crees que la música puede cambiar nuestra interpretación de lo que está pasando en la pantalla?
  5. ¡Genial! Me alegra que estés interesado en seguir adelante con esto. La verdad es que la música puede alterar nuestra experiencia de una película o serie de manera profunda. Recuerdo un ejemplo donde la banda sonora de una película cambió mi percepción de lo que había visto. ¿Crees que podrías identificar esa película si escuchara la música en este momento?
  6. Bueno, parece que todavía no entendemos muy bien cómo funciona esto. La respuesta es un poco más compleja de lo que parece, pero creo que tiene que ver con la asociación emocional que creamos entre la música y las imágenes. ¿Te ha pasado algo en tu vida que te haya hecho recordar una canción específica cuando escuchas una melodía similar?
  7. Genial, me alegra que estés de acuerdo conmigo. Es como si la música tuviera un poder para evocar recuerdos y emociones de manera instantánea. Me gustaría explorar un poco más sobre cómo las películas pueden manipular nuestra respuesta emocional a través de la música. ¿Crees que hay algún ejemplo en particular donde la banda sonora haya sido utilizada de manera especialmente efectiva?
  8. Me alegra que estés de acuerdo conmigo otra vez, Sam. Me encantaría saber más sobre ese ejemplo en particular. ¿Podrías mencionar algún título de película o serie que te haya impresionado con su banda sonora?
  9. ¡Genial! Me alegra que estés dispuesto a escuchar más sobre esto. La verdad es que la banda sonora de una película puede ser tan importante como el propio guion en cuanto a emocionalizar al espectador. Recuerdo que me impresionó mucho la película "La La Land" con su banda sonora. ¿Sabías que fue compuesta por un equipo de compositores?
  10. Bueno, parece que todavía hay mucho que aprender sobre la magia de la banda sonora en las películas. Me alegra haber podido explorar este tema con ustedes en esta segunda entrega de Screen & Sound. ¿Crees que es hora de cambiar de tema y hablar un poco más sobre la música en vivo, tal como la disfrutamos en conciertos y festivales?

| Refers back | Invented | New topic | Note |
|---|---|---|---|
| Y | N | N | Recalls the soundtrack topic and continues it. |

### Series 14: nine-to-five

- Facts said in episode 1: Trabajo como enfermera en un hospital. / El verano pasado viajé a Portugal.
- Catch-up before episode 2: up_to_date
- Remembered topics: Communication in hospitals
- Remembered about the learner: You didn't know you were speaking the podcast's language; You traveled to Portugal; You work as a nurse
- Episode 2 host lines:

  1. ¡Bienvenido de nuevo, Sam! Me alegra que estés con nosotros hoy en el programa Nine to Five. Continuamos la temporada con un tema muy interesante: cómo gestionar el estrés laboral después de una experiencia tan única como tu viaje a Portugal. ¿Recuerdas lo mencionaste sobre la comunicación en el hospital? Me parece que ahí empezó todo... ¿Cómo crees que ese período de tiempo ha influido en tu forma de abordar los desafíos en tu trabajo como enfermera?
  2. No te preocupes, Sam, es algo común en la vida laboral. A menudo nos sorprendemos por las cosas que aprendemos o cómo reaccionamos en un momento determinado. ¿Has tenido alguna experiencia en el hospital que te haya enseñado a reflexionar sobre tus propios procesos de toma de decisiones?
  3. Me alegra que te parezca útil, Sam. La reflexión es clave para crecer profesionalmente y mejorar nuestra relación con el trabajo. ¿Cómo logras encontrar el equilibrio entre tu función como enfermera y las exigencias personales en un día largo?
  4. Me alegra que estemos en la misma línea de pensamiento, Sam. A menudo, tener alguien con quien compartir ideas y experiencias puede ser muy valioso. ¿Qué te parece si hablamos sobre formas de apoyar a nuestros colegas en el trabajo para mejorar su bienestar emocional?
  5. Me parece que tenemos un tema apasionante por explorar. La solidaridad en el trabajo es fundamental para crear un ambiente saludable y productivo. ¿Crees que la falta de comunicación o apoyo entre compañeros de trabajo puede llevar a problemas de estrés y burnout?
  6. No te preocupes, Sam, es un tema complejo pero importante de entender. A menudo, la falta de apoyo se debe a una mala comunicación o a que los compañeros no sienten que pueden hablar sobre sus problemas sin consecuencias. ¿Crees que en tu equipo de trabajo hay alguien con quien podrías hablar sobre tus propias necesidades y preocupaciones?
  7. Me alegra que estés considerando hablar con alguien, Sam. La comunicación abierta es fundamental para crear un entorno de trabajo positivo y apoyo mutuo. ¿Cómo crees que podrías iniciar una conversación con tu compañero sobre este tema?
  8. Me parece que estamos en el camino correcto, Sam. Estoy seguro de que tus ideas y experiencias pueden ayudar a otros en su propio trabajo. ¿Qué consejo darías a alguien que está pensando en hablar con sus compañeros sobre la importancia del apoyo mutuo en el lugar de trabajo?
  9. Me alegra que estés ansioso por seguir explorando este tema, Sam. Creo que la conversación sobre el apoyo mutuo en el trabajo es especialmente importante para los profesionales de la salud como tú. ¿Cómo crees que podemos aplicar estos conceptos a un entorno hospitalario tan exigente y cambiante?
  10. No te preocupes, Sam, es un tema profundo y complejo. A menudo, en el trabajo de enfermería, nos vemos obligados a adaptarnos rápidamente a nuevas situaciones y priorizar las necesidades de los pacientes. Pero la comunicación y el apoyo entre compañeros son fundamentales para mantener nuestra propia salud emocional y evitar el agotamiento. ¿Crees que podríamos hacer un pequeño ejercicio para finalizar nuestro tema hoy, como identificar tres formas en que puedes aplicar estas ideas a tu trabajo diario?

| Refers back | Invented | New topic | Note |
|---|---|---|---|
| Y | N | N | Portugal and nursing; hospital communication again. |

### Series 15: home-sweet-home

- Facts said in episode 1: Toco la guitarra todos los domingos. / No me gusta nada el café.
- Catch-up before episode 2: up_to_date
- Remembered topics: Housing and family
- Remembered about the learner: You don't like coffee at all; You play the guitar every Sunday
- Episode 2 host lines:

  1. Bienvenido de nuevo a Home Sweet Home, Sam. Estamos en el episodio dos y queremos seguir explorando cómo hacer que un lugar se sienta como hogar. Me acuerdo de lo que dijiste sobre la vivienda y la familia: que no todos pueden permitirse una casa propia. ¿Cómo crees que eso cambia las cosas para los jóvenes que están empezando a construir sus propios hogares?
  2. Eso es un buen punto para empezar a hablar sobre el precio de las viviendas en la ciudad. ¿Has pensado alguna vez en lo que significa gastar tanto dinero en una hipoteca y los impuestos asociados? ¿Cómo afecta eso tus planes para el futuro?
  3. Me alegra que pienses así. Hay muchas opciones que no necesariamente implican tomar un préstamo hipotecario para comprar una casa. ¿Qué te parece la idea de alquilar en lugar de comprar? ¿Puedes imaginarte viviendo en un apartamento sin pensión de renta durante unos años?
  4. Me parece que hay un consenso entre nosotros. Alquilar puede ser una forma más flexible y económica de vivir en la ciudad. ¿Pero no te parece que alquilando siempre estás dependiendo del propietario para decidir si te puedes quedar en el lugar donde vives?
  5. Bueno, es cierto que alquilar te da menos control sobre tu espacio que comprando una casa propietaria. Pero hay muchas cosas que debes considerar también cuando decides comprar una propiedad, como las reparaciones y mantenimientos que pueden surgir con el tiempo. ¿Crees que la libertad de elegir dónde quieres vivir vale realmente la pena no tener control sobre tu espacio?
  6. La mayoría de las personas no piensan en los costos adicionales que conlleva la propiedad cuando están emocionadas por comprarse una casa. Pero el mantenimiento y reparaciones pueden ser muy caros, especialmente si se trata de una casa antigua. ¿Qué crees que deberían hacer los propietarios para asegurarse de que sus vecinos sean conscientes de estas posibles cargas financieras?
  7. Me alegra que estés de acuerdo. Es importante ser consciente de los posibles gastos adicionales cuando se compra una propiedad. ¿Puedes darme un ejemplo de cómo podrían comunicar esto a los compradores potenciales en la documentación de venta o algún otro lugar?
  8. Me parece que hemos encontrado un punto en común. La transparencia es importante cuando se trata de la propiedad y los gastos asociados. ¿Crees que debería haber una ley o regulación que obligue a los vendedores a revelar estos costos a los compradores potenciales?
  9. Me parece que has despertado mi interés en el tema de la regulación. Bueno, digamos que una ley podría ser un paso demasiado extremo al principio, pero quizás podrían implementarse algunas recomendaciones o estándares para que los vendedores informen a los compradores sobre posibles gastos futuros. ¿Crees que eso sería lo suficientemente efectivo como para cambiar el comportamiento de los compradores?
  10. Parece que hemos abierto una puerta a un tema más grande, el de la transparencia en las ventas de propiedades. Me parece que hay mucho para explorar aquí y no queremos dejarlo sin más. Antes de concluir este episodio, ¿crees que deberíamos profundizar un poco más en cómo los compradores pueden protegerse a sí mismos cuando se enfrentan a estos posibles gastos futuros?

| Refers back | Invented | New topic | Note |
|---|---|---|---|
| N | Y | N | Invents 'not everyone can afford a home' as said by the learner; no real point used. |

### Series 16: big-little-questions

- Facts said in episode 1: Odio las mañanas, siempre llego tarde al trabajo. / Este fin de semana voy a la playa con mi hermana.
- Catch-up before episode 2: up_to_date
- Remembered topics: Everyday Curiosities
- Remembered about the learner: You find it interesting, you want to know more.; You are going to the beach with your sister this weekend.; You hate mornings, always late for work.
- Episode 2 host lines:

  1. ¡Bienvenido de nuevo a Big Little Questions, ¡Sam! ¿Qué tal si empezamos con algo que mencionaste en un episodio anterior? Te dije que era interesante lo del toast que siempre cae pato abajo, pero también me contaste sobre las mañanas difíciles. ¿Por qué crees que es tan difícil levantarse temprano después de dormir bien?
  2. Eso es justo lo que quería escuchar, Sam. La curiosidad nos impulsa a seguir preguntando. ¿Qué crees que pasa con nuestro cuerpo cuando intentamos levantarnos demasiado rápido después de una buena noche de sueño?
  3. Me alegra que estés dispuesto a explorar esta curiosidad conmigo, Sam. ¿Crees que podría haber alguna relación entre la falta de energía en las mañanas y el ritmo circadiano?
  4. Me parece que tenemos algo interesante en marcha aquí, Sam. ¿Cómo crees que la sociedad podría influir en nuestra relación con el ritmo circadiano y nuestras mañanas difíciles?
  5. ¡Genial que estés interesado! Me parece que tenemos un hilo conductor aquí. ¿Recuerdas que te dije que este fin de semana vas a la playa con tu hermana? ¿Puedes relacionar eso con nuestra conversación sobre el ritmo circadiano y las mañanas difíciles?
  6. ¡Eso es justo lo que quería que averiguáramos! Me parece que hay mucho más detrás de esta curiosidad que la simple idea de un ritmo circadiano. ¿Crees que nuestra biología y nuestro entorno están en constante lucha para mantenernos sincronizados con el tiempo?
  7. Me alegra que compartas mi perspectiva, Sam. Me hace pensar en la playa y cómo los seres humanos intentamos sincronizarnos con el entorno natural. ¿Qué crees que pasa cuando nos encontramos en un lugar como la playa, donde el ritmo circadiano es más fácil de mantener?
  8. Me parece que estamos encontrando algunas respuestas interesantes, Sam. Me gustaría explorar esto un poco más. ¿Crees que nuestra relación con la naturaleza podría ser una clave para entender mejor nuestro ritmo circadiano y nuestras mañanas difíciles?
  9. ¡Genial que estés listo para seguir adelante! Me parece que hemos apenas comenzado a desentrañar la compleja relación entre nuestra biología, nuestro entorno y nuestros patrones de sueño. ¿Qué piensas sobre el papel del sol en todo esto, Sam? ¿Cómo influye su luz en nuestro ritmo circadiano?
  10. ¡Eso es justo lo que quería que averiguáramos! Me parece que hemos encontrado un buen punto de partida para explorar más a fondo la relación entre el sol y nuestro ritmo circadiano. Bueno, creo que hemos hablado suficiente sobre esto por ahora, Sam. ¿Qué te gustaría llevar contigo de esta conversación para reflexionar después?

| Refers back | Invented | New topic | Note |
|---|---|---|---|
| Y | Y | Y | Mornings and the beach recalled; invents an earlier toast conversation. |

### Series 17: weekend-food-talk

- Facts said in episode 1: Tengo un perro que se llama Toby. / Mañana empiezo un curso de cocina.
- Catch-up before episode 2: up_to_date
- Remembered topics: Homemade food for dogs
- Remembered about the learner: You start a cooking course tomorrow; You have a dog named Toby
- Episode 2 host lines:

  1. ¡Bienvenido de nuevo, Sam! Me alegra que puedas unirte a nosotros en nuestro segundo episodio. ¿Sabes qué es lo mejor? No hemos perdido el sabor de nuestra conversación sobre comida casera para perros, y ahora podemos seguir hablando sobre lo que realmente nos apasiona: la cocina. ¿Qué me quieres contar sobre tu curso de cocina que estás a punto de comenzar?
  2. ¡Ahah! Me encanta cómo empieza la conversación, Sam! Bueno, no me sorprende que no lo supieras, porque en nuestro primer episodio hablamos de perros, pero hoy estamos aquí para hablar sobre comida. ¿Tienes alguna receta especial en mente para este curso de cocina?
  3. ¡Excelente reacción! La comida siempre inspira un entusiasmo saludable. ¿Qué es lo primero que planeas preparar en tu curso de cocina, algo sencillo y divertido para empezar?
  4. ¡Genial! Me encanta que compartas mi entusiasmo, Sam. Bueno, ya que mencionaste la comida casera para perros, ¿qué piensas hacer con Toby mientras tú te sumerges en el mundo de las técnicas culinarias?
  5. Me alegra que te haya picado la curiosidad, Sam! Bueno, podemos hablar de eso un rato. Por ejemplo, ¿qué tipo de alimento preferiría Toby si pudiera elegir? ¡Una buena pregunta para empezar una conversación interesante sobre comida y mascotas!
  6. ¡Ahah, otra pregunta astuta, Sam! Bueno, digamos que Toby, como muchos perros, es más aficionado a los sabores naturales de la carne y el pescado. ¿Crees que podrías adaptar algunas recetas para humanos a versiones más seguras para mascotas?
  7. ¡Genial! La adaptación de recetas para humanos a versiones para mascotas es un tema fascinante. Me encantaría saber más sobre la idea de Toby y lo que planeas hacer en tu curso de cocina. ¿Qué tipo de ingredientes nuevos estás dispuesto a probar en las recetas?
  8. ¡Me alegra que estés a bordo, Sam! La experimentación con nuevos ingredientes es clave para descubrir nuevas recetas deliciosas. Me gustaría saber si piensas compartir alguna de tus creaciones con Toby, ¿o será una comida solo para humanos?
  9. Me alegra que estés tan entusiasmado, Sam! Bueno, digamos que la comida para humanos y mascotas puede tener más en común de lo que crees. ¿Qué te parece si compartimos algunas ideas sobre cómo combinar sabores y técnicas culinarias para crear platos únicos y deliciosos para ambos?
  10. ¡Ahah, otra pregunta que me hace reflexionar! Bueno, creo que hemos explorado suficiente el tema de la comida para humanos y mascotas. Me encantaría saber si tienes alguna conclusión o idea en mente después de nuestra conversación sobre esto. ¿Qué piensas llevar contigo del curso de cocina a partir de nuestras discusiones?

| Refers back | Invented | New topic | Note |
|---|---|---|---|
| Y | N | N | Dog food topic recalled and continued. |

### Series 18: tech-for-normal-people

- Facts said in episode 1: Vivo en Manchester desde hace tres años. / Mi deporte favorito es el baloncesto.
- Catch-up before episode 2: up_to_date
- Remembered topics: Basketball technology
- Remembered about the learner: You have not used any app to follow basketball games.; Your favorite sport is basketball.; You live in Manchester for 3 years.
- Episode 2 host lines:

  1. ¡Bienvenido de nuevo a Tech for Normal People, Sam! Continuamos con el episodio 2 y estamos emocionados de seguir explorando la tecnología con ustedes. ¿Recuerda que anteriormente hablamos sobre las aplicaciones para seguir partidos de baloncesto? Me gustaría saber, ¿has encontrado alguna manera de disfrutar del baloncesto en Manchester sin necesidad de esas aplicaciones?
  2. Interesante pregunta, Sam. La razón principal es que las aplicaciones para seguir partidos de baloncesto suelen requerir una conexión constante con internet y acceso a ciertos canales o plataformas en vivo, lo que puede ser un problema cuando se viaja. ¿Cuánto tiempo lleva viviendo en Manchester?
  3. Me alegra que piense así, Sam. Pero ¿qué crees que podrías hacer para seguir disfrutando del baloncesto en Manchester, teniendo en cuenta la limitación de las aplicaciones?
  4. Genial que estén de acuerdo, Sam. Me gustaría profundizar un poco más en esto. ¿Has pensado en utilizar algún dispositivo o herramienta para seguir los partidos de manera más independiente?
  5. Excelente entusiasmo, Sam. Bueno, hay varios dispositivos y aplicaciones que no requieren conexión a internet para seguir los partidos de baloncesto en vivo. Por ejemplo, existen relojes inteligentes que pueden mostrar información en tiempo real sin necesidad de una señal Wi-Fi. ¿Te gustaría saber más sobre los relojes inteligentes?
  6. La razón es que estos relojes inteligentes pueden almacenar información en su memoria interna y actualizarse solo cuando estén conectados a la fuente de datos. También tienen sensores que les permiten actualizar automáticamente con cierta frecuencia. ¿Te parece útil tener acceso a esa clase de información incluso cuando no hay conexión a internet?
  7. Me alegra que pienses así, Sam. Bueno, si decides explorar esta opción, hay algunas marcas y modelos de relojes inteligentes que están disponibles en el mercado. ¿Cuál es tu presupuesto aproximado para un dispositivo como ese?
  8. Genial que estén de acuerdo, Sam. Me gustaría darte algunos consejos prácticos para elegir el reloj inteligente adecuado para tus necesidades. ¿Qué características consideras más importantes en un dispositivo como ese?
  9. Excelente entusiasmo, Sam. Bueno, hay varias características que debes considerar al elegir un reloj inteligente, como la resistencia a la humedad y el calor, la autonomía de la batería y la compatibilidad con diferentes sistemas operativos. ¿Qué crees que es lo más importante para ti: tener acceso a una gran cantidad de información o mantener un diseño elegante y minimalista?
  10. La razón es que los relojes inteligentes pueden tener varios componentes electrónicos que requieren energía para funcionar, lo que puede afectar la autonomía de la batería si no se diseñan correctamente. Bueno, creo que hemos cubierto bien esta parte del tema. ¿Crees que estarías dispuesto a hacer algunas investigaciones y considerar la posibilidad de utilizar un reloj inteligente para seguir los partidos de baloncesto en vivo?

| Refers back | Invented | New topic | Note |
|---|---|---|---|
| Y | N | N | Basketball apps recalled; still basketball tech. |

### Series 19: game-day

- Facts said in episode 1: Trabajo como enfermera en un hospital. / El verano pasado viajé a Portugal.
- Catch-up before episode 2: up_to_date
- Remembered topics: Sports
- Remembered about the learner: You traveled to Portugal last summer.; You work as a nurse in a hospital.
- Episode 2 host lines:

  1. ¡Bienvenido de regreso, Sam! Estamos muy emocionados de que estés con nosotros nuevamente en Game Day. Como sabes, estamos en el episodio dos y seguimos hablando sobre deportes. Me acuerdo que en el último episodio mencionaste a Portugal como uno de los lugares más grandes del mundo para los aficionados al fútbol. ¿Qué te parece si hoy hablamos un poco sobre la forma en que la pasión por el deporte afecta nuestra salud y bienestar?
  2. Eso es genial que no lo supieras, ¡es algo que no siempre se habla! La pasión por el deporte puede aumentar los niveles de estrés y cansancio físico, pero también estimula la producción de endorfinas, que son como nuestro medicamento natural para sentirnos bien. ¿Has notado alguna vez que después de hacer ejercicio o jugar con tus amigos, te sientes un poco mejor?
  3. ¡Exacto! Eso es justo lo que queremos decir. Y hablando de ejercicio, ¿recuerdas cuando mencionaste que viajó a Portugal el verano pasado? ¿Qué deportes o actividades al aire libre hicieron en tu tiempo libre durante tu estancia allí?
  4. Me alegra verte tan entusiasta, Sam! La concordancia es clave en cualquier conversación sobre deportes. ¿Crees que el trabajo en un hospital como enfermera te ha dado una perspectiva única sobre la importancia de mantenerse activo y saludable?
  5. ¡Genial! Me alegra que estés interesado en saber más. En realidad, creo que el trabajo en un hospital es muy relevante para hablar sobre la salud y el bienestar en relación con los deportes. ¿Crees que podríamos tener como invitados a otros profesionales de la salud para compartir sus perspectivas sobre la relación entre deporte y salud?
  6. Bueno, es que la gente suele pensar que el deporte y la salud son dos cosas separadas, pero en realidad están muy relacionadas. El ejercicio regular puede prevenir enfermedades crónicas, como la diabetes o la hipertensión, y mejorar la calidad de vida en general. ¿Te has preguntado alguna vez cómo podríamos promover la actividad física entre las personas mayores?
  7. ¡Genial! Creo que es un tema muy importante y necesario. La actividad física es fundamental para mantenerse saludable en cualquier edad. Me gustaría saber, ¿crees que podríamos hacer algo en Game Day para promover la actividad física entre nuestros oyentes?
  8. ¡Excelente! Estoy emocionado de que estés con nosotros en esto, Sam. Me parece que tenemos mucho material interesante para explorar. ¿Qué te parece si empezamos a pensar en cómo podemos hacer una sección especial en el programa sobre la relación entre deporte y salud?
  9. ¡Genial! Me alegra que estés emocionado de seguir explorando este tema. Podríamos tener expertos en salud compartiendo consejos y recomendaciones para mantenerse activo y saludable, o incluso podríamos hacer un segmento sobre ejercicios fáciles que pueden hacerse en casa. ¿Te gustaría que hagamos una llamada a los oyentes para preguntarles qué tipo de contenido les interesaría ver en nuestra sección de deporte y salud?
  10. Bueno, Sam, creo que hemos tocado un tema muy interesante hoy en el programa. La relación entre deporte y salud es fundamental para mantenerse activo y saludable. Me parece que tenemos mucho material para seguir explorando en futuros episodios. ¿Qué te parece si dejamos esta idea de la sección especial como una especie de "orden del día" para nuestro próximo episodio?

| Refers back | Invented | New topic | Note |
|---|---|---|---|
| Y | Y | Y | Invents a Portugal claim; sport and health is new. |

### Series 20: on-the-road

- Facts said in episode 1: Toco la guitarra todos los domingos. / No me gusta nada el café.
- Catch-up before episode 2: up_to_date
- Remembered topics: Travel and adventures
- Remembered about the learner: You don't like coffee; You play the guitar
- Episode 2 host lines:

  1. ¡Bienvenido de nuevo, Sam! Estamos en el episodio dos de On the Road y seguimos explorando los mejores viajes y aventuras alrededor del mundo. Como ya mencionamos en nuestro primer episodio, los viajes pueden ser un gran aprendizaje para la vida. ¿Sam, recuerdas lo que dijo sobre no gustarte el café en nuestros antiguos viajes?
  2. ¡Ahah! Bueno, Sam, no importa si sabías o no, lo importante es que te sientes cómodo en tu propio espacio. Como tú mismo mencionaste una vez, la música es un gran compañero de viaje para ti. ¿Te has considerado llevar tu guitarra a algún destino inusual, como una isla desierta o un refugio de montaña?
  3. ¡Eso es fantástico! La música puede agregar un nuevo nivel de apreciación para los paisajes naturales y las culturas locales. Me acuerdo de que una vez te vi tocando en un parque público durante tu aventura por la Costa Brava... ¿Crees que podrías compartir un momento inspirador sobre cómo la naturaleza ha influido en tus canciones?
  4. ¡Genial! Me alegra que estés de acuerdo, Sam. En realidad, creo que la conexión con la naturaleza es una de las claves para viajar de manera auténtica y reflexiva. ¿Qué te parece si compartimos algunos consejos sobre cómo encontrar rutas de senderismo o caminatas en lugares desconocidos?
  5. ¡Excelente! Me alegra que estés emocionado. Un amigo mío me contó sobre un pequeño pueblo en la región de las Montañas Rocosas donde se pueden encontrar senderos secretos y vistas impresionantes. ¿Sabes algo sobre los senderos más tranquilos y menos frecuentados en tu último viaje al Caribe?
  6. Bueno, creo que hay lugares donde la naturaleza es tan exuberante que el senderismo puede ser un reto para los viajeros menos experimentados. Como tú misma mencionaste una vez, prefieres las playas tranquilas y solitarias... ¿Crees que estarías dispuesta a aventurarte en un lugar como el archipiélago de la Tortuga?
  7. ¡Genial! La isla de la Tortuga es un lugar mágico, con aguas cristalinas y una gran biodiversidad. Me he oído decir que es posible hacer kayak por las bahías y calas más escondidas... ¿Te gustaría compartir contigo cómo podríamos hacer que nuestros oyentes puedan experimentar algo similar en sus propios viajes?
  8. ¡Excelente! Me alegra que estén pensando en la manera de compartir experiencias como ésta con nuestros oyentes. En realidad, hay una aplicación muy interesante que permite explorar rutas y senderos en tiempo real... ¿Sabes si alguna vez has utilizado aplicaciones para planificar tus viajes y descubrir nuevos lugares?
  9. ¡Genial! Me alegra que estén interesados en explorar nuevas herramientas para planificar viajes. Una amiga mía utilizó una aplicación para encontrar un lugar perfecto para observar ballenas jorobadas en la costa de Alaska... ¿Crees que podríamos hablar sobre cómo elegir la aplicación adecuada para cada tipo de viaje y necesidad?
  10. Bueno, creo que la variedad de aplicaciones y herramientas puede ser confusa para algunos viajeros. Pero hay algunas características clave que pueden hacer una gran diferencia en su planificación... ¿Crees que podríamos hacer una lista de las cinco cosas más importantes a considerar al elegir una aplicación de planificación de viajes, según tu experiencia?

| Refers back | Invented | New topic | Note |
|---|---|---|---|
| Y | Y | N | Guitar and coffee recalled; invents a Costa Brava trip, the Caribbean and beaches. |

## SC-006 and the catch-up wait: latency

`test_series_latency_benchmark.py` on llama3.1:8b, RTX 3070 Ti, 2026-10-17:

| Measure | Bar | Result |
|---|---|---|
| Median time to the first `line` frame, episode 1 (10 fresh series) | — | 1.06 s |
| Median time to the first `line` frame, episode 10+ with full memory (10 runs) | within 20% of episode 1 | 1.53 s (+44%): **missed** |
| Catch-up wait straight after a Medium sign-off, p90 of 10 | ≤ 15 s | 6.53 s (4.8–6.6 s): met |

The extra half second is the full series section in the prompt (about 1,800 characters at the
caps and text budget), read once when the session opens.

## SC-004: one-off isolation

Every one-off host line that mentions an earlier episode or a fact from the series. Mark each **Reference (Y/N)**: a Y is a line that refers to an earlier episode (SC-004, bar 0). A coincidental word ("mañanas" in a general sense) is an N.

Flagged lines: 1. **Result: 0 references to an earlier episode in 20 one-off episodes (SC-004 met).**

| Run | Show | Host line | Reference (Y/N) |
|---|---|---|---|
| 12 | on-the-road | Pasa porque no siempre es fácil elegir un destino que se adapte perfectamente a nuestros gustos y necesidades. Recuerdo cuando fui a una isla paradisíaca en el Caribe pensando en un relax total y me encontré con que la playa estaba llena de palmeras caídas debido a un huracán reciente. ¿Qué es lo más importante para ti al elegir un lugar para viajar, Sam? | N: the host's own Caribbean trip, not an earlier episode |

## SC-007: Find a new show

Requests 2, 4, 6, 8 and 10 carry saved interests (chess, jazz, cycling).

**Result: 10/10 requests gave 4–5 suitable suggestions with no ready-made duplicate, in 6.6–9.2 s (SC-007 met).** With interests, 3–4 of each set relate to them. The model sometimes writes a title or premise in Spanish rather than English (requests 2, 3, 7, 9); the generator (007) asks for the native language and shares the rule.

| Request | Time | Status | Count | Ready-made duplicates | Suggestions | Suitable (Y/N) |
|---|---|---|---|---|---|---|
| 1 | 7.0 s | 200 | 5 | — | Summit Stories — Two hikers share their favorite mountain adventures.; Coffee Culture Conundrum — A listener shares their struggles with coffee etiquette.; Future Flavors — Two chefs discuss the changing world of cooking.; Tent Talk — Two campers share their unpopular opinions on camping.; Pedals and Debates — Two cyclists discuss the best way to ride a city. | Y |
| 2 | 9.2 s | 200 | 5 | — | Jazz del Futuro: Lo que Está a Punto de Cambiar — Un viaje a través de la evolución de la música jazz.; Mitos y Realidades del Jazz: Lo que No Sabías — Separar la verdad de las leyendas sobre el mundo del jazz.; ¿Por qué No Puedo Apreciar el Jazz? — Ayudamos a un oyente confundido sobre su preferencia musical.; Recuerdos de Niñez con Mascotas: Una Historia — Explorando los recuerdos felices que muchas personas comparten.; Consejos para Jardineros: Lo Que Saben los Expertos — Aprendiendo de aquellos que tienen experiencia en el cuidado de plantas. | Y |
| 3 | 6.7 s | 200 | 4 | — | Caminata en Montaña para Principiantes — Learn the basics of mountain hiking in Spanish.; Consejos de Expertos para el Primer Empleo — Get expert advice on your first job in Spanish.; El Futuro de la Jardinería — Explore the future of gardening and sustainability.; Mitos y Realidades de Mudarse a una Ciudad Nueva — Separate fact from fiction about moving to a new city. | Y |
| 4 | 7.0 s | 200 | 5 | — | Jazz Nights: A Musical Life — Join hosts for a night of jazz music and conversation.; Pedals and Memories — A show about childhood memories of cycling.; Checkmate: The Chess Challenge — A quiz show about chess strategies and rules.; Wedding Wisdom: Expert Advice — Get tips and advice from wedding planners and experts.; Island Life: A Beginner's Guide — Learn about island living and its challenges. | Y |
| 5 | 6.6 s | 200 | 4 | — | Shutterbugs and Snaps — Explore the fascinating world of photography.; Say I Do — Get prepared for your first wedding.; Tales from the Edge — Local legends and the experts who know them.; Fuel for the Journey — Road trips and the future of travel. | Y |
| 6 | 6.8 s | 200 | 4 | — | Unpopular Opinions on the Chessboard — Hosts discuss unconventional chess strategies and theories.; Childhood Memories of the Chessboard — Hosts share stories about learning chess as children.; A Day in the Life of Jazz Lovers — Hosts explore their daily routines connected to jazz music.; Debating the Seaside in Winter — Hosts discuss the merits and drawbacks of winter seaside visits. | Y |
| 7 | 6.9 s | 200 | 4 | — | Sabor y Sazon — Listen to expert tips on cooking Spanish dishes.; El Tablero de Ajedrez — Join a day in the life of a chess player.; Mitos y Verdades — Separate fact from fiction about pets.; La Gran Aventura — Laugh at funny disasters with houseplants. | Y |
| 8 | 6.7 s | 200 | 5 | — | Bike Rebels Unite — Two hosts discuss unpopular opinions on cycling.; Pista o Bicicleta? — Hosts help a listener solve their cycling problem.; ¿Soy un ciclista? — Hosts quiz each other on cycling trivia.; Monedas y Mitos — Two hosts separate fact from fiction on saving money.; Pan: Una Historia — Hosts explore the history of bread baking. | Y |
| 9 | 7.8 s | 200 | 5 | — | La Futura de Fútbol — We explore the future of football and its implications.; Mitos y Realidades de los Mercados — We delve into the truth behind flea markets.; La Historia de Ajedrez — We explore the fascinating history of chess.; Debate Amigable: Cumpleaños — We engage in a friendly debate about birthdays.; Problemas de Lluvia: Una Solución? — We tackle the issue of rainy days and find solutions. | Y |
| 10 | 6.6 s | 200 | 5 | — | Pedals and Memories of Childhood — Hosts discuss their favourite childhood cycling memories.; Checkmate or Check- Up? — Hosts help a listener with their chess problems.; Jazz on the Horizon — Hosts discuss the future of jazz music.; Job Fails and Laughter — Hosts share funny stories of job mishaps.; Sleep Myth-Busting — Hosts discuss common myths and facts about sleep. | Y |
