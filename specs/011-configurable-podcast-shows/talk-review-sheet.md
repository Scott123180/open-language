# Talk review sheet: Configurable Podcast Shows (011)

Hand-run on the default local setup: Ollama `llama3.1:8b` on an RTX 3070 Ti (8 GB), Piper voices,
Spanish, 2026-11-04. T063 ran in full on 2026-11-04 (host talk, 20 + 20 episodes); the latency figures below are
re-measured on an idle machine at both context sizes.

## SC-011: time to the first sentence's audio (T062 latency benchmark, 20 Continues per length)

| Host lines | First run (4,096 tokens, busy machine) | 4,096 tokens, idle | 8,192 tokens, idle | Target |
|---|---|---|---|---|
| Short | 4.45 s | 5.26 s | 5.71 s | ≤ 5 s |
| Medium | 5.19 s | 4.38 s | 5.83 s | ≤ 5 s |
| Long | 5.65 s | 7.34 s | 7.54 s | ≤ 5 s |

p90 over 20 Continues; the runs are noisy (Short slower than Medium at 4,096). **Missed, and accepted
by the learner (2026-11-04)**; configured talk ships as experimental (T131).

## R18: context size

| Context | `prompt_eval_count`, end of a Long episode of Long lines | Model on the GPU (`ollama ps`) |
|---|---|---|
| 4,096 (Ollama's default) | 4,094 first run, 4,077 idle run | 86% (5.6 GB) |
| 8,192 (011's window for small models) | 3,882 | 78% (6.2 GB) |

At 4,096 tokens a Long episode reaches the limit, so its start is cut. At the learner's request
(2026-11-04) models up to 10 GB on disk now ask for 8,192 tokens on every request
(`OPEN_LANGUAGE_OLLAMA_SMALL_MODEL_MAX_GB`, `OPEN_LANGUAGE_OLLAMA_SMALL_MODEL_CONTEXT`). On the 8 GB
card that moves 8 more points of `llama3.1:8b` onto the CPU, which costs about 0.2 to 1.5 s at p90.

## Host talk, full run (T063): 20 Medium One host + 20 Medium Panel, Beginner, defaults

Run 2026-11-04 on `llama3.1:8b` with the 8,192-token context (35% of the model on the CPU), each
episode played past its wrap-up to its sign-off with scripted questions and a last thought. 841 host
lines; intents: open 40, greet 20, react 300, explain 154, story 97, answer 150, wrap_up 40, sign_off 40.

| Criterion | Measured | Target | Result |
|---|---|---|---|
| SC-001 median sentences per discussion line | 4.0 | ≥ 3 | met |
| SC-001 inviting share before the wrap-up | 0.42 | ≤ 0.50 | met |
| SC-005 longest run without an invitation | ≤ 4 in every episode | ≤ 4 | met |
| SC-013 median sentences per explain/answer line | 4.0 | ≥ 4 | met |
| SC-002 Beginner sentences within 8 words | **0.07** | ≥ 0.90 | missed; **accepted by the learner, 2026-11-04** |
| SC-015 episodes signed off after the last thought | 40 / 40 | 100% | met |
| R19 address tag share (rather than the fallback) | 0.82 | recorded | ≥ 50%, no Open item needed |
| SC-012 host questions stored as not for the learner | 117 to no one, 19 to the lead, 6 to the second | ≤ 5% of questions to the learner | **likely missed** (see below) |

SC-002 (accepted as it is): the hosts keep three to five sentences, but the sentences are long (15–25 words) with
subordinate clauses and past and conditional tenses, as in the sanity run. The level's sentence rules
are in the prompt; `llama3.1:8b` does not follow them while also writing several sentences.

SC-012: most of the 117 questions stored with no addressee are plainly put to the learner ("¿Suele
sentirse cansado después de un largo viaje?") but carry `[@all]` or no tag, so the line does not hand
the learner the turn. A review of the episode transcripts should count them against the questions to
the learner; the tag share is 82%, so the instruction is followed, but the tag chosen is often wrong.

### To review by hand

SC-003, learner question → next host line:

- E1 one_host Q: ¿Por qué bostezamos? → [answer] El bostezo es un reflejo natural que sucede en muchos animales. Cuando estamos cansados o despiertos por poco, nuestro cerebro envía señales para despertar a nuestros músculos. Los músculos de la mandíbula se relajan y luego se contratan bruscamente, lo que produce el sonido del bostezo. Esto ayuda a mantener nuestra salud física y mental. ¿Suele sentirse cansado después de un largo viaje?
- E1 one_host Q: ¿Cuánto tiempo dura un bostezo? → [answer] Un bostezo dura solo unos segundos, pero puede variar dependiendo de la persona y las circunstancias. En promedio, un bostezo dura entre 1 a 3 segundos, aunque algunos pueden durar hasta 5 segundos en casos extremos. Esto sucede porque el reflejo del bostezo es automático y no requiere mucha energía cerebral. El cerebro envía una señal para que los músculos de la mandíbula se contraten y relajen rápidamente. El proceso es muy rápido.
- E1 one_host Q: ¿Los animales también bostezan? → [answer] Sí, muchos animales también bostezan como reflejo natural. Esto sucede porque el reflejo del bostezo es un mecanismo automático que se encuentra en la mayoría de los vertebrados y algunos invertebrados. Por ejemplo, los perros y las gatas también bostezan para despertar a sus músculos y mantener saludable su sistema nervioso. Esto muestra que el reflejo del bostezo es un proceso universal que se encuentra en muchos seres vivos.
- E2 one_host Q: ¿Por qué bostezamos? → [answer] El bostezo es un comportamiento común en humanos y muchos animales. Creemos que se debe a que nuestro cerebro necesita un poco de aire fresco mientras dormitamos o nos relajamos. Algunos científicos piensan que el bostezo puede ayudar a regular la presión arterial y la circulación sanguínea. ¿Crees que es una forma natural para reanimarnos después de un descanso?,.
- E2 one_host Q: ¿Cuánto tiempo dura un bostezo? → [answer] Un bostezo dura solo unos segundos, pero puede sentirse mucho más largo cuando lo estás experimentando. El músculo del diafragma se contrae y luego se relaja en un ciclo rápido. Algunos expertos creen que el tiempo total de un bostezo es alrededor de 15 a 30 segundos desde que comienza hasta que termina. ¿Crees que podrías contar exactamente cuántos segundos dura un bostezo?,.
- E2 one_host Q: ¿Los animales también bostezan? → [answer] Sí, muchos animales también bostezan, incluyendo perros, gatos y hasta algunos mamíferos salvajes. El bostezo es una respuesta natural para regular la presión arterial y la circulación sanguínea, y parece que muchos seres vivos la necesitan. Algunos animales pueden bostezar con más frecuencia o en situaciones diferentes a las humanas. Incluso se han observado bostezos en algunas especies de pájaros y reptiles,.

SC-012, host questions not stored as for the learner:

- E1 one_host ?→None: El bostezo es un reflejo natural que sucede en muchos animales. Cuando estamos cansados o despiertos por poco, nuestro cerebro envía señales para despertar a nuestros músculos. Los músculos de la mandíbula se relajan y luego se contratan bruscamente, lo que produce el sonido del bostezo. Esto ayuda a mantener nuestra salud física y mental. ¿Suele sentirse cansado después de un largo viaje?
- E1 one_host ?→None: Entiendo por qué la gravedad es la causa de este fenómeno tan común. Me parece que esto sucede en muchas situaciones, como cuando se hace pan o se come un sandwich. ¿Le ha pasado a usted alguna vez que el pan con mantequilla le haya caído por accidente?
- E1 one_host ?→None: Cuando el pan se inclina, la mantequilla tiende a mantener su forma original y no se mueve hacia abajo por sí sola. Esto sucede porque la mantequilla es un líquido con una alta viscosidad que resiste cambios de forma rápidos. Por ejemplo, si tienes un trozo de pan con mantequilla en el plato y lo inclinas, verás que la mantequilla se queda en la parte superior durante un rato antes de derramarse. Esto le sucede a mucha gente cuando come pan con mantequilla. ¿Comparte su pan con alguien cuando está comiendo?
- E1 one_host ?→None: Recuerdo una vez que estaba cocinando un sandwich para mi amigo y me di cuenta de que siempre caía la mantequilla hacia arriba. Le pregunté a mi madre por qué sucedía eso y ella me explicó que era debido a la gravedad. Me pareció lógico, pero también me hizo reflexionar sobre cómo la física está presente en nuestras vidas cotidianas de manera sorprendente. ¿Ha tenido alguna experiencia similar mientras cocinaba o preparaba una comida?

SC-014, openings and wrap-ups:

- E1 one_host [open] Bienvenido a Big Little Questions, soy Hugo. Estoy emocionado de compartir con usted estas curiosidades cotidianas. Hoy exploraremos por qué siempre cae el pan con mantequilla por arriba. ¿Qué sabe acerca de este fenómeno común? Me alegra tenerlo aquí.
- E2 one_host [open] ¡Bienvenido a Big Little Questions! Me llamo Hugo y soy uno de los presentadores de este programa. Hoy exploraremos la curiosidad diaria sobre por qué el pan se queda con la mantequilla abajo cuando lo tiramos. ¿Qué piensas que puede haber detrás de esto? Queremos saber tu opinión,.
- E3 one_host [open] Bienvenido a Big Little Questions, soy tu anfitrión, estoy aquí para hablar sobre las curiosidades del día a día. ¿Por qué siempre cae el pan con mantequilla hacia abajo? Es un tema que me ha fascinado desde la infancia y quería compartirlo contigo. Hoy vamos a explorar esta pregunta y otras como ella en este espacio de conversación. Estoy emocionado de tener tu perspectiva sobre esto.
- E1 one_host [wrap_up] Me alegra que haya disfrutado de nuestro programa hoy. En resumen, hemos explorado por qué el pan con mantequilla siempre cae por arriba y cómo la gravedad y la viscosidad intervienen en este fenómeno cotidiano. Queremos agradecerle su participación en Big Little Questions y le pedimos que nos dé una última reflexión sobre lo que hemos hablado hoy ¿Qué le quedará de esta conversa?
- E2 one_host [wrap_up] El programa está a punto de terminar, pero antes de irnos queremos resumir lo que aprendimos hoy sobre los bostezos: son una respuesta automática del cuerpo que ayuda a regular la presión arterial y la circulación sanguínea. Han sido fascinantes descubrir cómo funcionan y por qué nos hacemos bostezar en situaciones cotidianas. ¿Tienes alguna última reflexión sobre los bostezos que quieras compartir con nosotros?,.
- E3 one_host [wrap_up] Me alegra que hayas disfrutado del programa y casi hemos llegado al final de nuestra conversación sobre los pequeños misterios de la vida cotidiana. En resumen, hoy hablamos sobre fenómenos naturales como el bostezo, la gravedad y cómo cae el pan con mantequilla hacia abajo. Antes de despedirnos, ¿qué te parece si compartes una última reflexión sobre algo que te haya parecido interesante o llamativo en nuestra conversación?

The full list (131 learner questions and every opening, wrap-up and sign-off) is in the run's report,
`host-talk-report.md` beside this sheet.

## Still to run

- The full host-talk benchmark (20 + 20 episodes), plus 10 Presented and 10 Conversation for SC-004.
- The guest-episode benchmark (T128) once US4 exists.
- SC-003, SC-012, SC-014 and SC-016 transcript reviews.
