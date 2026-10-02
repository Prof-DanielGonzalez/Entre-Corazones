        const modes = {
            names: { title: 'Match de nombres', description: 'Una respuesta rápida para dos nombres.', icon: '💘', endpoint: '/api/calcular' },
            complete: { title: 'Lectura completa', description: 'Una mirada más detallada a lo que comparten.', icon: '💌', endpoint: '/api/lectura-completa' },
            tarot: { title: 'Tarot del amor', description: 'Tres cartas simbólicas para explorar tu pregunta.', icon: '🔮', endpoint: '/api/tarot' },
            zodiac: { title: 'Compatibilidad zodiacal', description: 'Una lectura de sus signos y energías.', icon: '✨', endpoint: '/api/zodiacal' },
            chat: { title: 'Conversa con la IA', description: 'Un espacio personal para pensar en tus vínculos y sentimientos.', icon: '💬' },
            quiz: { title: 'Test de pareja', description: 'Cuatro preguntas para descubrir coincidencias y diferencias.', icon: '🫶', endpoint: '/api/test-pareja' },
            celebrity: { title: 'Match de ficción', description: 'Compara tu química simbólica con personajes y famosos.', icon: '🎬', endpoint: '/api/match-celebridad' },
            ranking: { title: '1 contra todos', description: 'Un ranking recreativo entre varios nombres.', icon: '🏆', endpoint: '/api/ranking' },
            random: { title: 'Prueba tu suerte', description: 'Una historia aleatoria y disparatada.', icon: '🎲', endpoint: '/api/match-aleatorio' },
            community: { title: 'Vota en comunidad', description: 'Una votación anónima de parejas de ficción.', icon: '🗳️' }
        };
        const modeCards = document.querySelectorAll('.mode-card');
        const forms = document.querySelectorAll('.mode-form');
        const result = document.getElementById('result');
        const feedback = document.getElementById('feedback');
        const playTitle = document.getElementById('play-title');
        const playDescription = document.getElementById('play-description');
        const playSymbol = document.getElementById('play-symbol');
        const chatPanel = document.getElementById('chat-panel');
        const chatMessages = document.getElementById('chat-messages');
        const chatStatus = document.getElementById('chat-status');
        const chatForm = document.getElementById('chat-form');
        const chatInput = document.getElementById('chat-input');
        const chatSend = document.getElementById('chat-send');
        const chatVibe = document.getElementById('chat-vibe');
        const communityPanel = document.getElementById('community-panel');
        const communityList = document.getElementById('community-list');
        const communityStatus = document.getElementById('community-status');
        const themeChoice = document.getElementById('theme-choice');
        const historyToggle = document.getElementById('history-toggle');
        const historyPanel = document.getElementById('history-panel');
        const historyList = document.getElementById('history-list');
        const CHAT_STORAGE_KEY = 'entre-corazones-chat-v1';
        const CHAT_HISTORY_LIMIT = 30;
        const RESULT_HISTORY_KEY = 'entre-corazones-results-v1';
        const RESULT_HISTORY_LIMIT = 24;
        const THEME_STORAGE_KEY = 'entre-corazones-theme-v1';
        const CAPSULE_STORAGE_KEY = 'entre-corazones-capsules-v1';
        const VOTER_STORAGE_KEY = 'entre-corazones-voter-v1';
        const FONT_STORAGE_KEY = 'entre-corazones-large-text-v1';
        const CONTRAST_STORAGE_KEY = 'entre-corazones-high-contrast-v1';
        const SOUND_STORAGE_KEY = 'entre-corazones-sound-v1';
        const MOTION_STORAGE_KEY = 'entre-corazones-motion-v1';
        const VIBES = ['natural', 'romantico', 'comico', 'mistico', 'directo'];
        const appViews = new Map(['home', 'games', 'readings', 'community', 'play', 'tools']
            .map((view) => [view, document.getElementById(`${view}-view`)]));
        const MODE_CATEGORIES = {
            names: ['games', 'Juegos y matches'],
            quiz: ['games', 'Juegos y matches'],
            celebrity: ['games', 'Juegos y matches'],
            ranking: ['games', 'Juegos y matches'],
            random: ['games', 'Juegos y matches'],
            complete: ['readings', 'Lecturas y conversación'],
            tarot: ['readings', 'Lecturas y conversación'],
            zodiac: ['readings', 'Lecturas y conversación'],
            chat: ['readings', 'Lecturas y conversación'],
            community: ['community', 'En comunidad']
        };
        let currentView = 'home';
        const currentMode = () => document.querySelector('.mode-card[aria-pressed="true"]')?.dataset.mode || 'names';

        function renderView(view) {
            if (!appViews.has(view)) view = 'home';
            currentView = view;
            appViews.forEach((element, name) => { element.hidden = name !== view; });
            historyToggle.setAttribute('aria-expanded', String(view === 'tools'));
            window.scrollTo({ top: 0, behavior: 'smooth' });
        }

        function navigateTo(view, replace = false) {
            if (!appViews.has(view)) return;
            const url = `${location.pathname}${location.search}${view === 'home' ? '' : `#${view}`}`;
            if (replace) history.replaceState({ appView: view }, '', url);
            else if (currentView !== view) history.pushState({ appView: view }, '', url);
            renderView(view);
        }

        document.querySelectorAll('[data-page-link]').forEach((button) => {
            button.addEventListener('click', () => navigateTo(button.dataset.pageLink));
        });
        document.querySelectorAll('[data-go-back]').forEach((button) => {
            button.addEventListener('click', () => {
                if (currentView === 'play') navigateTo(MODE_CATEGORIES[currentMode()][0]);
                else navigateTo('home');
            });
        });
        document.querySelectorAll('[data-open-mode]').forEach((button) => {
            button.addEventListener('click', () => {
                document.querySelector(`.mode-card[data-mode="${button.dataset.openMode}"]`)?.click();
            });
        });
        window.addEventListener('popstate', () => {
            renderView(location.hash.slice(1) || 'home');
        });
        const initialView = appViews.has(location.hash.slice(1)) ? location.hash.slice(1) : 'home';
        history.replaceState({ appView: initialView }, '', `${location.pathname}${location.search}${initialView === 'home' ? '' : `#${initialView}`}`);
        renderView(initialView);

        let resultHistory = [];
        let capsules = [];
        let installPrompt = null;
        let audioContext = null;

        function readLocalStorage(key, fallback) {
            try {
                return localStorage.getItem(key) ?? fallback;
            } catch (error) {
                return fallback;
            }
        }

        function saveLocalStorage(key, value) {
            try {
                localStorage.setItem(key, value);
                return true;
            } catch (error) {
                const state = document.getElementById('accessibility-state');
                if (state) state.textContent = 'El navegador no permitió guardar esta preferencia o dato.';
                return false;
            }
        }

        function voterToken() {
            let token = readLocalStorage(VOTER_STORAGE_KEY, '');
            if (!/^[0-9a-f-]{36}$/i.test(token)) {
                if (crypto.randomUUID) token = crypto.randomUUID();
                else {
                    const bytes = crypto.getRandomValues(new Uint8Array(16));
                    bytes[6] = (bytes[6] & 15) | 64;
                    bytes[8] = (bytes[8] & 63) | 128;
                    const hex = [...bytes].map((value) => value.toString(16).padStart(2, '0')).join('');
                    token = `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
                }
                saveLocalStorage(VOTER_STORAGE_KEY, token);
            }
            return token;
        }

        function loadResultHistory() {
            try {
                const saved = localStorage.getItem(RESULT_HISTORY_KEY);
                if (!saved) return [];
                const parsed = JSON.parse(saved);
                if (!Array.isArray(parsed)) throw new Error('El historial de lecturas no tiene el formato esperado.');
                return parsed.filter((entry) => entry
                    && typeof entry.id === 'string'
                    && typeof entry.mode === 'string'
                    && Object.hasOwn(modes, entry.mode)
                    && entry.data
                    && typeof entry.data === 'object'
                    && typeof entry.createdAt === 'string').slice(0, RESULT_HISTORY_LIMIT);
            } catch (error) {
                return [];
            }
        }

        function saveResultHistory() {
            resultHistory = resultHistory.slice(0, RESULT_HISTORY_LIMIT);
            try {
                localStorage.setItem(RESULT_HISTORY_KEY, JSON.stringify(resultHistory));
            } catch (error) {
                feedback.textContent = 'El navegador no pudo guardar el historial de lecturas.';
                feedback.hidden = false;
            }
            renderResultHistory();
        }

        function loadTheme() {
            try {
                const saved = localStorage.getItem(THEME_STORAGE_KEY);
                if (['pastel', 'night', 'neon'].includes(saved)) return saved;
            } catch (error) {
                return 'pastel';
            }
            return 'pastel';
        }

        function applyTheme(theme) {
            const validTheme = ['pastel', 'night', 'neon'].includes(theme) ? theme : 'pastel';
            document.documentElement.dataset.theme = validTheme;
            themeChoice.value = validTheme;
            try {
                localStorage.setItem(THEME_STORAGE_KEY, validTheme);
            } catch (error) {
                chatStatus.textContent = 'El navegador no pudo guardar tu tema visual; el cambio sigue activo en esta visita.';
            }
        }

        applyTheme(loadTheme());

        function applyAccessibilityPreferences() {
            const large = readLocalStorage(FONT_STORAGE_KEY, 'false') === 'true';
            const contrast = readLocalStorage(CONTRAST_STORAGE_KEY, 'false') === 'true';
            document.documentElement.classList.toggle('accessibility-large', large);
            document.documentElement.classList.toggle('accessibility-contrast', contrast);
            document.getElementById('font-toggle').setAttribute('aria-pressed', String(large));
            document.getElementById('contrast-toggle').setAttribute('aria-pressed', String(contrast));
            document.getElementById('font-toggle').textContent = large ? 'Tamaño normal' : 'Aumentar texto';
            document.getElementById('contrast-toggle').textContent = contrast ? 'Contraste normal' : 'Alto contraste';
            const sound = readLocalStorage(SOUND_STORAGE_KEY, 'false') === 'true';
            document.getElementById('sound-toggle').setAttribute('aria-pressed', String(sound));
            document.getElementById('sound-toggle').textContent = sound ? 'Desactivar sonido' : 'Activar sonido';
            document.getElementById('motion-toggle').setAttribute('aria-pressed', readLocalStorage(MOTION_STORAGE_KEY, 'false') === 'true');
        }
        applyAccessibilityPreferences();

        function reproducirSonidoSuave() {
            if (readLocalStorage(SOUND_STORAGE_KEY, 'false') !== 'true') return;
            try {
                const AudioCtor = window.AudioContext || window.webkitAudioContext;
                if (!AudioCtor) throw new Error('Tu navegador no admite audio web.');
                audioContext ||= new AudioCtor();
                const oscillator = audioContext.createOscillator();
                const gain = audioContext.createGain();
                oscillator.type = 'sine';
                oscillator.frequency.setValueAtTime(660, audioContext.currentTime);
                oscillator.frequency.exponentialRampToValueAtTime(880, audioContext.currentTime + .11);
                gain.gain.setValueAtTime(.0001, audioContext.currentTime);
                gain.gain.exponentialRampToValueAtTime(.045, audioContext.currentTime + .015);
                gain.gain.exponentialRampToValueAtTime(.0001, audioContext.currentTime + .16);
                oscillator.connect(gain).connect(audioContext.destination);
                oscillator.start();
                oscillator.stop(audioContext.currentTime + .17);
            } catch (error) {
                document.getElementById('accessibility-state').textContent = error.message || 'No se pudo reproducir el sonido.';
            }
        }

        function lanzarParticulas() {
            if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
            const canvas = document.getElementById('particle-canvas');
            const context = canvas.getContext('2d');
            if (!context) return;
            const ratio = Math.min(window.devicePixelRatio || 1, 2);
            canvas.width = Math.floor(window.innerWidth * ratio);
            canvas.height = Math.floor(window.innerHeight * ratio);
            canvas.hidden = false;
            context.scale(ratio, ratio);
            const particles = Array.from({ length: 48 }, () => ({
                x: Math.random() * window.innerWidth,
                y: -20 - Math.random() * 180,
                speed: 1.5 + Math.random() * 3,
                drift: (Math.random() - .5) * 2,
                size: 11 + Math.random() * 12,
                hue: [336, 351, 18, 290][Math.floor(Math.random() * 4)]
            }));
            let frame = 0;
            const draw = () => {
                context.clearRect(0, 0, window.innerWidth, window.innerHeight);
                particles.forEach((particle) => {
                    particle.y += particle.speed;
                    particle.x += particle.drift;
                    context.font = `${particle.size}px serif`;
                    context.fillStyle = `hsl(${particle.hue} 75% 58% / .85)`;
                    context.fillText('♥', particle.x, particle.y);
                });
                frame += 1;
                if (frame < 150) requestAnimationFrame(draw);
                else { canvas.hidden = true; context.clearRect(0, 0, canvas.width, canvas.height); }
            };
            requestAnimationFrame(draw);
        }

        async function activarMovimiento() {
            const state = document.getElementById('accessibility-state');
            try {
                if (!window.DeviceOrientationEvent) throw new Error('Este dispositivo no ofrece sensor de orientación.');
                if (typeof window.DeviceOrientationEvent.requestPermission === 'function') {
                    const permission = await window.DeviceOrientationEvent.requestPermission();
                    if (permission !== 'granted') throw new Error('No se concedió permiso para el sensor.');
                }
                window.addEventListener('deviceorientation', (event) => {
                    if (readLocalStorage(MOTION_STORAGE_KEY, 'false') !== 'true') return;
                    const tilt = Math.max(-8, Math.min(8, Number(event.gamma) || 0));
                    document.querySelector('.brand-mark').style.transform = `rotate(${tilt}deg)`;
                }, { passive: true });
                saveLocalStorage(MOTION_STORAGE_KEY, 'true');
                state.textContent = 'Movimiento suave activado. Puedes apagarlo cuando quieras.';
            } catch (error) {
                saveLocalStorage(MOTION_STORAGE_KEY, 'false');
                state.textContent = error.message || 'No se pudo activar el movimiento.';
            }
            applyAccessibilityPreferences();
        }

        function loadChatHistory() {
            try {
                const saved = localStorage.getItem(CHAT_STORAGE_KEY);
                if (!saved) return [];
                const parsed = JSON.parse(saved);
                if (!Array.isArray(parsed)) throw new Error('El historial guardado no tiene el formato esperado.');
                return parsed
                    .filter((message) => message
                        && ['user', 'assistant'].includes(message.role)
                        && typeof message.content === 'string'
                        && message.content.length <= 1500)
                    .slice(-CHAT_HISTORY_LIMIT);
            } catch (error) {
                chatStatus.textContent = 'No pudimos leer el historial guardado en este navegador. Puedes borrarlo para empezar una nueva conversación.';
                return [];
            }
        }

        let chatHistory = loadChatHistory();

        function saveChatHistory() {
            chatHistory = chatHistory.slice(-CHAT_HISTORY_LIMIT);
            try {
                localStorage.setItem(CHAT_STORAGE_KEY, JSON.stringify(chatHistory));
            } catch (error) {
                chatStatus.textContent = 'El navegador no pudo guardar el historial. La conversación actual sigue disponible mientras esta página permanezca abierta.';
            }
        }

        function renderChatHistory() {
            chatMessages.replaceChildren();
            if (!chatHistory.length) {
                chatMessages.append(makeElement('p', 'chat-empty', 'Hola, este es un lugar tranquilo para ordenar tus ideas. ¿Qué te gustaría compartir hoy?'));
                return;
            }
            chatHistory.forEach((message) => {
                chatMessages.append(makeElement('div', `chat-bubble ${message.role}`, message.content));
            });
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }

        async function leerEventosChat(response, onDelta) {
            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';
            let finalizado = false;
            const leerBloque = (bloque) => {
                let tipo = 'message';
                const datos = [];
                bloque.split('\n').forEach((linea) => {
                    if (linea.startsWith('event:')) tipo = linea.slice(6).trim();
                    if (linea.startsWith('data:')) datos.push(linea.slice(5).trimStart());
                });
                if (!datos.length) return;
                const payload = datos.join('\n');
                if (tipo === 'error') {
                    const error = JSON.parse(payload);
                    throw new Error(error.error || 'La respuesta se interrumpió.');
                }
                if (payload === '[DONE]') {
                    finalizado = true;
                    return;
                }
                const evento = JSON.parse(payload);
                if (typeof evento.delta === 'string') onDelta(evento.delta);
            };

            while (true) {
                const { value, done } = await reader.read();
                buffer += decoder.decode(value || new Uint8Array(), { stream: !done });
                const bloques = buffer.split('\n\n');
                buffer = bloques.pop() || '';
                bloques.forEach(leerBloque);
                if (done) break;
            }
            if (buffer.trim()) leerBloque(buffer);
            if (!finalizado) throw new Error('La conexión terminó antes de completar la respuesta.');
        }

        renderChatHistory();

        modeCards.forEach((card) => {
            card.addEventListener('click', () => {
                modeCards.forEach((item) => item.setAttribute('aria-pressed', String(item === card)));
                const mode = modes[card.dataset.mode];
                forms.forEach((form) => { form.hidden = form.dataset.form !== card.dataset.mode; });
                chatPanel.hidden = card.dataset.mode !== 'chat';
                communityPanel.hidden = card.dataset.mode !== 'community';
                playTitle.textContent = mode.title;
                playDescription.textContent = mode.description;
                playSymbol.textContent = mode.icon;
                const [, categoryLabel] = MODE_CATEGORIES[card.dataset.mode];
                document.getElementById('play-breadcrumb').textContent = categoryLabel;
                result.hidden = true;
                feedback.hidden = true;
                chatStatus.textContent = '';
                communityStatus.textContent = '';
                if (card.dataset.mode === 'community') cargarComunidad();
                navigateTo('play');
            });
        });

        themeChoice.addEventListener('change', () => applyTheme(themeChoice.value));
        document.getElementById('font-toggle').addEventListener('click', () => {
            const enabled = document.documentElement.classList.toggle('accessibility-large');
            saveLocalStorage(FONT_STORAGE_KEY, String(enabled));
            applyAccessibilityPreferences();
        });
        document.getElementById('contrast-toggle').addEventListener('click', () => {
            const enabled = document.documentElement.classList.toggle('accessibility-contrast');
            saveLocalStorage(CONTRAST_STORAGE_KEY, String(enabled));
            applyAccessibilityPreferences();
        });
        document.getElementById('sound-toggle').addEventListener('click', () => {
            const enabled = readLocalStorage(SOUND_STORAGE_KEY, 'false') !== 'true';
            if (enabled) {
                const AudioCtor = window.AudioContext || window.webkitAudioContext;
                if (!AudioCtor) {
                    document.getElementById('accessibility-state').textContent = 'Tu navegador no admite audio web.';
                    return;
                }
            }
            saveLocalStorage(SOUND_STORAGE_KEY, String(enabled));
            applyAccessibilityPreferences();
            document.getElementById('accessibility-state').textContent = enabled ? 'Sonido suave activado. Se reproducirá al revelar un resultado.' : 'Sonido desactivado.';
        });
        document.getElementById('motion-toggle').addEventListener('click', () => {
            if (readLocalStorage(MOTION_STORAGE_KEY, 'false') === 'true') {
                saveLocalStorage(MOTION_STORAGE_KEY, 'false');
                document.querySelector('.brand-mark').style.transform = '';
                document.getElementById('accessibility-state').textContent = 'Movimiento desactivado.';
                applyAccessibilityPreferences();
            } else {
                activarMovimiento();
            }
        });
        document.getElementById('install-app').addEventListener('click', async () => {
            if (!installPrompt) return;
            await installPrompt.prompt();
            installPrompt = null;
            document.getElementById('install-app').hidden = true;
        });
        window.addEventListener('beforeinstallprompt', (event) => {
            event.preventDefault();
            installPrompt = event;
            document.getElementById('install-app').hidden = false;
        });
        if ('serviceWorker' in navigator && (location.protocol === 'https:' || location.hostname === 'localhost' || location.hostname === '127.0.0.1')) {
            navigator.serviceWorker.register('/service-worker.js').catch((error) => {
                document.getElementById('accessibility-state').textContent = `No se pudo activar el modo offline: ${error.message}`;
            });
        }
        fetch('/api/celebridades')
            .then(async (response) => {
                const data = await response.json();
                if (!response.ok) throw new Error(data.error || 'No se pudo cargar la lista.');
                const options = document.getElementById('celebrity-options');
                data.opciones.forEach((person, index) => {
                    const label = makeElement('label', 'option-check');
                    const input = makeElement('input');
                    input.type = 'checkbox';
                    input.name = 'opciones';
                    input.value = person.nombre;
                    input.id = `celebrity-${index}`;
                    label.htmlFor = input.id;
                    label.append(input, document.createTextNode(`${person.nombre} · ${person.tipo}`));
                    options.append(label);
                });
            })
            .catch((error) => { document.getElementById('celebrity-options').textContent = error.message; });

        document.getElementById('metrics-load').addEventListener('click', async () => {
            const tokenInput = document.getElementById('metrics-token');
            const status = document.getElementById('metrics-status');
            const output = document.getElementById('metrics-results');
            status.textContent = 'Consultando…';
            output.replaceChildren();
            try {
                const response = await fetch('/api/metrics', { headers: { 'X-Metrics-Token': tokenInput.value } });
                const data = await response.json();
                if (!response.ok) throw new Error(data.error || 'No se pudieron cargar las métricas.');
                [
                    `Matches en ${data.dias} días: ${data.matches}`,
                    `Promedio simbólico: ${data.promedio}%`,
                    `Lecturas: ${data.lecturas}`,
                    `Valoraciones: ${data.feedback.reduce((sum, item) => sum + item.total, 0)}`,
                    `Votos comunitarios: ${data.votos_comunidad.reduce((sum, item) => sum + item.total, 0)}`
                ].forEach((line) => output.append(makeElement('p', 'ranking-item', line)));
                data.serie_diaria.slice(-7).forEach((day) => {
                    output.append(makeElement('p', 'ranking-item', `${day.fecha}: ${day.matches} matches · ${day.promedio}% promedio · ${day.lecturas} lecturas`));
                });
                const feedbackPorModo = new Map();
                data.feedback.forEach((item) => {
                    const counts = feedbackPorModo.get(item.modo) || { positivos: 0, negativos: 0 };
                    if (item.rating > 0) counts.positivos += item.total;
                    else counts.negativos += item.total;
                    feedbackPorModo.set(item.modo, counts);
                });
                feedbackPorModo.forEach((counts, mode) => {
                    output.append(makeElement('p', 'ranking-item', `${modes[mode]?.title || mode}: 👍 ${counts.positivos} · 👎 ${counts.negativos}`));
                });
                status.textContent = 'Métricas agregadas cargadas.';
            } catch (error) {
                status.textContent = error.message || 'No se pudieron cargar las métricas.';
            } finally {
                tokenInput.value = '';
            }
        });

        document.getElementById('clear-all').addEventListener('click', () => {
            try {
                Object.keys(localStorage).filter((key) => key.startsWith('entre-corazones-')).forEach((key) => localStorage.removeItem(key));
                resultHistory = [];
                capsules = [];
                chatHistory = [];
                renderResultHistory();
                renderCapsules();
                renderChatHistory();
                forms.forEach((form) => form.reset());
                result.replaceChildren();
                result.hidden = true;
                chatPanel.hidden = true;
                communityPanel.hidden = true;
                communityStatus.textContent = '';
                modeCards.forEach((card) => card.setAttribute('aria-pressed', String(card.dataset.mode === 'names')));
                forms.forEach((form) => { form.hidden = form.dataset.form !== 'names'; });
                playTitle.textContent = modes.names.title;
                playDescription.textContent = modes.names.description;
                playSymbol.textContent = modes.names.icon;
                applyTheme('pastel');
                localStorage.removeItem(THEME_STORAGE_KEY);
                applyAccessibilityPreferences();
                document.getElementById('capsule-title').textContent = 'Cápsulas del tiempo';
                document.getElementById('capsule-list').replaceChildren(makeElement('p', 'feature-note', 'Todavía no guardaste cápsulas.'));
                navigateTo('home', true);
                document.getElementById('accessibility-state').textContent = 'Se borraron los datos guardados por esta app en este navegador. Los votos y métricas agregados del servidor no se pueden borrar desde aquí.';
            } catch (error) {
                document.getElementById('accessibility-state').textContent = 'El navegador no permitió borrar todos los datos locales.';
            }
        });
        historyToggle.addEventListener('click', () => {
            navigateTo('tools');
        });
        document.getElementById('history-clear').addEventListener('click', () => {
            resultHistory = [];
            try {
                localStorage.removeItem(RESULT_HISTORY_KEY);
            } catch (error) {
                feedback.textContent = 'El navegador no permitió borrar el historial guardado.';
                feedback.hidden = false;
            }
            renderResultHistory();
        });

        const challengeName = new URLSearchParams(window.location.search).get('p1');
        if (challengeName) {
            document.getElementById('quick-name1').value = challengeName.slice(0, 80);
            document.querySelector('.challenge-tools p').textContent = 'Te invitaron a jugar: escribe tu nombre y descubre el resultado. El nombre de quien te desafió aparece en este enlace.';
            history.replaceState({ appView: 'play' }, '', `${location.pathname}#play`);
            renderView('play');
        }
        document.getElementById('challenge-link').addEventListener('click', async () => {
            const nombre = document.getElementById('quick-name1').value.trim();
            const challengeStatus = document.querySelector('.challenge-tools p');
            if (!nombre) {
                challengeStatus.textContent = 'Escribe primero tu nombre para crear el enlace de desafío.';
                document.getElementById('quick-name1').focus();
                return;
            }
            const url = new URL(window.location.href);
            url.search = '';
            url.searchParams.set('p1', nombre.slice(0, 80));
            const texto = `Te desafío a probar nuestro match 💘 Completa el resultado aquí: ${url.toString()}`;
            try {
                if (navigator.share) {
                    await navigator.share({ title: 'Un desafío de Entre Corazones', text: texto, url: url.toString() });
                } else {
                    await navigator.clipboard.writeText(url.toString());
                    challengeStatus.textContent = 'Enlace copiado. Al abrirlo, tu amiga verá tu nombre precargado.';
                }
            } catch (error) {
                if (error.name !== 'AbortError') {
                    challengeStatus.textContent = 'No se pudo compartir automáticamente. Copia este enlace: ';
                    const link = makeElement('a', '', url.toString());
                    link.href = url.toString();
                    link.rel = 'noopener noreferrer';
                    challengeStatus.append(link);
                }
            }
        });

        function makeElement(tag, className, text) {
            const element = document.createElement(tag);
            if (className) element.className = className;
            if (text !== undefined) element.textContent = text;
            return element;
        }

        function loadCapsules() {
            try {
                const stored = readLocalStorage(CAPSULE_STORAGE_KEY, '[]');
                const parsed = JSON.parse(stored);
                return Array.isArray(parsed) ? parsed.filter((item) => item && typeof item.id === 'string' && typeof item.dueAt === 'string' && item.data && modes[item.mode])
                    .map((item) => {
                        if (/^\d{4}-\d{2}-\d{2}$/.test(item.dueAt)) return item;
                        const legacyDate = new Date(item.dueAt);
                        if (Number.isNaN(legacyDate.getTime())) return null;
                        const dueAt = `${legacyDate.getFullYear()}-${String(legacyDate.getMonth() + 1).padStart(2, '0')}-${String(legacyDate.getDate()).padStart(2, '0')}`;
                        return { ...item, dueAt };
                    }).filter(Boolean) : [];
            } catch (error) {
                return [];
            }
        }

        function saveCapsules() {
            capsules = capsules.slice(0, 24);
            if (saveLocalStorage(CAPSULE_STORAGE_KEY, JSON.stringify(capsules))) renderCapsules();
        }

        function fechaEnMeses(fecha, meses) {
            const dia = fecha.getDate();
            const destino = new Date(fecha.getFullYear(), fecha.getMonth() + meses, 1);
            const ultimoDia = new Date(destino.getFullYear(), destino.getMonth() + 1, 0).getDate();
            destino.setDate(Math.min(dia, ultimoDia));
            return destino;
        }

        function fechaCapsulaLocal(valor) {
            const [year, month, day] = valor.split('-').map(Number);
            return new Date(year, month - 1, day, 12);
        }

        function hoyComoFechaLocal() {
            const hoy = new Date();
            return `${hoy.getFullYear()}-${String(hoy.getMonth() + 1).padStart(2, '0')}-${String(hoy.getDate()).padStart(2, '0')}`;
        }

        function descargarRecordatorio(capsule) {
            const dateOnly = capsule.dueAt.replace(/-/g, '');
            const calendar = [
                'BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//Entre Corazones//Capsulas//ES',
                'BEGIN:VEVENT', `UID:${capsule.id}@entre-corazones`, `DTSTAMP:${new Date().toISOString().replace(/[-:]/g, '').replace(/\.\d{3}/, '')}`,
                `DTSTART;VALUE=DATE:${dateOnly}`, `SUMMARY:${String(capsule.data.titulo || 'Releer una cápsula de Entre Corazones').replace(/[\\,;]/g, ' ')}`,
                'DESCRIPTION:Vuelve a leer la cápsula guardada en este dispositivo.', 'BEGIN:VALARM', 'TRIGGER:-P1D', 'ACTION:DISPLAY',
                'DESCRIPTION:Mañana puedes volver a leer tu cápsula del amor.', 'END:VALARM', 'END:VEVENT', 'END:VCALENDAR'
            ].join('\r\n');
            const url = URL.createObjectURL(new Blob([calendar], { type: 'text/calendar;charset=utf-8' }));
            const link = makeElement('a', '', 'Descargar recordatorio de calendario');
            link.href = url;
            link.download = 'capsula-entre-corazones.ics';
            link.click();
            setTimeout(() => URL.revokeObjectURL(url), 1000);
        }

        function renderCapsules() {
            const list = document.getElementById('capsule-list');
            list.replaceChildren();
            if (!capsules.length) {
                list.append(makeElement('p', 'feature-note', 'Todavía no guardaste cápsulas.'))
                return;
            }
            capsules.forEach((capsule) => {
                const item = makeElement('article', `capsule-item${capsule.dueAt <= hoyComoFechaLocal() ? ' due' : ''}`);
                const title = makeElement('span', '', `${capsule.data.titulo || 'Tu lectura'} · volver el ${fechaCapsulaLocal(capsule.dueAt).toLocaleDateString('es')}`);
                const open = makeElement('button', 'feature-button', 'Abrir');
                open.type = 'button';
                open.addEventListener('click', () => {
                    modeCards.forEach((card) => card.setAttribute('aria-pressed', String(card.dataset.mode === capsule.mode)));
                    document.getElementById('play-breadcrumb').textContent = MODE_CATEGORIES[capsule.mode][1];
                    forms.forEach((form) => { form.hidden = true; });
                    chatPanel.hidden = true;
                    communityPanel.hidden = true;
                    communityPanel.hidden = true;
                    playTitle.textContent = modes[capsule.mode].title;
                    playDescription.textContent = 'Una cápsula guardada solo en este dispositivo.';
                    playSymbol.textContent = modes[capsule.mode].icon;
                    renderResult(capsule.mode, capsule.data);
                    navigateTo('play');
                });
                const calendar = makeElement('button', 'feature-button', 'Añadir a calendario');
                calendar.type = 'button';
                calendar.addEventListener('click', () => descargarRecordatorio(capsule));
                item.append(title, open, calendar);
                list.append(item);
            });
        }

        function comprobarCapsulasVencidas() {
            const pendientes = capsules.filter((capsule) => capsule.dueAt <= hoyComoFechaLocal() && !capsule.notified);
            if (!pendientes.length) return;
            document.getElementById('capsule-panel').open = true;
            navigateTo('tools');
            document.getElementById('capsule-title').textContent = `Ya puedes releer ${pendientes.length === 1 ? 'tu cápsula' : 'tus cápsulas'} del tiempo`;
            document.getElementById('capsule-panel').open = true;
            if ('Notification' in window && Notification.permission === 'granted') {
                pendientes.forEach((capsule) => new Notification('Entre Corazones', { body: 'Llegó el momento de volver a leer tu cápsula del tiempo.' }));
            }
            const ids = new Set(pendientes.map((capsule) => capsule.id));
            capsules = capsules.map((capsule) => ids.has(capsule.id) ? { ...capsule, notified: true } : capsule);
            saveCapsules();
        }

        function cargarComunidad(successMessage = '') {
            communityList.replaceChildren();
            communityStatus.textContent = 'Cargando parejas de ficción…';
            fetch('/api/community')
                .then(async (response) => {
                    const data = await response.json();
                    if (!response.ok) throw new Error(data.error || 'No se pudo cargar la votación.');
                    communityList.replaceChildren();
                    data.pares.forEach((pair) => {
                        const item = makeElement('article', 'community-item');
                        const info = makeElement('div');
                        info.append(makeElement('strong', '', pair.nombre), makeElement('span', '', `${pair.descripcion} · Sí: ${pair.si} · No: ${pair.no}`));
                        const controls = makeElement('div', 'community-votes');
                        [['Sí 💚', true], ['No 💭', false]].forEach(([label, vote]) => {
                            const button = makeElement('button', 'vote-button', label);
                            button.type = 'button';
                            button.addEventListener('click', async () => {
                                button.disabled = true;
                                try {
                                    const answer = await fetch('/api/community/vote', {
                                        method: 'POST', headers: { 'Content-Type': 'application/json' },
                                        body: JSON.stringify({ id: pair.id, voto: vote, token: voterToken() })
                                    });
                                    const body = await answer.json();
                                    if (!answer.ok) throw new Error(body.error || 'No se pudo guardar tu voto.');
                                    cargarComunidad('¡Gracias! El conteo de la comunidad se actualizó.');
                                } catch (error) {
                                    communityStatus.textContent = error.message || 'No se pudo enviar el voto.';
                                    button.disabled = false;
                                }
                            });
                            controls.append(button);
                        });
                        item.append(info, controls);
                        communityList.append(item);
                    });
                    communityStatus.textContent = successMessage;
                })
                .catch((error) => { communityStatus.textContent = error.message || 'La votación comunitaria no está disponible.'; });
        }

        function renderResultHistory() {
            historyList.replaceChildren();
            if (!resultHistory.length) {
                historyList.append(makeElement('p', 'history-empty', 'Todavía no hay resultados guardados. Calcula un match o completa una lectura para verla aquí.'));
                return;
            }
            resultHistory.forEach((entry) => {
                const item = makeElement('article', 'history-item');
                const open = makeElement('button', 'history-open');
                open.type = 'button';
                const title = entry.data.titulo || modes[entry.mode].title;
                const summary = entry.data.resumen || entry.data.mensaje || '';
                const percentage = Number.isInteger(entry.data.porcentaje) ? ` · ${entry.data.porcentaje}%` : '';
                open.append(makeElement('strong', '', `${title}${percentage}`));
                open.append(makeElement('span', '', `${new Date(entry.createdAt).toLocaleString()} · ${summary}`));
                open.addEventListener('click', () => {
                    document.querySelectorAll('.mode-card').forEach((card) => {
                        card.setAttribute('aria-pressed', String(card.dataset.mode === entry.mode));
                    });
                    document.getElementById('play-breadcrumb').textContent = MODE_CATEGORIES[entry.mode][1];
                    forms.forEach((form) => { form.hidden = true; });
                    chatPanel.hidden = true;
                    communityPanel.hidden = true;
                    playTitle.textContent = modes[entry.mode].title;
                    playDescription.textContent = 'Una lectura guardada en este navegador.';
                    playSymbol.textContent = modes[entry.mode].icon;
                    renderResult(entry.mode, entry.data);
                    navigateTo('play');
                });
                const remove = makeElement('button', 'history-delete', 'Quitar');
                remove.type = 'button';
                remove.setAttribute('aria-label', `Borrar ${title} del historial`);
                remove.addEventListener('click', () => {
                    resultHistory = resultHistory.filter((record) => record.id !== entry.id);
                    saveResultHistory();
                });
                item.append(open, remove);
                historyList.append(item);
            });
        }

        resultHistory = loadResultHistory();
        renderResultHistory();
        capsules = loadCapsules();
        renderCapsules();
        comprobarCapsulasVencidas();

        function renderAdvice(parent, text) {
            const advice = makeElement('p', 'advice');
            advice.append(makeElement('strong', '', 'Una idea para llevarte: '), document.createTextNode(text));
            parent.append(advice);
        }

        function appendVibePicker(parent, id) {
            const wrapper = makeElement('div', 'vibe-picker');
            const label = makeElement('label', '', 'Estilo de respuesta');
            label.htmlFor = id;
            const select = makeElement('select');
            select.id = id;
            [
                ['natural', 'Natural y cálido'],
                ['romantico', 'Romántico'],
                ['comico', 'Sarcástico / cómico'],
                ['mistico', 'Místico / astro'],
                ['directo', 'Directo / pícaro']
            ].forEach(([value, text]) => {
                const option = makeElement('option', '', text);
                option.value = value;
                select.append(option);
            });
            wrapper.append(label, select);
            parent.append(wrapper);
            return select;
        }

        function textoParaCompartir(data, interpretacion) {
            const fragments = ['💗 Entre Corazones'];
            const title = typeof data.titulo === 'string' ? data.titulo : 'Mi lectura';
            fragments.push(title);
            const summary = data.resumen || data.mensaje;
            if (typeof summary === 'string') fragments.push(summary.slice(0, 260));
            if (Number.isInteger(data.porcentaje)) fragments.push(`Afinidad simbólica: ${data.porcentaje}%`);
            if (Array.isArray(data.ranking)) {
                fragments.push(`Ranking: ${data.ranking.map((item) => `${item.nombre} (${item.porcentaje}%)`).join(' · ')}`);
            }
            if (typeof data.comentario_ia === 'string') fragments.push(`Comentario de IA: ${data.comentario_ia.slice(0, 240)}`);
            if (Array.isArray(data.lecturas)) {
                data.lecturas.slice(0, 3).forEach((item) => {
                    if (item && typeof item.titulo === 'string' && typeof item.texto === 'string') {
                        fragments.push(`${item.titulo}: ${item.texto.slice(0, 160)}`);
                    }
                });
            }
            if (Array.isArray(data.cartas)) {
                data.cartas.slice(0, 3).forEach((card) => {
                    if (card && typeof card.nombre === 'string' && typeof card.mensaje === 'string') {
                        fragments.push(`${card.posicion || 'Carta'} — ${card.nombre}: ${card.mensaje.slice(0, 130)}`);
                    }
                });
            }
            if (typeof data.consejo === 'string') fragments.push(`Idea para llevarte: ${data.consejo}`);
            if (interpretacion) fragments.push(`Una mirada más profunda: ${interpretacion.slice(0, 300)}`);
            fragments.push('Lectura recreativa, para conversar y reflexionar.');
            return fragments.join('\n\n').slice(0, 1600);
        }

        function animarPorcentaje(elemento, valor) {
            const objetivo = Math.max(0, Math.min(100, Number(valor) || 0));
            const inicio = performance.now();
            const duracion = window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 0 : 850;
            const actualizar = (ahora) => {
                const avance = duracion ? Math.min((ahora - inicio) / duracion, 1) : 1;
                const suavizado = 1 - Math.pow(1 - avance, 3);
                elemento.textContent = `${Math.round(objetivo * suavizado)}%`;
                if (avance < 1) requestAnimationFrame(actualizar);
            };
            requestAnimationFrame(actualizar);
            if (navigator.vibrate && !window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
                navigator.vibrate(12);
            }
        }

        function compartirTarjetaComoImagen(data) {
            const canvas = document.createElement('canvas');
            canvas.width = 1200;
            canvas.height = 630;
            const context = canvas.getContext('2d');
            if (!context) return Promise.reject(new Error('Este navegador no pudo crear la tarjeta.'));

            const fondo = context.createLinearGradient(0, 0, 1200, 630);
            fondo.addColorStop(0, '#fff3f6');
            fondo.addColorStop(1, '#fff9ef');
            context.fillStyle = fondo;
            context.fillRect(0, 0, 1200, 630);
            context.fillStyle = '#ffffff';
            context.beginPath();
            context.roundRect(44, 40, 1112, 550, 34);
            context.fill();
            context.strokeStyle = '#f0dce4';
            context.lineWidth = 2;
            context.stroke();

            context.fillStyle = '#f9e5eb';
            context.beginPath();
            context.arc(600, 145, 67, 0, Math.PI * 2);
            context.fill();
            context.fillStyle = '#c84470';
            context.beginPath();
            context.moveTo(600, 188);
            context.bezierCurveTo(560, 160, 540, 139, 551, 119);
            context.bezierCurveTo(562, 99, 588, 106, 600, 124);
            context.bezierCurveTo(612, 106, 638, 99, 649, 119);
            context.bezierCurveTo(660, 139, 640, 160, 600, 188);
            context.fill();

            context.textAlign = 'center';
            context.fillStyle = '#3c2b39';
            context.font = '600 43px Georgia, serif';
            context.fillText(String(data.titulo || 'Entre Corazones').slice(0, 42), 600, 265);
            if (Number.isInteger(data.porcentaje)) {
                context.fillStyle = '#b93664';
                context.font = '600 96px Georgia, serif';
                context.fillText(`${Math.max(0, Math.min(100, data.porcentaje))}%`, 600, 377);
            }

            const texto = String(data.resumen || data.mensaje || 'Una lectura para conversar y reflexionar.').replace(/\s+/g, ' ');
            context.fillStyle = '#766575';
            context.font = '24px Segoe UI, sans-serif';
            const palabras = texto.split(' ');
            const lineas = [];
            let linea = '';
            palabras.forEach((palabra) => {
                const candidata = linea ? `${linea} ${palabra}` : palabra;
                if (context.measureText(candidata).width > 820 && linea) {
                    lineas.push(linea);
                    linea = palabra;
                } else {
                    linea = candidata;
                }
            });
            if (linea) lineas.push(linea);
            lineas.slice(0, 3).forEach((textoLinea, indice) => context.fillText(textoLinea, 600, 426 + indice * 34));
            context.fillStyle = '#ae8797';
            context.font = '18px Segoe UI, sans-serif';
            context.fillText('Una lectura simbólica de Entre Corazones · solo por diversión', 600, 545);

            return new Promise((resolve, reject) => {
                canvas.toBlob((blob) => {
                    if (blob) resolve(blob);
                    else reject(new Error('No se pudo generar la imagen de la tarjeta.'));
                }, 'image/png');
            });
        }

        function crearStickerCuadrado(data) {
            const canvas = document.createElement('canvas');
            canvas.width = 768;
            canvas.height = 768;
            const context = canvas.getContext('2d');
            if (!context) return Promise.reject(new Error('Este navegador no pudo crear el sticker.'));
            const gradient = context.createLinearGradient(0, 0, 768, 768);
            gradient.addColorStop(0, '#fff0f5');
            gradient.addColorStop(1, '#f7efff');
            context.fillStyle = gradient;
            context.fillRect(0, 0, 768, 768);
            context.fillStyle = '#fff';
            context.beginPath();
            context.roundRect(38, 38, 692, 692, 52);
            context.fill();
            context.textAlign = 'center';
            context.fillStyle = '#c84470';
            context.font = '100px serif';
            context.fillText(data.emoji || '💗', 384, 190);
            context.fillStyle = '#3c2b39';
            context.font = '600 42px Georgia, serif';
            context.fillText(String(data.titulo || 'Entre Corazones').slice(0, 29), 384, 290);
            if (Number.isInteger(data.porcentaje)) {
                context.fillStyle = '#b93664';
                context.font = '700 128px Georgia, serif';
                context.fillText(`${Math.max(0, Math.min(100, data.porcentaje))}%`, 384, 445);
            }
            context.fillStyle = '#766575';
            context.font = '26px Segoe UI, sans-serif';
            const summary = String(data.resumen || data.mensaje || 'Una lectura para conversar y reflexionar.').replace(/\s+/g, ' ');
            const lines = [];
            let line = '';
            summary.split(' ').forEach((word) => {
                const candidate = line ? `${line} ${word}` : word;
                if (context.measureText(candidate).width > 570 && line) { lines.push(line); line = word; }
                else line = candidate;
            });
            if (line) lines.push(line);
            lines.slice(0, 3).forEach((text, index) => context.fillText(text, 384, 520 + index * 36));
            context.font = '19px Segoe UI, sans-serif';
            context.fillText('Entre Corazones · lectura recreativa', 384, 680);
            return new Promise((resolve, reject) => {
                canvas.toBlob((blob) => blob ? resolve(blob) : reject(new Error('No se pudo generar el sticker.')), 'image/png');
            });
        }

        function appendResultList(parent, title, values, ordered = false) {
            if (!Array.isArray(values) || !values.length) return null;
            const block = makeElement('section', 'result-block');
            block.append(makeElement('h3', '', title));
            const list = makeElement(ordered ? 'ol' : 'ul');
            values.forEach((value) => list.append(makeElement('li', '', value)));
            block.append(list);
            parent.append(block);
            return block;
        }

        function appendMatchExtras(parent, data) {
            const wrappers = makeElement('div', 'flag-grid');
            const greens = appendResultList(wrappers, '💚 Green flags para explorar', data.green_flags);
            const reds = appendResultList(wrappers, '🚩 Señales para conversar', data.red_flags);
            if (greens || reds) parent.append(wrappers);
            appendResultList(parent, '💞 Apodos de la dupla', data.apodos);
            appendResultList(parent, '🗓️ Ideas de citas', data.planes_cita, true);
            if (Array.isArray(data.ranking)) {
                const ranking = makeElement('section', 'result-block');
                ranking.append(makeElement('h3', '', '🏆 Ranking simbólico'));
                const list = makeElement('ol', 'ranking-list');
                data.ranking.forEach((entry) => {
                    list.append(makeElement('li', 'ranking-item', `${entry.nombre}${entry.tipo ? ` · ${entry.tipo}` : ''} — ${entry.porcentaje}%`));
                });
                ranking.append(list);
                parent.append(ranking);
            }
            return { greens, reds };
        }

        function guardarCapsula(mode, data, months) {
            const dueAt = fechaEnMeses(new Date(), months);
            const capsule = {
                id: crypto.randomUUID(),
                mode,
                dueAt: `${dueAt.getFullYear()}-${String(dueAt.getMonth() + 1).padStart(2, '0')}-${String(dueAt.getDate()).padStart(2, '0')}`,
                createdAt: new Date().toISOString(),
                data: {
                    ...data,
                    green_flags: Array.isArray(data.green_flags) ? [...data.green_flags] : [],
                    red_flags: Array.isArray(data.red_flags) ? [...data.red_flags] : [],
                    apodos: Array.isArray(data.apodos) ? [...data.apodos] : [],
                    planes_cita: Array.isArray(data.planes_cita) ? [...data.planes_cita] : []
                }
            };
            capsules.unshift(capsule);
            if (saveLocalStorage(CAPSULE_STORAGE_KEY, JSON.stringify(capsules))) {
                renderCapsules();
                descargarRecordatorio(capsule);
                document.getElementById('capsule-title').textContent = `Cápsula guardada para el ${dueAt.toLocaleDateString('es')}`;
                document.getElementById('capsule-panel').open = true;
            }
        }

        function renderResult(mode, data) {
            result.replaceChildren();
            const top = makeElement('div', 'result-top');
            top.append(
                makeElement('span', 'result-emoji', data.emoji || (mode === 'tarot' ? '🔮' : '✨')),
                makeElement('div')
            );
            const heading = top.lastElementChild;
            heading.append(
                makeElement('h2', 'result-title', data.titulo || (data.porcentaje !== undefined ? 'Su resultado' : 'Tu lectura')),
                makeElement('p', 'result-summary', data.resumen || data.mensaje || '')
            );
            result.append(top);

            if (data.porcentaje !== undefined) {
                const scoreArea = makeElement('div', 'score-area');
                const scoreMain = makeElement('div', 'score-main');
                const scoreValue = makeElement('strong', 'score-value', '0%');
                scoreMain.append(
                    scoreValue,
                    makeElement('span', 'score-caption', 'afinidad simbólica')
                );
                scoreArea.append(scoreMain);
                if (data.dimensiones) {
                    const list = makeElement('div', 'score-list');
                    data.dimensiones.forEach((dimension) => {
                        const row = makeElement('div', 'score-row');
                        const track = makeElement('span', 'score-track');
                        const fill = makeElement('span', 'score-fill');
                        fill.style.width = `${dimension.valor}%`;
                        track.append(fill);
                        row.append(
                            makeElement('span', 'score-name', dimension.nombre),
                            track,
                            makeElement('span', 'score-number', `${dimension.valor}%`)
                        );
                        list.append(row);
                    });
                    scoreArea.append(list);
                } else {
                    scoreArea.style.gridTemplateColumns = '1fr';
                }
                result.append(scoreArea);
                animarPorcentaje(scoreValue, data.porcentaje);
                reproducirSonidoSuave();
                if (Number(data.porcentaje) >= 85) lanzarParticulas();
            }

            if (data.lecturas) {
                const list = makeElement('div', 'reading-list');
                data.lecturas.forEach((lectura) => {
                    const item = makeElement('article', 'reading-item');
                    item.append(makeElement('h3', '', lectura.titulo), makeElement('p', '', lectura.texto));
                    list.append(item);
                });
                result.append(list);
            }

            if (data.cartas) {
                const grid = makeElement('div', 'tarot-grid');
                data.cartas.forEach((carta) => {
                    const item = makeElement('article', 'tarot-card');
                    item.append(
                        makeElement('span', 'tarot-position', carta.posicion),
                        makeElement('span', 'tarot-icon', carta.emoji),
                        makeElement('h3', 'tarot-name', carta.nombre),
                        makeElement('p', 'tarot-key', carta.clave),
                        makeElement('p', 'tarot-message', carta.mensaje)
                    );
                    grid.append(item);
                });
                result.append(grid);
            }

            if (data.consejo) renderAdvice(result, data.consejo);
            const extrasBlocks = appendMatchExtras(result, data);
            let storyButton = null;
            let storyText = null;
            let rankingButton = null;
            let rankingComment = null;
            if (mode === 'random' && Array.isArray(data.nombres)) {
                const story = makeElement('section', 'result-block');
                story.append(makeElement('h3', '', '🎲 Historia sorpresa'));
                storyText = makeElement('p', 'result-summary', 'Pide una historia romántica y absurda generada por IA.');
                storyButton = makeElement('button', 'feature-button', 'Inventar historia con IA');
                storyButton.type = 'button';
                story.append(storyText, storyButton);
                result.append(story);
            }
            if (mode === 'ranking' && Array.isArray(data.ranking)) {
                const rankingExtra = makeElement('section', 'result-block');
                rankingExtra.append(makeElement('h3', '', '🤖 Lectura del ranking'));
                rankingComment = makeElement('p', 'result-summary', 'Pide a la IA una reflexión ligera sobre el orden simbólico.');
                rankingButton = makeElement('button', 'feature-button', 'Comentar ranking con IA');
                rankingButton.type = 'button';
                rankingExtra.append(rankingComment, rankingButton);
                result.append(rankingExtra);
            }

            const depthArea = makeElement('div', 'depth-area');
            const questionId = `depth-question-${mode}`;
            const questionLabel = makeElement('label', '', '¿Qué detalle te gustaría explorar? (opcional)');
            questionLabel.htmlFor = questionId;
            const questionInput = makeElement('textarea');
            questionInput.id = questionId;
            questionInput.maxLength = 500;
            questionInput.placeholder = 'Por ejemplo: ¿cómo puedo iniciar esa conversación?';
            questionInput.setAttribute('aria-label', questionLabel.textContent);
            depthArea.append(questionLabel, questionInput);
            const depthVibe = appendVibePicker(depthArea, `depth-vibe-${mode}`);
            const depthButton = makeElement('button', 'depth-button', '✦ Profundizar esta lectura con IA');
            depthButton.type = 'button';
            const depthAnswer = makeElement('div', 'depth-answer');
            depthAnswer.hidden = true;
            depthArea.append(depthButton, depthAnswer);
            result.append(depthArea);
            const actions = makeElement('div', 'result-actions');
            const shareButton = makeElement('button', 'share-button', '↗ Compartir resultado');
            shareButton.type = 'button';
            const imageButton = makeElement('button', 'share-image-button', '▧ Crear tarjeta');
            imageButton.type = 'button';
            const stickerButton = makeElement('button', 'share-image-button', '▣ Crear sticker cuadrado');
            stickerButton.type = 'button';
            const downloadCard = makeElement('a', 'download-card', 'Descargar PNG');
            downloadCard.download = 'entre-corazones.png';
            downloadCard.hidden = true;
            const downloadSticker = makeElement('a', 'download-card', 'Descargar sticker');
            downloadSticker.download = 'entre-corazones-sticker.png';
            downloadSticker.hidden = true;
            const whatsappLink = makeElement('a', 'whatsapp-link', 'Enviar por WhatsApp');
            whatsappLink.target = '_blank';
            whatsappLink.rel = 'noopener noreferrer';
            const shareStatus = makeElement('p', 'share-status');
            shareStatus.setAttribute('role', 'status');
            shareStatus.setAttribute('aria-live', 'polite');
            const updateShareLink = (interpretation = '') => {
                const text = textoParaCompartir(data, interpretation);
                whatsappLink.href = `https://wa.me/?text=${encodeURIComponent(text)}`;
                shareButton.onclick = async () => {
                    if (navigator.share) {
                        try {
                            await navigator.share({ title: data.titulo || 'Entre Corazones', text });
                        } catch (error) {
                            if (error.name !== 'AbortError') shareStatus.textContent = 'No se pudo abrir el menú de compartir. Puedes usar el enlace de WhatsApp.';
                        }
                        return;
                    }
                    try {
                        await navigator.clipboard.writeText(text);
                        shareStatus.textContent = 'Texto copiado. Ya puedes pegarlo en la app que prefieras.';
                    } catch (error) {
                        shareStatus.textContent = 'Usa “Enviar por WhatsApp” para compartir este resultado.';
                    }
                };
            };
            let cardUrl = null;
            let stickerUrl = null;
            imageButton.addEventListener('click', async () => {
                imageButton.disabled = true;
                imageButton.textContent = 'Creando tarjeta…';
                shareStatus.textContent = '';
                try {
                    const blob = await compartirTarjetaComoImagen(data);
                    if (cardUrl) URL.revokeObjectURL(cardUrl);
                    cardUrl = URL.createObjectURL(blob);
                    downloadCard.href = cardUrl;
                    downloadCard.hidden = false;
                    const file = new File([blob], 'entre-corazones.png', { type: 'image/png' });
                    if (navigator.canShare && navigator.canShare({ files: [file] })) {
                        await navigator.share({
                            files: [file],
                            title: data.titulo || 'Entre Corazones',
                            text: 'Mira mi resultado de Entre Corazones 💗'
                        });
                        shareStatus.textContent = 'Elige Instagram Stories, WhatsApp u otra app para compartir la tarjeta.';
                    } else {
                        downloadCard.click();
                        shareStatus.textContent = 'Tarjeta lista: se descargó el PNG. Puedes adjuntarlo a Instagram Stories o WhatsApp.';
                    }
                } catch (error) {
                    if (error.name !== 'AbortError') shareStatus.textContent = error.message || 'No se pudo crear la tarjeta. Inténtalo de nuevo.';
                } finally {
                    imageButton.disabled = false;
                    imageButton.textContent = '▧ Crear tarjeta';
                }
            });
            stickerButton.addEventListener('click', async () => {
                stickerButton.disabled = true;
                shareStatus.textContent = '';
                try {
                    const blob = await crearStickerCuadrado(data);
                    if (stickerUrl) URL.revokeObjectURL(stickerUrl);
                    stickerUrl = URL.createObjectURL(blob);
                    downloadSticker.href = stickerUrl;
                    downloadSticker.hidden = false;
                    downloadSticker.click();
                    shareStatus.textContent = 'Sticker cuadrado listo para guardar y enviar por WhatsApp o Instagram.';
                } catch (error) {
                    shareStatus.textContent = error.message || 'No se pudo crear el sticker.';
                } finally {
                    stickerButton.disabled = false;
                }
            });
            updateShareLink();
            if (storyButton) {
                storyButton.addEventListener('click', async () => {
                    storyButton.disabled = true;
                    storyButton.textContent = 'Inventando una historia…';
                    try {
                        const response = await fetch('/api/historia-aleatoria', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ nombres: data.nombres })
                        });
                        const answer = await response.json();
                        if (!response.ok) throw new Error(answer.error || 'No se pudo inventar la historia.');
                        storyText.textContent = answer.historia;
                        data.resumen = answer.historia;
                        const historyEntry = resultHistory.find((entry) => entry.mode === mode && entry.data === data);
                        if (historyEntry) saveResultHistory();
                        updateShareLink();
                        shareStatus.textContent = 'Historia generada. Puedes compartirla o guardarla en tu cápsula.';
                    } catch (error) {
                        shareStatus.textContent = error.message || 'No se pudo inventar la historia.';
                    } finally {
                        storyButton.disabled = false;
                        storyButton.textContent = 'Inventar otra historia';
                    }
                });
            }
            if (rankingButton) {
                rankingButton.addEventListener('click', async () => {
                    rankingButton.disabled = true;
                    rankingButton.textContent = 'Leyendo el ranking…';
                    try {
                        const response = await fetch('/api/idea-ranking', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ ranking: data.ranking })
                        });
                        const answer = await response.json();
                        if (!response.ok) throw new Error(answer.error || 'No se pudo comentar el ranking.');
                        rankingComment.textContent = answer.comentario;
                        shareStatus.textContent = 'La reflexión incluye los nombres del ranking y se generó con IA.';
                        data.comentario_ia = answer.comentario;
                        const historyEntry = resultHistory.find((entry) => entry.mode === mode && entry.data === data);
                        if (historyEntry) saveResultHistory();
                    } catch (error) {
                        shareStatus.textContent = error.message || 'No se pudo comentar el ranking.';
                    } finally {
                        rankingButton.disabled = false;
                        rankingButton.textContent = 'Comentar ranking con IA';
                    }
                });
            }
            const capsulePeriod = makeElement('select');
            capsulePeriod.setAttribute('aria-label', 'Cuándo volver a leer la cápsula');
            [['6', 'En 6 meses'], ['12', 'En 1 año']].forEach(([value, label]) => {
                const option = makeElement('option', '', label);
                option.value = value;
                capsulePeriod.append(option);
            });
            const capsuleButton = makeElement('button', 'share-button', '⏳ Guardar cápsula');
            capsuleButton.type = 'button';
            capsuleButton.addEventListener('click', () => guardarCapsula(mode, data, Number(capsulePeriod.value)));
            const capsuleControls = makeElement('div', 'capsule-controls');
            capsuleControls.append(capsulePeriod, capsuleButton);
            const feedbackButtons = makeElement('div', 'community-votes');
            [['👍 Me gustó', 1], ['👎 No me gustó', -1]].forEach(([label, rating]) => {
                const button = makeElement('button', 'vote-button', label);
                button.type = 'button';
                button.addEventListener('click', async () => {
                    button.disabled = true;
                    try {
                        const response = await fetch('/api/feedback', {
                            method: 'POST', headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ modo: mode, rating })
                        });
                        const body = await response.json();
                        if (!response.ok) throw new Error(body.error || 'No se pudo guardar la valoración.');
                        shareStatus.textContent = 'Gracias por tu opinión.';
                        feedbackButtons.querySelectorAll('button').forEach((item) => { item.disabled = true; });
                    } catch (error) {
                        shareStatus.textContent = error.message || 'No se pudo guardar la valoración.';
                        button.disabled = false;
                    }
                });
                feedbackButtons.append(button);
            });
            const ideasButton = makeElement('button', 'share-button', '✦ Pedir ideas extra a la IA');
            ideasButton.type = 'button';
            ideasButton.addEventListener('click', async () => {
                ideasButton.disabled = true;
                ideasButton.textContent = 'Consultando ideas…';
                try {
                    const response = await fetch('/api/ideas-ia', {
                        method: 'POST', headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ modo: mode, resultado: data })
                    });
                    const extra = await response.json();
                    if (!response.ok) throw new Error(extra.error || 'No se pudieron generar las ideas.');
                    Object.assign(data, extra);
                    extrasBlocks.greens?.remove();
                    extrasBlocks.reds?.remove();
                    result.querySelectorAll('.result-block').forEach((block) => {
                        if (['💞 Apodos de la dupla', '🗓️ Ideas de citas'].includes(block.querySelector('h3')?.textContent)) block.remove();
                    });
                    appendMatchExtras(result, data);
                    updateShareLink();
                    shareStatus.textContent = 'Actualizamos tus señales, apodos e ideas de citas con ayuda de la IA.';
                } catch (error) {
                    shareStatus.textContent = error.message || 'No se pudieron generar las ideas.';
                } finally {
                    ideasButton.disabled = false;
                    ideasButton.textContent = '✦ Pedir ideas extra a la IA';
                }
            });
            const speakButton = makeElement('button', 'share-button speech-button', '🔊 Escuchar resultado');
            speakButton.type = 'button';
            speakButton.addEventListener('click', () => {
                if (!('speechSynthesis' in window)) {
                    shareStatus.textContent = 'Este navegador no ofrece lectura de voz.';
                    return;
                }
                window.speechSynthesis.cancel();
                const speech = new SpeechSynthesisUtterance(`${data.titulo || 'Resultado'}. ${data.resumen || data.mensaje || ''} ${data.consejo || ''}`);
                speech.lang = 'es';
                window.speechSynthesis.speak(speech);
            });
            actions.append(shareButton, imageButton, downloadCard, stickerButton, downloadSticker, whatsappLink, ideasButton, capsuleControls, feedbackButtons, speakButton, shareStatus);
            result.append(actions);
            depthButton.addEventListener('click', async () => {
                depthButton.disabled = true;
                depthButton.textContent = 'Preparando una respuesta personal…';
                depthAnswer.hidden = true;
                feedback.hidden = true;
                try {
                    const response = await fetch('/api/profundizar', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            modo: mode,
                            resultado: data,
                            pregunta: questionInput.value.trim(),
                            vibe: depthVibe.value
                        })
                    });
                    const answer = await response.json();
                    if (!response.ok) throw new Error(answer.error || 'No se pudo profundizar la lectura.');
                    depthAnswer.textContent = answer.interpretacion;
                    depthAnswer.hidden = false;
                    updateShareLink(answer.interpretacion);
                } catch (error) {
                    feedback.textContent = error.message || 'Hubo un problema de conexión. Inténtalo de nuevo.';
                    feedback.hidden = false;
                } finally {
                    depthButton.disabled = false;
                    depthButton.textContent = '✦ Profundizar esta lectura con IA';
                }
            });
            result.hidden = false;
        }

        forms.forEach((form) => {
            form.addEventListener('submit', async (event) => {
                event.preventDefault();
                const mode = currentMode();
                const button = form.querySelector('.submit-button');
                const originalLabel = button.textContent;
                const payload = Object.fromEntries(new FormData(form).entries());
                if (mode === 'celebrity') {
                    payload.opciones = [...form.querySelectorAll('input[name="opciones"]:checked')].map((input) => input.value);
                }
                if (mode === 'ranking') {
                    payload.opciones = [1, 2, 3, 4].map((index) => document.getElementById(`ranking-option${index}`).value.trim()).filter(Boolean);
                }
                feedback.hidden = true;
                result.hidden = true;
                button.disabled = true;
                button.classList.add('is-loading');
                button.textContent = 'Preparando tu lectura…';

                try {
                    const response = await fetch(modes[mode].endpoint, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(payload)
                    });
                    const data = await response.json();
                    if (!response.ok) throw new Error(data.error || 'No se pudo preparar la lectura.');
                    resultHistory.unshift({
                        id: crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random()}`,
                        mode,
                        data,
                        createdAt: new Date().toISOString()
                    });
                    saveResultHistory();
                    renderResult(mode, data);
                    result.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                } catch (error) {
                    feedback.textContent = error.message || 'Hubo un problema de conexión. Inténtalo de nuevo.';
                    feedback.hidden = false;
                } finally {
                    button.disabled = false;
                    button.classList.remove('is-loading');
                    button.textContent = originalLabel;
                }
            });
        });

        chatForm.addEventListener('submit', async (event) => {
            event.preventDefault();
            const content = chatInput.value.trim();
            if (!content) return;
            const conversation = [...chatHistory, { role: 'user', content }];
            chatHistory = conversation.slice(-CHAT_HISTORY_LIMIT);
            renderChatHistory();
            saveChatHistory();
            chatInput.value = '';
            chatInput.focus();
            chatSend.disabled = true;
            chatSend.classList.add('is-loading');
            chatStatus.textContent = 'Pensando una respuesta…';
            try {
                const response = await fetch('/api/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        mensajes: conversation.slice(-12),
                        vibe: chatVibe.value,
                        stream: true
                    })
                });
                if (!response.ok) {
                    const data = await response.json();
                    throw new Error(data.error || 'No pudimos responder ahora.');
                }
                if (!response.body) throw new Error('Este navegador no permite recibir respuestas en streaming.');
                const replyBubble = makeElement('div', 'chat-bubble assistant');
                replyBubble.setAttribute('aria-label', 'Respuesta de Entre Corazones');
                chatMessages.append(replyBubble);
                let reply = '';
                await leerEventosChat(response, (delta) => {
                    reply += delta;
                    replyBubble.textContent = reply;
                    chatMessages.scrollTop = chatMessages.scrollHeight;
                });
                if (!reply.trim()) throw new Error('La IA no generó una respuesta. Inténtalo de nuevo.');
                chatHistory.push({ role: 'assistant', content: reply });
                chatHistory = chatHistory.slice(-CHAT_HISTORY_LIMIT);
                saveChatHistory();
                chatStatus.textContent = '';
                renderChatHistory();
            } catch (error) {
                chatStatus.textContent = error.message || 'Hubo un problema de conexión. Inténtalo de nuevo.';
            } finally {
                chatSend.disabled = false;
                chatSend.classList.remove('is-loading');
                chatInput.focus();
            }
        });

        document.getElementById('clear-chat').addEventListener('click', () => {
            try {
                localStorage.removeItem(CHAT_STORAGE_KEY);
            } catch (error) {
                chatStatus.textContent = 'El navegador no permitió borrar el historial guardado.';
                return;
            }
            chatHistory = [];
            chatStatus.textContent = 'Conversación borrada de este navegador.';
            renderChatHistory();
        });
