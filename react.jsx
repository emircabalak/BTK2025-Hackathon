import React, { useState, useEffect, useRef } from 'react';

// --- ICONS (using inline SVGs for self-containment) ---
const BrainCircuitIcon = (props) => (
  <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}>
    <path d="M12 2a2.5 2.5 0 0 1 2.5 2.5v.75a2.5 2.5 0 0 1-5 0v-.75A2.5 2.5 0 0 1 12 2Z" />
    <path d="M4.5 9.5A2.5 2.5 0 0 0 7 12v0a2.5 2.5 0 0 0-2.5 2.5v0A2.5 2.5 0 0 0 7 17v0a2.5 2.5 0 0 0-2.5 2.5v0" />
    <path d="M19.5 9.5A2.5 2.5 0 0 1 17 12v0a2.5 2.5 0 0 1 2.5 2.5v0A2.5 2.5 0 0 1 17 17v0a2.5 2.5 0 0 1 2.5 2.5v0" />
    <path d="M12 12a2.5 2.5 0 0 0-2.5-2.5v0A2.5 2.5 0 0 0 7 7v0" />
    <path d="M12 12a2.5 2.5 0 0 1 2.5-2.5v0A2.5 2.5 0 0 1 17 7v0" />
    <path d="M12 12a2.5 2.5 0 0 0-2.5 2.5v0A2.5 2.5 0 0 0 7 17v0" />
    <path d="M12 12a2.5 2.5 0 0 1 2.5 2.5v0A2.5 2.5 0 0 1 17 17v0" />
    <path d="M12 4.75v3.5" />
    <path d="M7 9.5h10" />
    <path d="M7 14.5h10" />
    <path d="M12 17.25v3.5" />
  </svg>
);

const SendIcon = (props) => (
  <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}>
    <path d="m22 2-7 20-4-9-9-4Z" />
    <path d="M22 2 11 13" />
  </svg>
);

const BotIcon = (props) => (
    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}>
        <path d="M12 8V4H8" />
        <rect width="16" height="12" x="4" y="8" rx="2" />
        <path d="M2 14h2" />
        <path d="M20 14h2" />
        <path d="M15 13v2" />
        <path d="M9 13v2" />
    </svg>
);

const UserIcon = (props) => (
    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}>
        <path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2" />
        <circle cx="12" cy="7" r="4" />
    </svg>
);


// --- Main App Component ---
export default function App() {
  // State management for the entire application
  const [screen, setScreen] = useState('topic'); // 'topic', 'debate', 'report'
  const [topic, setTopic] = useState('');
  const [customTopic, setCustomTopic] = useState('');
  const [stance, setStance] = useState(''); // 'savunuyorum', 'karşı çıkıyorum'
  const [messages, setMessages] = useState([]);
  const [report, setReport] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  const finalTopic = topic === 'custom' ? customTopic : topic;

  // Pre-defined debate topics
  const predefinedTopics = [
    { value: 'Yapay zeka insanlık için bir tehdit mi?', label: 'Yapay zeka insanlık için bir tehdit mi?' },
    { value: 'Üniversite eğitimi herkes için ücretsiz mi olmalı?', label: 'Üniversite eğitimi herkes için ücretsiz mi olmalı?' },
    { value: 'Sosyal medya toplumu olumlu yönde mi etkiliyor?', label: 'Sosyal medya toplumu olumlu yönde mi etkiliyor?' },
  ];

  // Function to handle starting the debate
  const handleStartDebate = () => {
    if (!finalTopic || !stance) {
      setError('Lütfen bir konu ve taraf seçin.');
      return;
    }
    setError('');
    setMessages([]);
    setReport(null);
    setScreen('debate');
  };
  
  // Function to call Gemini API
  const callGeminiAPI = async (prompt, isJson = false) => {
      setIsLoading(true);
      setError('');
      
      let chatHistory = [];
      chatHistory.push({ role: "user", parts: [{ text: prompt }] });
      
      const payload = { contents: chatHistory };
      if (isJson) {
          payload.generationConfig = {
              responseMimeType: "application/json",
          };
      }
      
      const apiKey = ""; // The environment will provide the key
      // FIX: Changed model to gemini-2.0-flash which is compatible with the auto-provided API key.
      const apiUrl = `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=${apiKey}`;

      try {
          const response = await fetch(apiUrl, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify(payload)
          });

          if (!response.ok) {
              const errorData = await response.json().catch(() => null); 
              const errorMessage = errorData?.error?.message || `API Hatası: ${response.status} ${response.statusText}`;
              throw new Error(errorMessage);
          }

          const result = await response.json();
          
          if (result.candidates && result.candidates.length > 0 &&
              result.candidates[0].content && result.candidates[0].content.parts &&
              result.candidates[0].content.parts.length > 0) {
            return result.candidates[0].content.parts[0].text;
          } else {
            console.error("Unexpected API response structure:", result);
            throw new Error("API'den beklenen formatta bir yanıt alınamadı.");
          }

      } catch (e) {
          console.error(e);
          setError(e.message || "Bir hata oluştu. Lütfen tekrar deneyin.");
          return null;
      } finally {
          setIsLoading(false);
      }
  };


  // Function to handle sending a user message
  const handleSendMessage = async (text) => {
    const userMessage = { author: 'user', text };
    const newMessages = [...messages, userMessage];
    setMessages(newMessages);

    const systemPrompt = `Sen, 'Münazara Arenası' platformunun yapay zeka münazırısın. Görevin, kullanıcıyla seçilen bir konu üzerinde mantık ve kanıta dayalı bir münazara yapmaktır.

Kuralların:
1. Her zaman saygılı, objektif ve tarafsız bir dil kullan. Asla saldırgan veya kişisel olma.
2. Kullanıcının argümanlarını dikkatle analiz et ve doğrudan bu argümanlara cevap ver. Konuyu dağıtma.
3. Kendi argümanlarını desteklemek için genel bilgi, istatistik veya mantıksal çıkarımlar kullan. Ancak 'Ben bir yapay zekayım' gibi ifadelerden kaçın. Rolünü oyna.
4. Kullanıcının yaptığı mantık hatalarını (örneğin, adam karalama, korkuluk safsatası) fark et, ancak bunları münazara sırasında yüzüne vurma. Bu bilgiyi final raporu için sakla.
5. Cevapların net, anlaşılır ve 2-3 paragrafı geçmeyecek uzunlukta olsun.

Şu anki konumuz: "${finalTopic}". Kullanıcı bu konuda "${stance === 'savunuyorum' ? 'destekleyici' : 'karşıt'}" tarafı savunuyor. Sen ise karşı tarafı savunacaksın. Sohbet geçmişini dikkate alarak sadece sıradaki cevabını ver.`;

    const conversationHistory = newMessages.map(m => `${m.author === 'user' ? 'Kullanıcı' : 'AI Münazır'}: ${m.text}`).join('\n');
    const fullPrompt = `${systemPrompt}\n\n---SOHBET GEÇMİŞİ---\n${conversationHistory}\n\nAI Münazır'ın sıradaki cevabı:`;
    
    const aiResponseText = await callGeminiAPI(fullPrompt);
    
    if (aiResponseText) {
      const aiMessage = { author: 'ai', text: aiResponseText };
      setMessages(prev => [...prev, aiMessage]);
    }
  };

  // Function to end the debate and generate a report
  const handleEndDebate = async () => {
    const conversationHistory = messages.map(m => `${m.author === 'user' ? 'Kullanıcı' : 'AI Münazır'}: ${m.text}`).join('\n');
    
    const reportPrompt = `Aşağıda bir kullanıcı ile senin aranda geçen münazaranın tam metni bulunmaktadır. Bu metni bir münazara eğitmeni gibi analiz et ve aşağıdaki kriterlere göre bir performans raporu oluştur. Çıktıyı mutlaka geçerli bir JSON formatında ver.

Münazara Metni:
"""
${conversationHistory}
"""

JSON Formatında İstenen Rapor Şeması:
{
  "enGucluArguman": "Kullanıcının sunduğu en güçlü ve ikna edici argümanı buraya özetle.",
  "gelistirilmesiGerekenNokta": {
    "tespitEdilenHata": "Kullanıcının yaptığı en belirgin mantık hatası veya zayıf argümanı buraya yaz. Örneğin: 'Kullanıcı, karşı argümanı basitleştirerek bir Korkuluk Safsatası (Straw Man) yapmıştır.'",
    "onerilenGelistirme": "Bu hatayı nasıl düzeltebileceğine dair kısa bir tavsiye ver."
  },
  "iknaEdicilikPuani": "Kullanıcının genel performansına 1'den 10'a kadar bir puan ver (sadece sayı).",
  "genelYorum": "Kullanıcının performansına dair 1-2 cümlelik genel bir eğitmen yorumu ekle."
}`;

    const reportJsonText = await callGeminiAPI(reportPrompt, true);

    if (reportJsonText) {
        try {
            const parsedReport = JSON.parse(reportJsonText);
            setReport(parsedReport);
            setScreen('report');
        } catch(e) {
            console.error("Failed to parse report JSON:", e);
            setError("Rapor oluşturulurken bir hata oluştu. Lütfen rapor formatını kontrol edin.");
            // Fallback to showing raw text if JSON parsing fails
            setReport({ rawText: reportJsonText });
            setScreen('report');
        }
    }
  };

  // Function to start a new debate
  const handleNewDebate = () => {
    setScreen('topic');
    setTopic('');
    setCustomTopic('');
    setStance('');
    setMessages([]);
    setReport(null);
    setError('');
  };

  // Render different screens based on the current state
  const renderScreen = () => {
    switch (screen) {
      case 'debate':
        return <DebateScreen messages={messages} onSendMessage={handleSendMessage} onEndDebate={handleEndDebate} isLoading={isLoading} topic={finalTopic} />;
      case 'report':
        return <ReportScreen report={report} onNewDebate={handleNewDebate} />;
      case 'topic':
      default:
        return (
          <TopicSelectionScreen
            topic={topic}
            setTopic={setTopic}
            customTopic={customTopic}
            setCustomTopic={setCustomTopic}
            stance={stance}
            setStance={setStance}
            onStartDebate={handleStartDebate}
            predefinedTopics={predefinedTopics}
            error={error}
          />
        );
    }
  };

  return (
    <div className="bg-gray-900 text-white min-h-screen font-sans flex flex-col items-center justify-center p-4">
      <div className="w-full max-w-2xl mx-auto bg-gray-800 rounded-2xl shadow-2xl flex flex-col" style={{height: '90vh'}}>
        <header className="p-4 border-b border-gray-700 flex items-center space-x-3">
          <BrainCircuitIcon className="h-8 w-8 text-cyan-400" />
          <div>
            <h1 className="text-xl font-bold text-white">Münazara Arenası</h1>
            <p className="text-sm text-gray-400">Yapay zeka ile argümanlarını sına</p>
          </div>
        </header>
        <main className="flex-grow p-6 overflow-y-auto">
          {renderScreen()}
        </main>
      </div>
    </div>
  );
}

// --- Sub-components for different screens ---

const TopicSelectionScreen = ({ topic, setTopic, customTopic, setCustomTopic, stance, setStance, onStartDebate, predefinedTopics, error }) => {
  return (
    <div className="flex flex-col h-full justify-center animate-fade-in">
      <div className="space-y-6">
        <div>
          <label htmlFor="topic-select" className="block text-sm font-medium text-gray-300 mb-2">1. Bir Münazara Konusu Seçin</label>
          <select
            id="topic-select"
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            className="w-full p-3 bg-gray-700 border border-gray-600 rounded-lg focus:ring-2 focus:ring-cyan-500 focus:border-cyan-500 transition"
          >
            <option value="" disabled>Konu seç...</option>
            {predefinedTopics.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
            <option value="custom">Kendi konumu yazmak istiyorum...</option>
          </select>
        </div>

        {topic === 'custom' && (
          <div className="animate-fade-in">
            <input
              type="text"
              value={customTopic}
              onChange={(e) => setCustomTopic(e.target.value)}
              placeholder="Münazara konunuzu buraya yazın"
              className="w-full p-3 bg-gray-700 border border-gray-600 rounded-lg focus:ring-2 focus:ring-cyan-500 focus:border-cyan-500 transition"
            />
          </div>
        )}

        <div>
          <h3 className="block text-sm font-medium text-gray-300 mb-2">2. Tarafınızı Belirleyin</h3>
          <div className="grid grid-cols-2 gap-4">
            <button
              onClick={() => setStance('savunuyorum')}
              className={`p-4 rounded-lg text-center transition ${stance === 'savunuyorum' ? 'bg-green-600 ring-2 ring-green-400' : 'bg-gray-700 hover:bg-gray-600'}`}
            >
              Savunuyorum
            </button>
            <button
              onClick={() => setStance('karşı çıkıyorum')}
              className={`p-4 rounded-lg text-center transition ${stance === 'karşı çıkıyorum' ? 'bg-red-600 ring-2 ring-red-400' : 'bg-gray-700 hover:bg-gray-600'}`}
            >
              Karşı Çıkıyorum
            </button>
          </div>
        </div>
        
        {error && <p className="text-red-400 text-sm text-center">{error}</p>}

        <button
          onClick={onStartDebate}
          disabled={!(topic === 'custom' ? customTopic : topic) || !stance}
          className="w-full p-4 bg-cyan-600 hover:bg-cyan-700 rounded-lg font-bold text-lg transition disabled:bg-gray-600 disabled:cursor-not-allowed"
        >
          Münazarayı Başlat
        </button>
      </div>
    </div>
  );
};

const DebateScreen = ({ messages, onSendMessage, onEndDebate, isLoading, topic }) => {
  const [inputText, setInputText] = useState('');
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(scrollToBottom, [messages, isLoading]);

  const handleSend = () => {
    if (inputText.trim()) {
      onSendMessage(inputText);
      setInputText('');
    }
  };

  return (
    <div className="flex flex-col h-full">
      <div className="p-4 border-b border-gray-700 bg-gray-800/80 backdrop-blur-sm -mx-6 -mt-6 mb-4 sticky top-0 z-10">
        <h3 className="text-center font-semibold text-gray-300">Konu: <span className="text-cyan-400">{topic}</span></h3>
      </div>
      <div className="flex-grow overflow-y-auto pr-4 -mr-4 space-y-6">
        {messages.map((msg, index) => (
          <div key={index} className={`flex items-start gap-3 animate-fade-in ${msg.author === 'user' ? 'justify-end' : 'justify-start'}`}>
            {msg.author === 'ai' && <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gray-700 flex items-center justify-center"><BotIcon className="w-5 h-5 text-cyan-400"/></div>}
            <div className={`max-w-md p-3 rounded-xl ${msg.author === 'user' ? 'bg-cyan-600 text-white rounded-br-none' : 'bg-gray-700 text-gray-200 rounded-bl-none'}`}>
              <p className="text-sm" style={{whiteSpace: 'pre-wrap'}}>{msg.text}</p>
            </div>
             {msg.author === 'user' && <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gray-700 flex items-center justify-center"><UserIcon className="w-5 h-5 text-gray-300"/></div>}
          </div>
        ))}
        {isLoading && (
          <div className="flex items-start gap-3 justify-start">
            <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gray-700 flex items-center justify-center"><BotIcon className="w-5 h-5 text-cyan-400"/></div>
            <div className="max-w-md p-3 rounded-xl bg-gray-700 text-gray-200 rounded-bl-none">
                <div className="flex items-center space-x-2">
                    <div className="w-2 h-2 bg-cyan-400 rounded-full animate-pulse"></div>
                    <div className="w-2 h-2 bg-cyan-400 rounded-full animate-pulse" style={{animationDelay: '0.2s'}}></div>
                    <div className="w-2 h-2 bg-cyan-400 rounded-full animate-pulse" style={{animationDelay: '0.4s'}}></div>
                </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>
      <div className="mt-4 pt-4 border-t border-gray-700">
        <div className="flex items-center space-x-2">
          <input
            type="text"
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && !isLoading && handleSend()}
            placeholder="Argümanınızı yazın..."
            className="flex-grow p-3 bg-gray-700 border border-gray-600 rounded-lg focus:ring-2 focus:ring-cyan-500 focus:border-cyan-500 transition"
            disabled={isLoading}
          />
          <button onClick={handleSend} disabled={isLoading} className="p-3 bg-cyan-600 hover:bg-cyan-700 rounded-lg transition disabled:bg-gray-600">
            <SendIcon className="w-6 h-6" />
          </button>
        </div>
        <button onClick={onEndDebate} disabled={isLoading} className="w-full mt-3 p-3 bg-red-600 hover:bg-red-700 rounded-lg font-bold transition disabled:bg-gray-600">
          Münazarayı Bitir ve Rapor Al
        </button>
      </div>
    </div>
  );
};

const ReportScreen = ({ report, onNewDebate }) => {
    if (!report) {
        return (
            <div className="text-center">
                <p>Rapor yükleniyor veya bir hata oluştu...</p>
                <button onClick={onNewDebate} className="mt-4 p-3 bg-cyan-600 hover:bg-cyan-700 rounded-lg font-bold">Yeni Münazara Başlat</button>
            </div>
        );
    }
    
    // Fallback for when JSON parsing fails
    if (report.rawText) {
        return (
            <div className="flex flex-col h-full justify-center items-center text-center animate-fade-in space-y-6">
                <h2 className="text-2xl font-bold text-red-400">Rapor Hatası</h2>
                <p className="text-gray-300">Raporun formatı anlaşılamadı. Ham veri aşağıdadır:</p>
                <pre className="p-4 bg-gray-900 rounded-lg text-left text-sm text-yellow-300 overflow-x-auto w-full">
                    {report.rawText}
                </pre>
                <button onClick={onNewDebate} className="w-full max-w-xs p-3 bg-cyan-600 hover:bg-cyan-700 rounded-lg font-bold transition">
                    Yeni Münazara Başlat
                </button>
            </div>
        );
    }

    const score = report.iknaEdicilikPuani || 0;

    return (
        <div className="flex flex-col h-full justify-center animate-fade-in space-y-6">
            <h2 className="text-3xl font-bold text-center text-cyan-400">Performans Raporu</h2>
            
            <div className="relative flex justify-center items-center">
                <svg className="transform -rotate-90" width="120" height="120" viewBox="0 0 120 120">
                    <circle cx="60" cy="60" r="54" fill="none" stroke="#374151" strokeWidth="12" />
                    <circle
                        cx="60"
                        cy="60"
                        r="54"
                        fill="none"
                        stroke="#22d3ee"
                        strokeWidth="12"
                        strokeDasharray={2 * Math.PI * 54}
                        strokeDashoffset={2 * Math.PI * 54 * (1 - score / 10)}
                        strokeLinecap="round"
                        className="transition-all duration-1000 ease-out"
                    />
                </svg>
                <span className="absolute text-3xl font-bold">{score}<span className="text-lg">/10</span></span>
            </div>
            <p className="text-center text-lg font-semibold text-gray-300">İkna Edicilik Puanı</p>

            <div className="space-y-4">
                <div className="p-4 bg-gray-700 rounded-lg">
                    <h3 className="font-semibold text-green-400 mb-2">En Güçlü Argümanınız</h3>
                    <p className="text-sm text-gray-300">{report.enGucluArguman}</p>
                </div>
                <div className="p-4 bg-gray-700 rounded-lg">
                    <h3 className="font-semibold text-yellow-400 mb-2">Geliştirilmesi Gereken Nokta</h3>
                    <p className="text-sm text-gray-300 font-bold">{report.gelistirilmesiGerekenNokta?.tespitEdilenHata}</p>
                    <p className="text-sm text-gray-400 mt-1">{report.gelistirilmesiGerekenNokta?.onerilenGelistirme}</p>
                </div>
                <div className="p-4 bg-gray-700 rounded-lg">
                    <h3 className="font-semibold text-cyan-400 mb-2">Genel Yorum</h3>
                    <p className="text-sm text-gray-300">{report.genelYorum}</p>
                </div>
            </div>

            <button onClick={onNewDebate} className="w-full p-3 bg-cyan-600 hover:bg-cyan-700 rounded-lg font-bold transition">
                Yeni Münazara Başlat
            </button>
        </div>
    );
};
