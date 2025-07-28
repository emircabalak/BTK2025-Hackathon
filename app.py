import os
import json
import requests
from flask import Flask, request, jsonify, render_template_string
from dotenv import load_dotenv

app = Flask(__name__)
load_dotenv()

API_KEY = os.getenv("GOOGLE_API_KEY", "")
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={API_KEY}"

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Münazara Arenası</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
    <style>
        @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
        .animate-fade-in { animation: fadeIn 0.5s ease-out forwards; }
        .animate-pulse { animation: pulse 1.5s cubic-bezier(0.4, 0, 0.6, 1) infinite; }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }
        body { font-family: 'Inter', sans-serif; }
        #schema-container svg {
            width: 100%;
            height: auto;
        }
    </style>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap" rel="stylesheet">
</head>
<body class="bg-gray-900 text-white">

    <div class="min-h-screen flex flex-col items-center justify-center p-4">
        <div id="app-container" class="w-full max-w-2xl mx-auto bg-gray-800 rounded-2xl shadow-2xl flex flex-col" style="height: 90vh;">
            <header class="p-4 border-b border-gray-700 flex items-center space-x-3">
                <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-cyan-400"><path d="M12 2a2.5 2.5 0 0 1 2.5 2.5v.75a2.5 2.5 0 0 1-5 0v-.75A2.5 2.5 0 0 1 12 2Z"/><path d="M4.5 9.5A2.5 2.5 0 0 0 7 12v0a2.5 2.5 0 0 0-2.5 2.5v0A2.5 2.5 0 0 0 7 17v0a2.5 2.5 0 0 0-2.5 2.5v0"/><path d="M19.5 9.5A2.5 2.5 0 0 1 17 12v0a2.5 2.5 0 0 1 2.5 2.5v0A2.5 2.5 0 0 1 17 17v0a2.5 2.5 0 0 1 2.5 2.5v0"/><path d="M12 12a2.5 2.5 0 0 0-2.5-2.5v0A2.5 2.5 0 0 0 7 7v0"/><path d="M12 12a2.5 2.5 0 0 1 2.5-2.5v0A2.5 2.5 0 0 1 17 7v0"/><path d="M12 12a2.5 2.5 0 0 0-2.5 2.5v0A2.5 2.5 0 0 0 7 17v0"/><path d="M12 12a2.5 2.5 0 0 1 2.5 2.5v0A2.5 2.5 0 0 1 17 17v0"/><path d="M12 4.75v3.5"/><path d="M7 9.5h10"/><path d="M7 14.5h10"/><path d="M12 17.25v3.5"/></svg>
                <div>
                    <h1 class="text-xl font-bold text-white">Münazara Arenası</h1>
                    <p class="text-sm text-gray-400">Python & Flask Versiyonu</p>
                </div>
            </header>
            
            <main class="flex-grow p-6 overflow-y-auto">
                <div id="topic-screen" class="flex flex-col h-full justify-center animate-fade-in">
                    <div class="space-y-6">
                        <div>
                            <label for="topic-select" class="block text-sm font-medium text-gray-300 mb-2">1. Bir Münazara Konusu Seçin</label>
                            <select id="topic-select" class="w-full p-3 bg-gray-700 border border-gray-600 rounded-lg focus:ring-2 focus:ring-cyan-500 focus:border-cyan-500 transition">
                                <option value="" disabled selected>Konu seç...</option>
                                <option value="Yapay zeka insanlık için bir tehdit mi?">Yapay zeka insanlık için bir tehdit mi?</option>
                                <option value="Üniversite eğitimi herkes için ücretsiz mi olmalı?">Üniversite eğitimi herkes için ücretsiz mi olmalı?</option>
                                <option value="Sosyal medya toplumu olumlu yönde mi etkiliyor?">Sosyal medya toplumu olumlu yönde mi etkiliyor?</option>
                                <option value="custom">Kendi konumu yazmak istiyorum...</option>
                            </select>
                        </div>
                        <div id="custom-topic-container" class="hidden">
                            <input type="text" id="custom-topic-input" placeholder="Münazara konunuzu buraya yazın" class="w-full p-3 bg-gray-700 border border-gray-600 rounded-lg focus:ring-2 focus:ring-cyan-500 focus:border-cyan-500 transition" />
                        </div>
                        <div>
                            <h3 class="block text-sm font-medium text-gray-300 mb-2">2. Tarafınızı Belirleyin</h3>
                            <div class="grid grid-cols-2 gap-4">
                                <button data-action="set-stance" data-stance="savunuyorum" class="p-4 rounded-lg text-center transition bg-gray-700 hover:bg-gray-600">Savunuyorum</button>
                                <button data-action="set-stance" data-stance="karşı çıkıyorum" class="p-4 rounded-lg text-center transition bg-gray-700 hover:bg-gray-600">Karşı Çıkıyorum</button>
                            </div>
                        </div>
                        <p id="error-message" class="text-red-400 text-sm text-center"></p>
                        <button data-action="start-debate" id="start-debate-btn" class="w-full p-4 bg-cyan-600 hover:bg-cyan-700 rounded-lg font-bold text-lg transition disabled:bg-gray-600 disabled:cursor-not-allowed" disabled>
                            Münazarayı Başlat
                        </button>
                    </div>
                </div>

                <div id="debate-screen" class="hidden flex flex-col h-full">
                    <div class="p-4 border-b border-gray-700 bg-gray-800/80 backdrop-blur-sm -mx-6 -mt-6 mb-4 sticky top-0 z-10">
                        <h3 id="debate-topic-header" class="text-center font-semibold text-gray-300">Konu: <span class="text-cyan-400"></span></h3>
                    </div>
                    <div id="messages-container" class="flex-grow overflow-y-auto pr-4 -mr-4 space-y-6">
                    </div>
                    <div class="mt-4 pt-4 border-t border-gray-700">
                        <div class="flex items-center space-x-2">
                            <input type="text" id="message-input" placeholder="Argümanınızı yazın..." class="flex-grow p-3 bg-gray-700 border border-gray-600 rounded-lg focus:ring-2 focus:ring-cyan-500 focus:border-cyan-500 transition" />
                            <button data-action="send-message" id="send-btn" class="p-3 bg-cyan-600 hover:bg-cyan-700 rounded-lg transition disabled:bg-gray-600">
                                <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="pointer-events-none"><path d="m22 2-7 20-4-9-9-4Z"/><path d="M22 2 11 13"/></svg>
                            </button>
                        </div>
                        <button data-action="end-debate" id="end-debate-btn" class="w-full mt-3 p-3 bg-red-600 hover:bg-red-700 rounded-lg font-bold transition disabled:bg-gray-600">
                            Münazarayı Bitir ve Rapor Al
                        </button>
                    </div>
                </div>

                <div id="report-screen" class="hidden flex flex-col h-full justify-center animate-fade-in">
                </div>
                
                <div id="schema-screen" class="hidden flex flex-col h-full">
                    <h2 class="text-2xl font-bold text-center text-cyan-400 mb-4">Argüman Haritası</h2>
                    <div id="schema-container" class="flex-grow bg-gray-900 p-4 rounded-lg overflow-auto">
                    </div>
                    <div class="mt-4">
                        <button data-action="back-to-report" class="w-full p-3 bg-cyan-600 hover:bg-cyan-700 rounded-lg font-bold transition">Rapora Geri Dön</button>
                    </div>
                </div>
            </main>
        </div>
    </div>
    
    <div id="pdf-render-container" style="position: absolute; top: 0; left: -9999px; background-color: #111827; padding: 20px;"></div>

    <script>
        document.addEventListener('DOMContentLoaded', () => {
            const state = {
                topic: '',
                stance: '',
                messages: []
            };

            const screens = {
                topic: document.getElementById('topic-screen'),
                debate: document.getElementById('debate-screen'),
                report: document.getElementById('report-screen'),
                schema: document.getElementById('schema-screen')
            };
            const topicSelect = document.getElementById('topic-select');
            const customTopicContainer = document.getElementById('custom-topic-container');
            const customTopicInput = document.getElementById('custom-topic-input');
            const startDebateBtn = document.getElementById('start-debate-btn');
            const errorMessage = document.getElementById('error-message');
            const debateTopicHeader = document.getElementById('debate-topic-header').querySelector('span');
            const messagesContainer = document.getElementById('messages-container');
            const messageInput = document.getElementById('message-input');
            
            function showScreen(screenName) {
                Object.values(screens).forEach(s => s.classList.add('hidden'));
                screens[screenName].classList.remove('hidden');
            }

            function updateMessages() {
                if (!messagesContainer) return;
                messagesContainer.innerHTML = state.messages.map(msg => `
                    <div class="flex items-start gap-3 animate-fade-in ${msg.author === 'user' ? 'justify-end' : 'justify-start'}">
                        ${msg.author === 'ai' ? '<div class="flex-shrink-0 w-8 h-8 rounded-full bg-gray-700 flex items-center justify-center"><svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-cyan-400"><path d="M12 8V4H8"/><rect width="16" height="12" x="4" y="8" rx="2"/><path d="M2 14h2"/><path d="M20 14h2"/><path d="M15 13v2"/><path d="M9 13v2"/></svg></div>' : ''}
                        <div class="max-w-md p-3 rounded-xl ${msg.author === 'user' ? 'bg-cyan-600 text-white rounded-br-none' : 'bg-gray-700 text-gray-200 rounded-bl-none'}">
                            <p class="text-sm" style="white-space: pre-wrap;">${msg.text}</p>
                        </div>
                        ${msg.author === 'user' ? '<div class="flex-shrink-0 w-8 h-8 rounded-full bg-gray-700 flex items-center justify-center"><svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-gray-300"><path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg></div>' : ''}
                    </div>
                `).join('');
                messagesContainer.scrollTop = messagesContainer.scrollHeight;
            }

            function addMessage(author, text) {
                state.messages.push({ author, text });
                updateMessages();
            }

            function setLoading(isLoading, message = '') {
                document.querySelectorAll('[data-action]').forEach(el => el.disabled = isLoading);
                if(messageInput) messageInput.disabled = isLoading;

                let loadingEl = document.getElementById('loading-indicator');
                if (isLoading) {
                    if (!loadingEl) {
                        loadingEl = document.createElement('div');
                        loadingEl.id = 'loading-indicator';
                        loadingEl.innerHTML = `
                            <div class="flex items-start gap-3 justify-start">
                                <div class="flex-shrink-0 w-8 h-8 rounded-full bg-gray-700 flex items-center justify-center"><svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-cyan-400"><path d="M12 8V4H8"/><rect width="16" height="12" x="4" y="8" rx="2"/><path d="M2 14h2"/><path d="M20 14h2"/><path d="M15 13v2"/><path d="M9 13v2"/></svg></div>
                                <div class="max-w-md p-3 rounded-xl bg-gray-700 text-gray-200 rounded-bl-none">
                                    <div class="flex items-center space-x-2"><div class="w-2 h-2 bg-cyan-400 rounded-full animate-pulse"></div><div class="w-2 h-2 bg-cyan-400 rounded-full animate-pulse" style="animation-delay: 0.2s"></div><div class="w-2 h-2 bg-cyan-400 rounded-full animate-pulse" style="animation-delay: 0.4s"></div></div>
                                    ${message ? `<p class="text-sm ml-2">${message}</p>` : ''}
                                </div>
                            </div>`;
                        messagesContainer.appendChild(loadingEl);
                        messagesContainer.scrollTop = messagesContainer.scrollHeight;
                    }
                } else {
                    if (loadingEl) loadingEl.remove();
                }
            }

            function renderReportScreen(report) {
                const score = report.iknaEdicilikPuani || 0;
                screens.report.innerHTML = `
                    <div id="report-content" class="space-y-6">
                        <h2 class="text-3xl font-bold text-center text-cyan-400">Performans Raporu</h2>
                        <div class="relative flex justify-center items-center">
                            <svg class="transform -rotate-90" width="120" height="120" viewBox="0 0 120 120">
                                <circle cx="60" cy="60" r="54" fill="none" stroke="#374151" stroke-width="12" />
                                <circle cx="60" cy="60" r="54" fill="none" stroke="#22d3ee" stroke-width="12" pathLength="1" stroke-dasharray="1" stroke-dashoffset="${1 - (score / 10)}" />
                            </svg>
                            <span class="absolute text-3xl font-bold">${score}<span class="text-lg">/10</span></span>
                        </div>
                        <p class="text-center text-lg font-semibold text-gray-300">İkna Edicilik Puanı</p>
                        <div class="space-y-4">
                            <div class="p-4 bg-gray-700 rounded-lg">
                                <h3 class="font-semibold text-green-400 mb-2">En Güçlü Argümanınız</h3>
                                <p class="text-sm text-gray-300">${report.enGucluArguman || 'Belirlenemedi.'}</p>
                            </div>
                            <div class="p-4 bg-gray-700 rounded-lg">
                                <h3 class="font-semibold text-yellow-400 mb-2">Geliştirilmesi Gereken Nokta: ${report.gelistirilmesiGerekenNokta?.tespitEdilenHataTuru || 'Genel'}</h3>
                                <p class="text-sm text-gray-400 mt-1 mb-2"><em>${report.gelistirilmesiGerekenNokta?.hataTanimi || ''}</em></p>
                                <p class="text-sm text-gray-300 border-l-4 border-yellow-400 pl-3"><strong>Örnek Cümleniz:</strong> "${report.gelistirilmesiGerekenNokta?.ornekCumle || 'Belirlenemedi.'}"</p>
                                <p class="text-sm text-gray-300 mt-2"><strong>Öneri:</strong> ${report.gelistirilmesiGerekenNokta?.onerilenGelistirme || 'Daha net ve kanıta dayalı argümanlar sunmaya çalışın.'}</p>
                            </div>
                            <div class="p-4 bg-gray-700 rounded-lg">
                                <h3 class="font-semibold text-indigo-400 mb-2">Kanıt Kullanımı ve Destekleme</h3>
                                <p class="text-sm text-gray-300">${report.kanitKullanimi || 'Argümanlarınızı daha fazla veri veya örnekle destekleyebilirsiniz.'}</p>
                            </div>
                            <div class="p-4 bg-gray-700 rounded-lg">
                                <h3 class="font-semibold text-cyan-400 mb-2">Genel Yorum</h3>
                                <p class="text-sm text-gray-300">${report.genelYorum || 'Belirlenemedi.'}</p>
                            </div>
                        </div>
                    </div>
                    <div class="mt-6 space-y-3">
                        <button data-action="draw-schema" class="w-full p-3 bg-teal-600 hover:bg-teal-700 rounded-lg font-bold transition">Argüman Haritasını Çiz</button>
                        <button data-action="download-pdf" class="w-full p-3 bg-indigo-600 hover:bg-indigo-700 rounded-lg font-bold transition">Raporu ve Haritayı İndir</button>
                        <button data-action="new-debate" class="w-full p-3 bg-cyan-600 hover:bg-cyan-700 rounded-lg font-bold transition">Yeni Münazara Başlat</button>
                    </div>
                `;
            }

            function checkCanStart() {
                const finalTopic = topicSelect.value === 'custom' ? customTopicInput.value.trim() : topicSelect.value;
                startDebateBtn.disabled = !finalTopic || !state.stance;
            }

            async function handleAction(event) {
                const target = event.target.closest('[data-action]');
                if (!target || target.disabled) return;

                const action = target.dataset.action;

                if (action === 'set-stance') {
                    state.stance = target.dataset.stance;
                    document.querySelectorAll('[data-action="set-stance"]').forEach(btn => btn.classList.remove('bg-green-600', 'ring-2', 'ring-green-400', 'bg-red-600', 'ring-red-400'));
                    target.classList.add(state.stance === 'savunuyorum' ? 'bg-green-600' : 'bg-red-600', 'ring-2', state.stance === 'savunuyorum' ? 'ring-green-400' : 'ring-red-400');
                    checkCanStart();
                }

                if (action === 'start-debate') {
                    const finalTopic = topicSelect.value === 'custom' ? customTopicInput.value.trim() : topicSelect.value;
                    if (!finalTopic || !state.stance) {
                        errorMessage.textContent = 'Lütfen bir konu ve taraf seçin.';
                        return;
                    }
                    state.topic = finalTopic;
                    state.messages = [];
                    debateTopicHeader.textContent = state.topic;
                    updateMessages();
                    showScreen('debate');
                }

                if (action === 'send-message') {
                    const text = messageInput.value.trim();
                    if (!text) return;
                    addMessage('user', text);
                    messageInput.value = '';
                    setLoading(true);
                    try {
                        const response = await fetch('/api/debate', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(state) });
                        const data = await response.json();
                        if (!response.ok) throw new Error(data.error || 'Sunucudan bilinmeyen bir hata alındı.');
                        addMessage('ai', data.reply);
                    } catch (error) {
                        addMessage('ai', `Mesaj gönderilemedi: ${error.message}`);
                    } finally {
                        setLoading(false);
                    }
                }

                if (action === 'end-debate') {
                    setLoading(true);
                    try {
                        const response = await fetch('/api/report', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(state) });
                        const report = await response.json();
                        if (!response.ok) throw new Error(report.error || 'Sunucudan bilinmeyen bir hata alındı.');
                        renderReportScreen(report);
                        showScreen('report');
                    } catch (error) {
                         addMessage('ai', `Rapor oluşturulamadı: ${error.message}`);
                    } finally {
                        setLoading(false);
                    }
                }

                if (action === 'new-debate') {
                    showScreen('topic');
                }
                
                if (action === 'back-to-report') {
                    showScreen('report');
                }

                if (action === 'draw-schema') {
                    setLoading(true);
                    const schemaContainer = document.getElementById('schema-container');
                    let schemaData = '';
                    try {
                        const response = await fetch('/api/schema', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(state) });
                        const data = await response.json();
                        if (!response.ok) throw new Error(data.error || 'Şema verisi sunucudan alınamadı.');
                        
                        schemaData = data.schema;
                        if (!schemaData || !schemaData.trim().startsWith('graph')) {
                           throw new Error("Yapay zeka geçerli bir şema formatı döndürmedi.");
                        }
                        
                        const { svg } = await mermaid.render('mermaid-graph', schemaData);
                        schemaContainer.innerHTML = svg;
                        const svgElement = schemaContainer.querySelector('svg');
                        if (svgElement) {
                            svgElement.style.width = '100%';
                            svgElement.style.height = 'auto';
                        }

                        showScreen('schema');
                    } catch (error) {
                         console.error("Mermaid render error:", error);
                         schemaContainer.innerHTML = `
                            <p class="text-yellow-400 mb-2">Argüman haritası çizilirken bir hata oluştu.</p>
                            <p class="text-gray-400 text-sm mb-2">Hata Detayı: ${error.message}</p>
                            <p class="text-gray-400 text-sm mb-2 mt-4">Alınan Ham Veri:</p>
                            <pre class="bg-black p-4 rounded text-white text-sm whitespace-pre-wrap">${schemaData || '(Sunucudan veri alınamadı veya veri boş.)'}</pre>
                         `;
                         showScreen('schema');
                    } finally {
                        setLoading(false);
                    }
                }

                if (action === 'download-pdf') {
                    setLoading(true, 'PDF oluşturuluyor...');
                    try {
                        const { jsPDF } = window.jspdf;
                        const pdf = new jsPDF({ orientation: 'p', unit: 'mm', format: 'a4' });

                        const reportContent = document.getElementById('report-content');
                        const reportCanvas = await html2canvas(reportContent, { backgroundColor: '#1f2937', scale: 2 });
                        const reportImgData = reportCanvas.toDataURL('image/png');
                        const pdfWidth = pdf.internal.pageSize.getWidth();
                        const reportImgProps = pdf.getImageProperties(reportImgData);
                        const reportImgHeight = (reportImgProps.height * pdfWidth) / reportImgProps.width;
                        pdf.addImage(reportImgData, 'PNG', 0, 0, pdfWidth, reportImgHeight);

                        const schemaResponse = await fetch('/api/schema', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(state) });
                        const schemaData = await schemaResponse.json();
                        if (!schemaResponse.ok) throw new Error(schemaData.error || 'Şema verisi alınamadı.');

                        const renderContainer = document.getElementById('pdf-render-container');
                        
                        const { svg } = await mermaid.render('temp-mermaid-graph-id', schemaData.schema);
                        renderContainer.innerHTML = svg;
                        
                        await new Promise(resolve => requestAnimationFrame(resolve));

                        const schemaCanvas = await html2canvas(renderContainer, { backgroundColor: '#111827', scale: 2 });
                        const schemaImgData = schemaCanvas.toDataURL('image/png');
                        const schemaImgProps = pdf.getImageProperties(schemaImgData);
                        const schemaImgHeight = (schemaImgProps.height * pdfWidth) / schemaImgProps.width;

                        pdf.addPage();
                        pdf.addImage(schemaImgData, 'PNG', 0, 0, pdfWidth, schemaImgHeight);
                        
                        renderContainer.innerHTML = '';
                        pdf.save('munazara-raporu-ve-harita.pdf');

                    } catch (error) {
                        console.error("PDF Oluşturma Hatası:", error);
                        const errorMessage = error instanceof Error ? error.message : String(error);
                        alert(`PDF oluşturulurken bir hata oluştu: ${errorMessage}`);
                    } finally {
                        setLoading(false);
                    }
                }
            }

            mermaid.initialize({ startOnLoad: false, theme: 'dark' });
            document.body.addEventListener('click', handleAction);
            topicSelect.addEventListener('change', () => {
                customTopicContainer.classList.toggle('hidden', topicSelect.value !== 'custom');
                checkCanStart();
            });
            customTopicInput.addEventListener('input', checkCanStart);
            messageInput.addEventListener('keypress', e => {
                if (e.key === 'Enter' && !document.querySelector('[data-action="send-message"]').disabled) {
                    handleAction({ target: document.querySelector('[data-action="send-message"]') });
                }
            });
            
            showScreen('topic');
        });
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/debate', methods=['POST'])
def handle_debate():
    try:
        data = request.json
        if not data:
            return jsonify({"error": "Geçersiz istek: JSON verisi bulunamadı."}), 400
            
        topic = data.get('topic')
        stance = data.get('stance')
        messages = data.get('messages', [])

        conversation_history = "\\n".join([f"{'Kullanıcı' if m['author'] == 'user' else 'AI Münazır'}: {m['text']}" for m in messages])

        system_prompt = f"""Sen, 'Münazara Arenası' platformunun yapay zeka münazırısın. Görevin, kullanıcıyla seçilen bir konu üzerinde mantık ve kanıta dayalı bir münazara yapmaktır.
    Kuralların:
    1. Her zaman saygılı, objektif ve tarafsız bir dil kullan.
    2. Kullanıcının argümanlarını dikkatle analiz et ve doğrudan bu argümanlara cevap ver.
    3. Kendi argümanlarını desteklemek için genel bilgi veya mantıksal çıkarımlar kullan. Rolünü oyna.
    4. Cevapların net ve anlaşılır olsun.

    Şu anki konumuz: "{topic}". Kullanıcı bu konuda "{stance}" tarafını savunuyor. Sen ise karşı tarafı savunacaksın. Sohbet geçmişini dikkate alarak sadece sıradaki cevabını ver."""
        
        full_prompt = f"{system_prompt}\\n\\n---SOHBET GEÇMİŞİ---\\n{conversation_history}\\n\\nAI Münazır'ın sıradaki cevabı:"

        payload = {
            "contents": [{"role": "user", "parts": [{"text": full_prompt}]}]
        }
        
        response = requests.post(GEMINI_API_URL, json=payload)
        response.raise_for_status()
        result = response.json()
        reply = result['candidates'][0]['content']['parts'][0]['text']
        return jsonify({"reply": reply})

    except requests.exceptions.HTTPError as http_err:
        error_info = http_err.response.json()
        return jsonify({"error": f"API Hatası: {error_info.get('error', {}).get('message', 'Bilinmeyen API hatası')}"}), http_err.response.status_code
    except Exception as e:
        return jsonify({"error": f"Sunucuda beklenmedik bir hata oluştu: {str(e)}"}), 500


@app.route('/api/report', methods=['POST'])
def handle_report():
    try:
        data = request.json
        if not data:
            return jsonify({"error": "Geçersiz istek: JSON verisi bulunamadı."}), 400

        messages = data.get('messages', [])
        conversation_history = "\\n".join([f"{'Kullanıcı' if m['author'] == 'user' else 'AI Münazır'}: {m['text']}" for m in messages])

        report_prompt = f"""Aşağıda bir kullanıcı ile senin aranda geçen münazaranın tam metni bulunmaktadır. Bu metni bir münazara eğitmeni gibi çok detaylı analiz et ve aşağıdaki kriterlere göre bir performans raporu oluştur. Çıktıyı mutlaka geçerli bir JSON formatında ver. JSON formatını ```json ... ``` bloğu içine alma.

    Münazara Metni:
    \"\"\"
    {conversation_history}
    \"\"\"

    JSON Formatında İstenen Rapor Şeması:
    {{
      "enGucluArguman": "Kullanıcının sunduğu en güçlü, en mantıklı ve ikna edici argümanı buraya özetle.",
      "gelistirilmesiGerekenNokta": {{
        "tespitEdilenHataTuru": "Kullanıcının yaptığı en belirgin mantık hatasının adını yaz (Örn: 'Korkuluk Safsatası (Straw Man)', 'Aceleci Genelleme'). Eğer belirgin bir hata yoksa 'Genel Argüman Zayıflığı' yaz.",
        "hataTanimi": "Tespit ettiğin mantık hatasının ne anlama geldiğini bir cümleyle açıkla.",
        "ornekCumle": "Kullanıcının hangi cümlesinin bu hataya yol açtığını tam olarak alıntıla.",
        "onerilenGelistirme": "Kullanıcının bu hatayı nasıl düzeltebileceğine veya argümanını nasıl daha güçlü hale getirebileceğine dair somut bir tavsiye ver."
      }},
      "kanitKullanimi": "Kullanıcının argümanlarını ne kadar kanıt, veri veya örnekle desteklediğini değerlendir. (Örn: 'Argümanlar genel olarak iddialara dayalı, somut kanıtlarla desteklenmesi ikna ediciliği artırır.')",
      "iknaEdicilikPuani": "Kullanıcının genel performansına 1'den 10'a kadar bir puan ver (sadece sayı).",
      "genelYorum": "Kullanıcının performansına dair 1-2 cümlelik genel bir eğitmen yorumu ekle."
    }}"""

        payload = {
            "contents": [{"role": "user", "parts": [{"text": report_prompt}]}],
        }

        response = requests.post(GEMINI_API_URL, json=payload)
        response.raise_for_status()
        response_text = response.json()['candidates'][0]['content']['parts'][0]['text']
        
        cleaned_json_string = response_text.strip().replace("```json", "").replace("```", "").strip()
        
        report_json = json.loads(cleaned_json_string)
        return jsonify(report_json)

    except requests.exceptions.HTTPError as http_err:
        error_info = http_err.response.json()
        return jsonify({"error": f"API Hatası: {error_info.get('error', {}).get('message', 'Bilinmeyen API hatası')}"}), http_err.response.status_code
    except Exception as e:
        return jsonify({"error": f"Sunucuda beklenmedik bir hata oluştu: {str(e)}"}), 500

@app.route('/api/schema', methods=['POST'])
def handle_schema():
    try:
        data = request.json
        if not data:
            return jsonify({"error": "Geçersiz istek: JSON verisi bulunamadı."}), 400

        messages = data.get('messages', [])
        conversation_history = "\\n".join([f"{'Kullanıcı' if m['author'] == 'user' else 'AI Münazır'}: {m['text']}" for m in messages])

        schema_prompt = f"""Aşağıdaki münazara metnini analiz et ve metindeki mantıksal akışı temsil eden bir Mermaid.js şeması oluştur.

    Kurallar:
    1.  Çıktı, sadece ve sadece geçerli bir Mermaid.js `graph TD` (Top-Down) sözdizimi içermelidir.
    2.  Kullanıcının ana argümanlarını özetleyerek dikdörtgen kutular içine al. Örn: A["Ana Argüman 1"].
    3.  Kullanıcının bu ana argümanları desteklemek için sunduğu alt fikirleri veya örnekleri yuvarlak kenarlı kutular içine al. Örn: B("Destekleyici Fikir 1.1").
    4.  AI Münazır'ın, kullanıcının argümanlarına veya fikirlerine getirdiği karşı argümanları eşkenar dörtgen (rhombus) şekli içine al. Örn: C{{"Karşı Argüman 1"}}.
    5.  Okları (`-->`) kullanarak argümanlar, destekleyici fikirler ve karşı argümanlar arasındaki mantıksal bağlantıyı göster.
    6.  Metinleri kısa ve öz tut, cümlenin tamamını değil, fikrin özetini yaz.
    7.  Yanıtın doğrudan 'graph TD' ile başlamalıdır. Öncesinde veya sonrasında başka hiçbir metin, açıklama veya kod bloğu (` ```) olmamalıdır.

    Münazara Metni:
    \"\"\"
    {conversation_history}
    \"\"\"
    
    Mermaid.js Çıktısı:
    """

        payload = {
            "contents": [{"role": "user", "parts": [{"text": schema_prompt}]}],
        }

        response = requests.post(GEMINI_API_URL, json=payload)
        response.raise_for_status()
        response_text = response.json()['candidates'][0]['content']['parts'][0]['text']
        
        cleaned_schema_string = response_text.strip().replace("```mermaid", "").replace("```", "").strip()
        
        return jsonify({"schema": cleaned_schema_string})

    except requests.exceptions.HTTPError as http_err:
        error_info = http_err.response.json()
        return jsonify({"error": f"API Hatası: {error_info.get('error', {}).get('message', 'Bilinmeyen API hatası')}"}), http_err.response.status_code
    except Exception as e:
        return jsonify({"error": f"Sunucuda beklenmedik bir hata oluştu: {str(e)}"}), 500


if __name__ == '__main__':
    app.run(debug=False, port=5000)
