import React, { useState, useEffect, useMemo, useCallback, useRef } from 'react';
import { initializeApp } from 'firebase/app';
import {
  getAuth,
  signInAnonymously,
  onAuthStateChanged,
} from 'firebase/auth';
import { getFirestore, doc, setDoc, onSnapshot } from 'firebase/firestore';
import {
  Users,
  Calendar,
  Lightbulb,
  CheckSquare,
  Plus,
  Trash2,
  LayoutDashboard,
  Star,
  Heart,
  ScrollText,
  MessageSquare,
  Quote,
  UtensilsCrossed,
  Bird,
  Sparkles,
  Baby,
  Moon,
  Sun,
  Copy,
  Check,
  Lock,
  Unlock,
  Send,
  Mic,
  Download,
} from 'lucide-react';

const firebaseConfig = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID,
  storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET,
  messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID,
  appId: import.meta.env.VITE_FIREBASE_APP_ID,
};

const hubAppId =
  import.meta.env.VITE_HUB_APP_ID || 'baruch-70-hub-final';
const configuredEditorKey =
  import.meta.env.VITE_HUB_EDITOR_KEY || '';

const LS_KEY = `baruch70hub:mainState:${hubAppId}`;
const LS_EDITOR_KEY = `baruch70hub:editorKey`;

const defaultData = () => ({
  portrait: {
    roots:
      'סיפור המזלג של סבתא אדלה (הגנה ואומץ), ביטול העצמי של סבא אברהם (חיתון האחים). שורשי חאלב.',
    character:
      'מאיפוק חלאבי וביקורתיות ל"מרגרינה" - אדם חם, אוהב, שחושב על עצמו אחרון.',
    torah: 'לוי, חזן ימים נוראים 20 שנה, אהבת שירי שבת ומסורת חלאבית.',
    art: 'ידי אמן: ינשוף מעץ, דמויות פימו, ציור. יצירתיות שקטה.',
  },
  schedule: [
    {
      id: '1',
      time: 'ערב שבת',
      activity: 'התכנסות וקבלת שבת',
      lead: 'לוגיסטיקה',
      content: 'שירי שבת שאבא אוהב',
    },
    {
      id: '2',
      time: 'סעודה 1',
      activity: 'תמונה משפחתית',
      lead: 'צלם',
      content: '"שכבות" - משפחה סביב אבא',
    },
    {
      id: '3',
      time: 'לילה',
      activity: 'הפתעות בחדרים',
      lead: 'לוגיסטיקה',
      content: 'עוגיות, שתייה וכרטיסי ברכה',
    },
    {
      id: '4',
      time: 'סעודה 2',
      activity: 'משחק חיבור',
      lead: 'רגשי',
      content: '"סיפור אחד מאבא"',
    },
    {
      id: '5',
      time: 'עונג שבת',
      activity: "דבר תורה (50 דק')",
      lead: 'אופיר',
      content: 'הושענא רבה ודמות אבא',
    },
    {
      id: '6',
      time: 'מוצ"ש',
      activity: 'טקס אוסקר',
      lead: 'יצירתי',
      content: 'טריילר ה-AI וחלוקת 5 פרסים',
    },
  ],
  ideas: [
    {
      id: 'i1',
      title: 'טריילר קולנועי AI',
      detail:
        "פרומו \"גיבור שקט\" ב-5 ז'אנרים: שורשים, בנייה, תורה, אמנות, סבא.",
      status: 'planning',
      locked: false,
    },
    {
      id: 'i2',
      title: 'טקס אוסקר בטש',
      detail:
        "פרסים פיזיים: מיני-ג'יפ, שטיחון, פסנתרון. קטגוריות כמו \"פרס קול התפילה\".",
      status: 'approved',
      locked: false,
    },
    {
      id: 'i3',
      title: 'שחזור תמונה היסטורית',
      detail: 'שחזור תמונת סבא-סבתא עם כל הנכדים סביב אבא.',
      status: 'draft',
      locked: false,
    },
  ],
  tasks: [
    {
      id: 't1',
      title: 'סגירת מלון ואוכל חלאבי',
      date: '2026-06-01',
      status: 'todo',
      owner: 'אח לוגיסטי',
    },
    {
      id: 't2',
      title: 'איסוף סיפורים מדודים וחברים',
      date: '2026-08-01',
      status: 'todo',
      owner: 'אח רגשי',
    },
    {
      id: 't3',
      title: 'הפקת טריילר AI',
      date: '2026-09-15',
      status: 'todo',
      owner: 'אח יצירתי',
    },
  ],
  questionnaire: [
    {
      id: 'q1',
      target: 'נכדים',
      question: 'איזו יצירה של סבא (ינשוף, פימו) הכי זכורה לך?',
    },
    {
      id: 'q2',
      target: 'משפחה',
      question: 'איך רואים את סיפור המזלג חוזר בדמותו של ברוך?',
    },
    {
      id: 'q3',
      target: 'חברים',
      question: 'ספרו על רגע של נתינה שקטה שראיתם אצלו.',
    },
  ],
  grandkidsNotes: [],
});

function loadLocal() {
  try {
    const raw = localStorage.getItem(LS_KEY);
    if (!raw) return null;
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

function saveLocal(data) {
  try {
    localStorage.setItem(LS_KEY, JSON.stringify(data));
  } catch (e) {
    console.warn('local save failed', e);
  }
}

function mergeWithDefaults(patch) {
  const base = defaultData();
  if (!patch || typeof patch !== 'object') return base;
  return {
    ...base,
    ...patch,
    portrait: { ...base.portrait, ...(patch.portrait || {}) },
    schedule: Array.isArray(patch.schedule) ? patch.schedule : base.schedule,
    ideas: Array.isArray(patch.ideas)
      ? patch.ideas.map((i) => ({
          locked: false,
          ...i,
        }))
      : base.ideas,
    tasks: Array.isArray(patch.tasks) ? patch.tasks : base.tasks,
    questionnaire: Array.isArray(patch.questionnaire)
      ? patch.questionnaire
      : base.questionnaire,
    grandkidsNotes: Array.isArray(patch.grandkidsNotes)
      ? patch.grandkidsNotes
      : base.grandkidsNotes || [],
  };
}

function buildTrailerPrompt(portrait) {
  const sections = [
    ['שורשים ומשפחה (המזלג, חאלב)', portrait.roots],
    ['אופי ומהפך (המרגרינה)', portrait.character],
    ['תורה, לוויה וחזנות', portrait.torah],
    ['אמנות ויצירה (פימו, ינשוף)', portrait.art],
  ]
    .map(([t, b]) => (b && String(b).trim() ? `## ${t}\n${String(b).trim()}` : ''))
    .filter(Boolean)
    .join('\n\n');

  return [
    'אתה יוצר טריילר קצר (30–90 שניות) לכבוד יום הולדת 70 לברוך בטש.',
    'קונספט: "גיבור שקט" — עומק רוחני (הושענא רבה), מורשת חלאבית, יצירתיות שקטה.',
    'הימנע מקלישאות; שמור על כבוד, חום משפחתי, ותחושת ארכיון רגשי.',
    '',
    'השתמש בחומרי הדיוקן הבאים כבסיס לדימויים, קריינות ומוזיקה מוצעת:',
    '',
    sections || '(השלימו את דיוקן אבא בלשונית המתאימה)',
    '',
    'פלט מבוקש: רעיון לוויזואליה בזמן, טקסט קריינות בעברית (קצר), והמלצות לסגנון צילום/צבע.',
  ].join('\n');
}

const App = () => {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [firebaseReady, setFirebaseReady] = useState(false);
  const [data, setData] = useState(() =>
    mergeWithDefaults(loadLocal() || {}),
  );
  const [eveningMode, setEveningMode] = useState(false);
  const [editorKeyInput, setEditorKeyInput] = useState(() => {
    try {
      return localStorage.getItem(LS_EDITOR_KEY) || '';
    } catch {
      return '';
    }
  });
  const [promptCopied, setPromptCopied] = useState(false);

  const appRef = useRef(null);
  const authRef = useRef(null);
  const dbRef = useRef(null);

  const isEditor = useMemo(() => {
    if (!configuredEditorKey) return true;
    return editorKeyInput && editorKeyInput === configuredEditorKey;
  }, [editorKeyInput, configuredEditorKey]);

  const persistEditorKey = (v) => {
    setEditorKeyInput(v);
    try {
      if (v) localStorage.setItem(LS_EDITOR_KEY, v);
      else localStorage.removeItem(LS_EDITOR_KEY);
    } catch {
      /* ignore */
    }
  };

  useEffect(() => {
    const hasKey = Boolean(firebaseConfig.apiKey && firebaseConfig.projectId);
    if (!hasKey) {
      setFirebaseReady(false);
      setLoading(false);
      return;
    }
    try {
      const app = initializeApp(firebaseConfig);
      appRef.current = app;
      authRef.current = getAuth(app);
      dbRef.current = getFirestore(app);
      setFirebaseReady(true);
    } catch (e) {
      console.error('Firebase init error', e);
      setFirebaseReady(false);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!firebaseReady || !authRef.current) return;
    const auth = authRef.current;
    const unsub = onAuthStateChanged(auth, setUser);
    signInAnonymously(auth).catch((err) => console.error('Auth error:', err));
    return () => unsub();
  }, [firebaseReady]);

  useEffect(() => {
    if (!firebaseReady || !user || !dbRef.current) return;
    const docRef = doc(
      dbRef.current,
      'artifacts',
      hubAppId,
      'public',
      'mainState',
    );
    const unsubscribe = onSnapshot(
      docRef,
      (docSnap) => {
        if (docSnap.exists()) {
          setData((prev) => mergeWithDefaults({ ...prev, ...docSnap.data() }));
        }
      },
      (error) => console.error('Firestore sync error:', error),
    );
    return () => unsubscribe();
  }, [user, firebaseReady]);

  useEffect(() => {
    if (firebaseReady) return;
    saveLocal(data);
  }, [data, firebaseReady]);

  const syncData = async (newData) => {
    if (!firebaseReady || !user || !dbRef.current) return;
    try {
      const docRef = doc(
        dbRef.current,
        'artifacts',
        hubAppId,
        'public',
        'mainState',
      );
      await setDoc(docRef, newData, { merge: true });
    } catch (err) {
      console.error('Save error:', err);
    }
  };

  const handleUpdate = useCallback(
    (path, value) => {
      const keys = path.split('.');
      const newData = { ...data };
      let current = newData;
      for (let i = 0; i < keys.length - 1; i++) {
        current[keys[i]] = { ...current[keys[i]] };
        current = current[keys[i]];
      }
      current[keys[keys.length - 1]] = value;
      setData(newData);
      syncData(newData);
      if (!firebaseReady) saveLocal(newData);
    },
    [data, firebaseReady, user],
  );

  const addItem = useCallback(
    (listKey, template) => {
      const newItem = { ...template, id: Date.now().toString() };
      const newData = { ...data, [listKey]: [...data[listKey], newItem] };
      setData(newData);
      syncData(newData);
      if (!firebaseReady) saveLocal(newData);
    },
    [data, firebaseReady, user],
  );

  const deleteItem = useCallback(
    (listKey, id) => {
      const newData = {
        ...data,
        [listKey]: data[listKey].filter((i) => i.id !== id),
      };
      setData(newData);
      syncData(newData);
      if (!firebaseReady) saveLocal(newData);
    },
    [data, firebaseReady, user],
  );

  const trailerPrompt = useMemo(
    () => buildTrailerPrompt(data.portrait),
    [data.portrait],
  );

  const copyPrompt = () => {
    navigator.clipboard.writeText(trailerPrompt).then(() => {
      setPromptCopied(true);
      setTimeout(() => setPromptCopied(false), 2000);
    });
  };

  const navItems = [
    { id: 'dashboard', label: 'סקירה כללית', icon: LayoutDashboard },
    { id: 'portrait', label: 'דיוקן אבא', icon: UtensilsCrossed },
    { id: 'schedule', label: 'לו"ז השבת', icon: Calendar },
    { id: 'ideas', label: 'קומה 2 (רעיונות)', icon: Lightbulb },
    { id: 'tasks', label: 'משימות וביצוע', icon: CheckSquare },
    { id: 'survey', label: 'שאלון סיפורים', icon: MessageSquare },
    { id: 'prompt', label: 'מחולל פרומפט AI', icon: Sparkles },
    { id: 'grandkids', label: 'אזור נכדים', icon: Baby },
  ];

  const shellClass = eveningMode
    ? 'bg-zinc-950 text-amber-50'
    : 'bg-slate-50 text-slate-900';
  const sidebarClass = eveningMode
    ? 'bg-zinc-900 text-amber-50 border-amber-900/40 shadow-[0_0_60px_rgba(234,179,8,0.08)]'
    : 'bg-indigo-950 text-white';
  const mainBg = eveningMode ? 'bg-zinc-950' : 'bg-[#f8fafc]';

  if (loading && firebaseReady) {
    return (
      <div className="p-20 text-center animate-pulse" dir="rtl">
        מתחבר למערכת ברוך בטש 70...
      </div>
    );
  }

  return (
    <div
      className={`flex h-screen font-sans overflow-hidden transition-colors duration-500 ${shellClass}`}
      dir="rtl"
    >
      <nav
        className={`w-72 flex flex-col p-6 shadow-2xl z-20 border-l ${sidebarClass}`}
      >
        <div className="mb-8 flex flex-col items-center">
          <div
            className={`w-20 h-20 rounded-3xl rotate-3 flex items-center justify-center shadow-lg mb-4 ${
              eveningMode
                ? 'bg-gradient-to-tr from-amber-600 to-yellow-200 text-zinc-950'
                : 'bg-gradient-to-tr from-amber-400 to-yellow-200 text-indigo-950'
            }`}
          >
            <span className="text-4xl font-black -rotate-3">70</span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight">ברוך בטש</h1>
          <p
            className={`text-xs font-medium uppercase tracking-widest mt-1 ${
              eveningMode ? 'text-amber-200/70' : 'text-indigo-300'
            }`}
          >
            Event Hub
          </p>
        </div>

        <div className="space-y-1 flex-1 overflow-y-auto min-h-0 pr-1">
          {navItems.map((item) => (
            <button
              key={item.id}
              type="button"
              onClick={() => setActiveTab(item.id)}
              className={`w-full flex items-center gap-4 px-4 py-3 rounded-2xl transition-all duration-200 ${
                activeTab === item.id
                  ? eveningMode
                    ? 'bg-amber-500/15 text-amber-100 border border-amber-500/30 font-bold translate-x-1'
                    : 'bg-white text-indigo-950 shadow-md font-bold translate-x-1'
                  : eveningMode
                    ? 'hover:bg-zinc-800 text-amber-100/60 hover:text-amber-50'
                    : 'hover:bg-indigo-900/50 text-indigo-100/70 hover:text-white'
              }`}
            >
              <item.icon size={20} strokeWidth={activeTab === item.id ? 2.5 : 2} />
              <span>{item.label}</span>
            </button>
          ))}
        </div>

        <div className="mt-4 space-y-3">
          <button
            type="button"
            onClick={() => setEveningMode((v) => !v)}
            className={`w-full flex items-center justify-center gap-2 py-3 rounded-2xl font-bold text-sm transition-all ${
              eveningMode
                ? 'bg-amber-500/20 text-amber-100 border border-amber-500/40'
                : 'bg-indigo-900/40 text-indigo-100 border border-indigo-800/50'
            }`}
          >
            {eveningMode ? <Sun size={18} /> : <Moon size={18} />}
            {eveningMode ? 'מצב יום' : 'ערב שבת (כהה + זהב)'}
          </button>

          {configuredEditorKey ? (
            <div
              className={`p-3 rounded-2xl text-xs space-y-2 ${
                eveningMode
                  ? 'bg-zinc-800/80 border border-amber-900/30'
                  : 'bg-indigo-900/40 border border-indigo-800/50'
              }`}
            >
              <label className="block font-bold opacity-90">מפתח עורך ראשי</label>
              <input
                type="password"
                value={editorKeyInput}
                onChange={(e) => persistEditorKey(e.target.value)}
                placeholder="להפעלת אישורים ונעילה"
                className={`w-full rounded-xl px-3 py-2 border outline-none ${
                  eveningMode
                    ? 'bg-zinc-900 border-amber-900/40 text-amber-50'
                    : 'bg-indigo-950/50 border-indigo-700 text-white'
                }`}
              />
              <p className="opacity-70 leading-relaxed">
                {isEditor ? 'מחובר כעורך.' : 'ללא מפתח — צפייה ועריכה חופשית, ללא אישור/נעילה.'}
              </p>
            </div>
          ) : (
            <div
              className={`p-3 rounded-2xl text-xs ${
                eveningMode
                  ? 'bg-zinc-800/80 text-amber-200/80'
                  : 'bg-indigo-900/40 text-indigo-200'
              }`}
            >
              מצב צוות מלא: כל הפעולות פתוחות (הגדר VITE_HUB_EDITOR_KEY לאבטחה).
            </div>
          )}

          <div
            className={`flex items-center gap-3 text-sm p-3 rounded-2xl ${
              eveningMode
                ? 'bg-zinc-800/60 text-amber-200/90'
                : 'bg-indigo-900/40 text-indigo-200'
            }`}
          >
            <div className="w-2 h-2 bg-emerald-400 rounded-full animate-pulse shrink-0" />
            <span className="truncate">
              {firebaseReady && user
                ? `מחובר: ${user.uid.slice(0, 6)}…`
                : firebaseReady
                  ? 'ממתין להתחברות…'
                  : 'מצב מקומי (ללא Firebase)'}
            </span>
          </div>
        </div>
      </nav>

      <main className={`flex-1 overflow-y-auto p-8 lg:p-12 ${mainBg}`}>
        <div className="max-w-5xl mx-auto">
          {!firebaseReady && (
            <div
              className={`mb-6 p-4 rounded-2xl text-sm border ${
                eveningMode
                  ? 'bg-amber-950/40 border-amber-800/50 text-amber-100/90'
                  : 'bg-amber-50 border-amber-200 text-amber-900'
              }`}
            >
              אין קונפיגורציית Firebase ב-.env — הנתונים נשמרים בדפדפן בלבד. העתקו{' '}
              <code className="font-mono">.env.example</code> ל-<code className="font-mono">.env</code>{' '}
              ומלאו את מפתחות הפרויקט לסנכרון בזמן אמת.
            </div>
          )}

          {activeTab === 'dashboard' && (
            <div className="space-y-10 animate-in fade-in slide-in-from-bottom-4 duration-700">
              <header className="flex justify-between items-end flex-wrap gap-4">
                <div>
                  <h2
                    className={`text-4xl font-black ${
                      eveningMode ? 'text-amber-50' : 'text-slate-900'
                    }`}
                  >
                    ברוך השם.
                  </h2>
                  <p
                    className={`text-lg mt-2 ${
                      eveningMode ? 'text-amber-200/70' : 'text-slate-500'
                    }`}
                  >
                    המרכז הדיגיטלי להפקת שבת ה-70.
                  </p>
                </div>
                <div className="text-left">
                  <span
                    className={`px-4 py-1 rounded-full text-sm font-bold border ${
                      eveningMode
                        ? 'bg-amber-500/20 text-amber-100 border-amber-500/40'
                        : 'bg-amber-100 text-amber-800 border-amber-200'
                    }`}
                  >
                    הושענא רבה תשפ״ז
                  </span>
                </div>
              </header>

              <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                {[
                  {
                    label: 'משימות',
                    val: data.tasks.length,
                    icon: CheckSquare,
                    color: 'text-indigo-500',
                  },
                  {
                    label: 'אירועים',
                    val: data.schedule.length,
                    icon: Calendar,
                    color: 'text-emerald-500',
                  },
                  {
                    label: 'רעיונות',
                    val: data.ideas.length,
                    icon: Lightbulb,
                    color: 'text-amber-500',
                  },
                  {
                    label: 'סיפורים',
                    val: data.questionnaire.length,
                    icon: Quote,
                    color: 'text-rose-500',
                  },
                ].map((stat) => (
                  <div
                    key={stat.label}
                    className={`p-6 rounded-3xl border shadow-sm ${
                      eveningMode
                        ? 'bg-zinc-900/80 border-amber-900/30 text-amber-50'
                        : 'bg-white border-slate-100'
                    }`}
                  >
                    <stat.icon className={`${stat.color} mb-2`} size={24} />
                    <div className="text-2xl font-black">{stat.val}</div>
                    <div
                      className={`text-sm font-bold ${
                        eveningMode ? 'text-amber-200/70' : 'text-slate-500'
                      }`}
                    >
                      {stat.label}
                    </div>
                  </div>
                ))}
              </div>

              <div
                className={`rounded-[2.5rem] p-10 relative overflow-hidden shadow-2xl border ${
                  eveningMode
                    ? 'bg-gradient-to-br from-zinc-900 to-zinc-950 border-amber-800/40 text-amber-50'
                    : 'bg-indigo-950 text-white border-transparent'
                }`}
              >
                <div className="relative z-10 space-y-4">
                  <div
                    className={`inline-flex items-center gap-2 px-4 py-1 rounded-full border ${
                      eveningMode
                        ? 'bg-amber-500/10 border-amber-500/30'
                        : 'bg-indigo-900/50 border-indigo-800'
                    }`}
                  >
                    <Star size={16} className="text-amber-400 fill-amber-400" />
                    <span className="text-xs font-bold uppercase tracking-widest">
                      הקונספט המוביל
                    </span>
                  </div>
                  <h3 className="text-4xl font-bold italic tracking-tight">
                    &quot;גיבור שקט&quot;
                  </h3>
                  <p
                    className={`max-w-2xl leading-relaxed text-lg font-light ${
                      eveningMode ? 'text-amber-100/85' : 'text-indigo-100/80'
                    }`}
                  >
                    שילוב של גיל גבורות, יום של חיתום, ושורשים משפחתיים של מסירות,
                    תורה, חיבת הארץ והשראה שקטה.
                  </p>
                  <div className="pt-4 flex gap-4 flex-wrap">
                    <div
                      className={`px-4 py-2 rounded-xl border text-sm ${
                        eveningMode
                          ? 'bg-amber-500/10 border-amber-500/25'
                          : 'bg-white/10 border-white/10'
                      }`}
                    >
                      #עומק_מעל_כמות
                    </div>
                    <div
                      className={`px-4 py-2 rounded-xl border text-sm ${
                        eveningMode
                          ? 'bg-amber-500/10 border-amber-500/25'
                          : 'bg-white/10 border-white/10'
                      }`}
                    >
                      #מורשת_חאלב
                    </div>
                  </div>
                </div>
                <Users
                  className={`absolute -right-10 -bottom-10 w-80 h-80 rotate-12 ${
                    eveningMode ? 'text-amber-500/5' : 'text-white/5'
                  }`}
                />
              </div>
            </div>
          )}

          {activeTab === 'portrait' && (
            <div className="space-y-8 animate-in fade-in duration-500">
              <div className="flex items-center gap-4">
                <UtensilsCrossed
                  size={32}
                  className={eveningMode ? 'text-amber-400' : 'text-indigo-600'}
                />
                <h2
                  className={`text-3xl font-bold ${
                    eveningMode ? 'text-amber-50' : 'text-slate-900'
                  }`}
                >
                  דיוקן אבא: המהות שמאחורי האיש
                </h2>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {[
                  {
                    key: 'roots',
                    label: 'שורשים ומשפחה (המזלג)',
                    icon: UtensilsCrossed,
                    ring: eveningMode
                      ? 'bg-amber-500/15 text-amber-300 border border-amber-500/30'
                      : 'bg-amber-50 text-amber-700',
                  },
                  {
                    key: 'character',
                    label: 'אופי ומהפך (המרגרינה)',
                    icon: Heart,
                    ring: eveningMode
                      ? 'bg-rose-500/15 text-rose-200 border border-rose-500/25'
                      : 'bg-rose-50 text-rose-600',
                  },
                  {
                    key: 'torah',
                    label: 'תורה, לוויה וחזנות',
                    icon: ScrollText,
                    ring: eveningMode
                      ? 'bg-sky-500/15 text-sky-200 border border-sky-500/25'
                      : 'bg-sky-50 text-sky-600',
                  },
                  {
                    key: 'art',
                    label: 'אמנות (ינשוף, פימו)',
                    icon: Bird,
                    ring: eveningMode
                      ? 'bg-zinc-700/80 text-amber-100 border border-amber-800/40'
                      : 'bg-slate-100 text-slate-700',
                  },
                ].map((section) => (
                  <div
                    key={section.key}
                    className={`p-8 rounded-[2rem] border shadow-sm group hover:shadow-md transition-all ${
                      eveningMode
                        ? 'bg-zinc-900/90 border-amber-900/35'
                        : 'bg-white border-slate-100'
                    }`}
                  >
                    <div className="flex items-center gap-3 mb-6">
                      <div className={`p-3 rounded-2xl ${section.ring}`}>
                        <section.icon size={24} />
                      </div>
                      <h3
                        className={`font-bold text-xl ${
                          eveningMode ? 'text-amber-50' : 'text-slate-900'
                        }`}
                      >
                        {section.label}
                      </h3>
                    </div>
                    <textarea
                      className={`w-full h-40 p-5 rounded-2xl border-none outline-none resize-none leading-relaxed ${
                        eveningMode
                          ? 'bg-zinc-950 text-amber-50/95 focus:ring-2 focus:ring-amber-500/50'
                          : 'bg-slate-50 text-slate-700 focus:ring-2 focus:ring-indigo-500'
                      }`}
                      value={data.portrait[section.key]}
                      onChange={(e) =>
                        handleUpdate(`portrait.${section.key}`, e.target.value)
                      }
                      placeholder="הכניסו תובנות על דמותו..."
                    />
                  </div>
                ))}
              </div>
            </div>
          )}

          {activeTab === 'schedule' && (
            <div className="space-y-8 animate-in slide-in-from-left duration-500">
              <div className="flex justify-between items-center flex-wrap gap-4">
                <div className="flex items-center gap-4">
                  <Calendar
                    size={32}
                    className={eveningMode ? 'text-amber-400' : 'text-indigo-600'}
                  />
                  <h2
                    className={`text-3xl font-bold ${
                      eveningMode ? 'text-amber-50' : 'text-slate-900'
                    }`}
                  >
                    לו&quot;ז השבת המתוכנן
                  </h2>
                </div>
                <button
                  type="button"
                  onClick={() =>
                    addItem('schedule', {
                      time: '',
                      activity: '',
                      lead: '',
                      content: '',
                    })
                  }
                  className={`px-6 py-3 rounded-2xl font-bold shadow-lg transition-all flex items-center gap-2 ${
                    eveningMode
                      ? 'bg-amber-600 hover:bg-amber-500 text-zinc-950'
                      : 'bg-indigo-600 hover:bg-indigo-700 text-white'
                  }`}
                >
                  <Plus size={20} />
                  הוסף תחנה
                </button>
              </div>

              <div
                className={`rounded-[2rem] overflow-hidden border shadow-sm ${
                  eveningMode
                    ? 'bg-zinc-900/90 border-amber-900/35'
                    : 'bg-white border-slate-100'
                }`}
              >
                <table className="w-full text-right border-collapse">
                  <thead>
                    <tr
                      className={
                        eveningMode
                          ? 'bg-zinc-800/80 border-b border-amber-900/30'
                          : 'bg-slate-50/80 border-b border-slate-100'
                      }
                    >
                      {['זמן', 'פעילות', 'אחראי', 'תוכן / דגשים', ''].map(
                        (h) => (
                          <th
                            key={h || 'x'}
                            className={`p-6 font-bold text-sm uppercase tracking-wider ${
                              eveningMode ? 'text-amber-200/70' : 'text-slate-500'
                            }`}
                          >
                            {h}
                          </th>
                        ),
                      )}
                    </tr>
                  </thead>
                  <tbody
                    className={
                      eveningMode ? 'divide-y divide-amber-900/20' : 'divide-y divide-slate-50'
                    }
                  >
                    {data.schedule.map((item) => (
                      <tr
                        key={item.id}
                        className={
                          eveningMode
                            ? 'hover:bg-amber-500/5 transition-colors group'
                            : 'hover:bg-indigo-50/30 transition-colors group'
                        }
                      >
                        <td className="p-4">
                          <input
                            className={`bg-transparent w-full font-medium outline-none ${
                              eveningMode ? 'text-amber-50' : ''
                            }`}
                            value={item.time}
                            onChange={(e) => {
                              const newList = data.schedule.map((s) =>
                                s.id === item.id
                                  ? { ...s, time: e.target.value }
                                  : s,
                              );
                              handleUpdate('schedule', newList);
                            }}
                          />
                        </td>
                        <td className="p-4">
                          <input
                            className={`bg-transparent w-full font-bold underline decoration-indigo-200 underline-offset-4 tracking-tight outline-none ${
                              eveningMode
                                ? 'text-amber-100 decoration-amber-700'
                                : 'text-indigo-900'
                            }`}
                            value={item.activity}
                            onChange={(e) => {
                              const newList = data.schedule.map((s) =>
                                s.id === item.id
                                  ? { ...s, activity: e.target.value }
                                  : s,
                              );
                              handleUpdate('schedule', newList);
                            }}
                          />
                        </td>
                        <td className="p-4">
                          <input
                            className={`bg-transparent w-full text-sm outline-none ${
                              eveningMode ? 'text-amber-100/90' : ''
                            }`}
                            value={item.lead}
                            onChange={(e) => {
                              const newList = data.schedule.map((s) =>
                                s.id === item.id
                                  ? { ...s, lead: e.target.value }
                                  : s,
                              );
                              handleUpdate('schedule', newList);
                            }}
                          />
                        </td>
                        <td className="p-4">
                          <input
                            className={`bg-transparent w-full italic outline-none ${
                              eveningMode ? 'text-amber-200/75' : 'text-slate-500'
                            }`}
                            value={item.content}
                            onChange={(e) => {
                              const newList = data.schedule.map((s) =>
                                s.id === item.id
                                  ? { ...s, content: e.target.value }
                                  : s,
                              );
                              handleUpdate('schedule', newList);
                            }}
                          />
                        </td>
                        <td className="p-4 w-20">
                          <button
                            type="button"
                            onClick={() => deleteItem('schedule', item.id)}
                            className={`p-2 opacity-0 group-hover:opacity-100 transition-opacity ${
                              eveningMode
                                ? 'text-zinc-600 hover:text-red-400'
                                : 'text-slate-200 hover:text-red-500'
                            }`}
                          >
                            <Trash2 size={18} />
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {activeTab === 'ideas' && (
            <IdeasTab
              data={data}
              eveningMode={eveningMode}
              isEditor={isEditor}
              configuredEditorKey={configuredEditorKey}
              handleUpdate={handleUpdate}
              addItem={addItem}
              deleteItem={deleteItem}
            />
          )}

          {activeTab === 'survey' && (
            <div className="space-y-8 animate-in fade-in duration-500">
              <div className="flex items-center gap-4">
                <MessageSquare
                  size={32}
                  className={eveningMode ? 'text-rose-300' : 'text-rose-500'}
                />
                <h2
                  className={`text-3xl font-bold ${
                    eveningMode ? 'text-amber-50' : 'text-slate-900'
                  }`}
                >
                  מאגר שאלות ל&quot;איסוף סיפורים&quot;
                </h2>
              </div>
              <div
                className={`p-10 rounded-[2.5rem] border shadow-sm ${
                  eveningMode
                    ? 'bg-zinc-900/90 border-amber-900/35'
                    : 'bg-white border-slate-100'
                }`}
              >
                <p
                  className={`mb-8 font-medium italic ${
                    eveningMode ? 'text-amber-200/80' : 'text-slate-600'
                  }`}
                >
                  &quot;המטרה: להוציא מאנשים תוכן אמיתי, לא תשובות גנריות.&quot;
                </p>
                <div className="space-y-6">
                  {data.questionnaire.map((q) => (
                    <div
                      key={q.id}
                      className={`flex gap-6 p-6 rounded-3xl items-start group ${
                        eveningMode ? 'bg-zinc-950/80' : 'bg-slate-50'
                      }`}
                    >
                      <div
                        className={`px-3 py-1 rounded-full text-[10px] font-black mt-1 shrink-0 ${
                          eveningMode
                            ? 'bg-amber-500/20 text-amber-200'
                            : 'bg-indigo-100 text-indigo-700'
                        }`}
                      >
                        {q.target}
                      </div>
                      <input
                        className={`flex-1 bg-transparent border-none outline-none font-bold ${
                          eveningMode ? 'text-amber-50' : 'text-slate-800'
                        }`}
                        value={q.question}
                        onChange={(e) => {
                          const newList = data.questionnaire.map((item) =>
                            item.id === q.id
                              ? { ...item, question: e.target.value }
                              : item,
                          );
                          handleUpdate('questionnaire', newList);
                        }}
                      />
                      <button
                        type="button"
                        onClick={() => deleteItem('questionnaire', q.id)}
                        className={`opacity-0 group-hover:opacity-100 transition-all shrink-0 ${
                          eveningMode
                            ? 'text-zinc-600 hover:text-red-400'
                            : 'text-slate-300 hover:text-red-500'
                        }`}
                      >
                        <Trash2 size={18} />
                      </button>
                    </div>
                  ))}
                  <button
                    type="button"
                    onClick={() =>
                      addItem('questionnaire', { target: 'קהל', question: '' })
                    }
                    className={`w-full py-4 border-2 border-dashed rounded-3xl font-bold transition-all ${
                      eveningMode
                        ? 'border-amber-800/50 text-amber-200/60 hover:bg-amber-500/5'
                        : 'border-slate-200 text-slate-400 hover:bg-slate-50'
                    }`}
                  >
                    + הוסף שאלה למאגר
                  </button>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'prompt' && (
            <div className="space-y-8 animate-in fade-in duration-500">
              <div className="flex items-center gap-4 flex-wrap">
                <Sparkles
                  size={32}
                  className={eveningMode ? 'text-amber-300' : 'text-violet-600'}
                />
                <h2
                  className={`text-3xl font-bold ${
                    eveningMode ? 'text-amber-50' : 'text-slate-900'
                  }`}
                >
                  מחולל הנחיות לטריילר (AI)
                </h2>
              </div>
              <p
                className={`text-sm leading-relaxed max-w-3xl ${
                  eveningMode ? 'text-amber-200/75' : 'text-slate-600'
                }`}
              >
                נוצר אוטומטית מדיוקן אבא. הדביקו ב-Runway, Luma, או כל כלי AI
                לווידאו/קריינות — וערכו לפי הצורך.
              </p>
              <div
                className={`rounded-[2rem] border shadow-sm overflow-hidden ${
                  eveningMode
                    ? 'bg-zinc-900/90 border-amber-900/35'
                    : 'bg-white border-slate-100'
                }`}
              >
                <div
                  className={`flex items-center justify-between gap-3 px-6 py-4 border-b ${
                    eveningMode
                      ? 'border-amber-900/30 bg-zinc-950/50'
                      : 'border-slate-100 bg-slate-50/80'
                  }`}
                >
                  <span className="font-bold text-sm">Prompt מוכן</span>
                  <button
                    type="button"
                    onClick={copyPrompt}
                    className={`flex items-center gap-2 px-4 py-2 rounded-xl font-bold text-sm transition-all ${
                      eveningMode
                        ? 'bg-amber-500/20 text-amber-100 hover:bg-amber-500/30'
                        : 'bg-indigo-600 text-white hover:bg-indigo-700'
                    }`}
                  >
                    {promptCopied ? (
                      <Check size={18} />
                    ) : (
                      <Copy size={18} />
                    )}
                    {promptCopied ? 'הועתק' : 'העתק ללוח'}
                  </button>
                </div>
                <pre
                  className={`p-6 text-sm whitespace-pre-wrap leading-relaxed overflow-x-auto font-mono ${
                    eveningMode ? 'text-amber-100/90' : 'text-slate-700'
                  }`}
                >
                  {trailerPrompt}
                </pre>
              </div>
            </div>
          )}

          {activeTab === 'grandkids' && (
            <GrandkidsTab
              data={data}
              eveningMode={eveningMode}
              handleUpdate={handleUpdate}
            />
          )}

          {activeTab === 'tasks' && (
            <div className="space-y-8 animate-in slide-in-from-right duration-500">
              <div className="flex justify-between items-center flex-wrap gap-4">
                <div className="flex items-center gap-4">
                  <CheckSquare
                    size={32}
                    className={eveningMode ? 'text-amber-400' : 'text-indigo-600'}
                  />
                  <h2
                    className={`text-3xl font-bold ${
                      eveningMode ? 'text-amber-50' : 'text-slate-900'
                    }`}
                  >
                    משימות וחלוקת עבודה
                  </h2>
                </div>
                <button
                  type="button"
                  onClick={() =>
                    addItem('tasks', {
                      title: '',
                      date: '',
                      status: 'todo',
                      owner: '',
                    })
                  }
                  className={`px-6 py-3 rounded-2xl font-bold shadow-lg ${
                    eveningMode
                      ? 'bg-amber-600 text-zinc-950 hover:bg-amber-500'
                      : 'bg-indigo-600 text-white hover:bg-indigo-700'
                  }`}
                >
                  הוסף משימה
                </button>
              </div>
              <div className="space-y-3">
                {data.tasks.map((task) => (
                  <div
                    key={task.id}
                    className={`p-5 rounded-2xl border shadow-sm flex items-center gap-5 group flex-wrap ${
                      eveningMode
                        ? 'bg-zinc-900/90 border-amber-900/35'
                        : 'bg-white border-slate-100'
                    }`}
                  >
                    <button
                      type="button"
                      onClick={() => {
                        const next =
                          task.status === 'done' ? 'todo' : 'done';
                        const newList = data.tasks.map((t) =>
                          t.id === task.id ? { ...t, status: next } : t,
                        );
                        handleUpdate('tasks', newList);
                      }}
                      title="חיתום השלמה"
                      className={`shrink-0 w-10 h-10 rounded-full border-2 flex items-center justify-center text-lg font-serif transition-all ${
                        task.status === 'done'
                          ? eveningMode
                            ? 'border-amber-400 bg-amber-500/20 text-amber-200'
                            : 'border-amber-600 bg-amber-50 text-amber-800'
                          : eveningMode
                            ? 'border-amber-800/60 text-amber-200/40 hover:border-amber-500'
                            : 'border-slate-200 text-slate-300 hover:border-amber-300'
                      }`}
                    >
                      {task.status === 'done' ? '✶' : ''}
                    </button>
                    <input
                      className={`flex-1 min-w-[200px] font-bold text-lg bg-transparent border-none outline-none ${
                        task.status === 'done'
                          ? eveningMode
                            ? 'line-through text-amber-200/35'
                            : 'line-through text-slate-300'
                          : eveningMode
                            ? 'text-amber-50'
                            : 'text-slate-800'
                      }`}
                      value={task.title}
                      onChange={(e) => {
                        const newList = data.tasks.map((t) =>
                          t.id === task.id
                            ? { ...t, title: e.target.value }
                            : t,
                        );
                        handleUpdate('tasks', newList);
                      }}
                      placeholder="משימה חדשה..."
                    />
                    <div className="flex items-center gap-3 flex-wrap">
                      <span
                        className={`text-[10px] font-black px-3 py-1 rounded-full ${
                          eveningMode
                            ? 'bg-amber-500/15 text-amber-200'
                            : 'bg-indigo-50 text-indigo-600'
                        }`}
                      >
                        {task.owner || 'ללא אחראי'}
                      </span>
                      <input
                        type="date"
                        className={`text-xs bg-transparent outline-none ${
                          eveningMode ? 'text-amber-200/70' : 'text-slate-400'
                        }`}
                        value={task.date}
                        onChange={(e) => {
                          const newList = data.tasks.map((t) =>
                            t.id === task.id
                              ? { ...t, date: e.target.value }
                              : t,
                          );
                          handleUpdate('tasks', newList);
                        }}
                      />
                      <button
                        type="button"
                        onClick={() => deleteItem('tasks', task.id)}
                        className={`transition-colors opacity-0 group-hover:opacity-100 ${
                          eveningMode
                            ? 'text-zinc-600 hover:text-red-400'
                            : 'text-slate-200 hover:text-red-500'
                        }`}
                      >
                        <Trash2 size={18} />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  );
};

function IdeasTab({
  data,
  eveningMode,
  isEditor,
  configuredEditorKey,
  handleUpdate,
  addItem,
  deleteItem,
}) {
  const statusBadge = (status) => {
    if (status === 'approved') {
      return eveningMode
        ? 'bg-emerald-500/20 text-emerald-200 border border-emerald-500/30'
        : 'bg-emerald-100 text-emerald-700';
    }
    if (status === 'planning') {
      return eveningMode
        ? 'bg-amber-500/15 text-amber-100 border border-amber-500/25'
        : 'bg-amber-100 text-amber-700';
    }
    return eveningMode
      ? 'bg-zinc-800 text-amber-200/70 border border-amber-900/30'
      : 'bg-slate-100 text-slate-600';
  };

  const statusLabel = (status) => {
    if (status === 'approved') return 'מאושר';
    if (status === 'planning') return 'בהמתנה לאישור';
    return 'טיוטה';
  };

  const updateIdea = (id, patch) => {
    const newList = data.ideas.map((i) =>
      i.id === id ? { ...i, ...patch } : i,
    );
    handleUpdate('ideas', newList);
  };

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      <div className="flex justify-between items-center flex-wrap gap-4">
        <div className="flex items-center gap-4">
          <Lightbulb
            size={32}
            className={eveningMode ? 'text-amber-300' : 'text-amber-500'}
          />
          <h2
            className={`text-3xl font-bold ${
              eveningMode ? 'text-amber-50' : 'text-slate-900'
            }`}
          >
            רעיונות &quot;קומה 2&quot; ושדרוגים
          </h2>
        </div>
        <button
          type="button"
          onClick={() =>
            addItem('ideas', {
              title: '',
              detail: '',
              status: 'draft',
              locked: false,
            })
          }
          className={`px-6 py-3 rounded-2xl font-bold shadow-lg transition-all flex items-center gap-2 ${
            eveningMode
              ? 'bg-amber-600 hover:bg-amber-500 text-zinc-950'
              : 'bg-amber-500 hover:bg-amber-600 text-white'
          }`}
        >
          <Plus size={20} />
          רעיון חדש
        </button>
      </div>

      {configuredEditorKey && !isEditor && (
        <p
          className={`text-sm rounded-2xl px-4 py-3 border ${
            eveningMode
              ? 'bg-zinc-900/80 border-amber-900/40 text-amber-100/85'
              : 'bg-amber-50 border-amber-200 text-amber-900'
          }`}
        >
          שליחה לאישור ונעילה זמינות רק לעורך הראשי (מפתח בסרגל).
        </p>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {data.ideas.map((idea) => {
          const locked = Boolean(idea.locked);
          const canEditFields = !locked || isEditor;
          const canDelete = !locked || isEditor;

          return (
            <div
              key={idea.id}
              className={`p-8 rounded-[2rem] border shadow-sm flex flex-col transition-all group ${
                eveningMode
                  ? 'bg-zinc-900/90 border-amber-900/35 hover:border-amber-700/50'
                  : 'bg-white border-slate-100 hover:border-amber-200'
              }`}
            >
              <div className="flex justify-between items-start mb-4 gap-2 flex-wrap">
                <div className="flex flex-wrap gap-2 items-center">
                  <span
                    className={`px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-widest ${statusBadge(
                      idea.status,
                    )}`}
                  >
                    {statusLabel(idea.status)}
                  </span>
                  {locked && (
                    <span
                      className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-[10px] font-bold ${
                        eveningMode
                          ? 'bg-zinc-800 text-amber-200/90 border border-amber-800/40'
                          : 'bg-slate-800 text-amber-100'
                      }`}
                    >
                      <Lock size={12} />
                      נעול
                    </span>
                  )}
                </div>
                {canDelete && (
                  <button
                    type="button"
                    onClick={() => deleteItem('ideas', idea.id)}
                    className={
                      eveningMode
                        ? 'text-zinc-600 hover:text-red-400'
                        : 'text-slate-200 hover:text-red-500'
                    }
                  >
                    <Trash2 size={16} />
                  </button>
                )}
              </div>

              <input
                className={`text-xl font-bold bg-transparent border-none outline-none mb-3 ${
                  eveningMode ? 'text-amber-50' : ''
                } ${!canEditFields ? 'opacity-60 cursor-not-allowed' : ''}`}
                value={idea.title}
                disabled={!canEditFields}
                onChange={(e) => updateIdea(idea.id, { title: e.target.value })}
              />
              <textarea
                className={`flex-1 p-4 rounded-xl border-none outline-none text-sm resize-none leading-relaxed min-h-[120px] ${
                  eveningMode
                    ? 'bg-zinc-950 text-amber-100/85'
                    : 'bg-slate-50/50 text-slate-600'
                } ${!canEditFields ? 'opacity-60 cursor-not-allowed' : ''}`}
                value={idea.detail}
                disabled={!canEditFields}
                onChange={(e) =>
                  updateIdea(idea.id, { detail: e.target.value })
                }
              />

              <div className="mt-4 flex flex-col gap-2">
                {idea.status === 'draft' && (
                  <button
                    type="button"
                    disabled={locked && !isEditor}
                    onClick={() =>
                      updateIdea(idea.id, { status: 'planning' })
                    }
                    className={`w-full py-2 rounded-xl text-xs font-bold flex items-center justify-center gap-2 border transition-all ${
                      eveningMode
                        ? 'border-amber-800/50 text-amber-100 hover:bg-amber-500/10 disabled:opacity-40'
                        : 'border-slate-200 text-slate-600 hover:bg-slate-50 disabled:opacity-40'
                    }`}
                  >
                    <Send size={14} />
                    שלח לאישור אופיר
                  </button>
                )}
                {isEditor && idea.status === 'planning' && (
                  <button
                    type="button"
                    onClick={() =>
                      updateIdea(idea.id, { status: 'approved' })
                    }
                    className={`w-full py-2 rounded-xl text-xs font-bold ${
                      eveningMode
                        ? 'bg-emerald-600/90 text-white hover:bg-emerald-500'
                        : 'bg-emerald-600 text-white hover:bg-emerald-700'
                    }`}
                  >
                    אשר רעיון
                  </button>
                )}
                {isEditor && (
                  <button
                    type="button"
                    onClick={() =>
                      updateIdea(idea.id, { locked: !locked })
                    }
                    className={`w-full py-2 rounded-xl text-xs font-bold flex items-center justify-center gap-2 border ${
                      eveningMode
                        ? 'border-amber-800/50 text-amber-100 hover:bg-amber-500/10'
                        : 'border-slate-200 text-slate-600 hover:bg-slate-50'
                    }`}
                  >
                    {locked ? <Unlock size={14} /> : <Lock size={14} />}
                    {locked ? 'בטל נעילה' : 'נעל ויז׳ן (עורך)'}
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function GrandkidsTab({ data, eveningMode, handleUpdate }) {
  const [name, setName] = useState('');
  const [note, setNote] = useState('');
  const [recState, setRecState] = useState('idle');
  const mediaRecorderRef = useRef(null);
  const chunksRef = useRef([]);
  const [localUrl, setLocalUrl] = useState(null);

  useEffect(() => {
    return () => {
      if (localUrl) URL.revokeObjectURL(localUrl);
    };
  }, [localUrl]);

  const startRec = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mr = new MediaRecorder(stream);
      mediaRecorderRef.current = mr;
      chunksRef.current = [];
      mr.ondataavailable = (e) => {
        if (e.data.size) chunksRef.current.push(e.data);
      };
      mr.onstop = () => {
        stream.getTracks().forEach((t) => t.stop());
        const blob = new Blob(chunksRef.current, {
          type: mr.mimeType || 'audio/webm',
        });
        if (localUrl) URL.revokeObjectURL(localUrl);
        const url = URL.createObjectURL(blob);
        setLocalUrl(url);
        setRecState('stopped');
      };
      mr.start();
      setRecState('recording');
    } catch (e) {
      console.error(e);
      alert('לא ניתן להקליט — בדקו הרשאת מיקרופון.');
    }
  };

  const stopRec = () => {
    const mr = mediaRecorderRef.current;
    if (mr && mr.state !== 'inactive') mr.stop();
  };

  const downloadRec = () => {
    if (!localUrl) return;
    const a = document.createElement('a');
    a.href = localUrl;
    a.download = `ברכה-לסבא-${Date.now()}.webm`;
    a.click();
  };

  const addNote = () => {
    const text = note.trim();
    if (!text) return;
    const item = {
      id: Date.now().toString(),
      name: name.trim() || 'נכד/ה',
      text,
      createdAt: new Date().toISOString(),
    };
    const next = [...(data.grandkidsNotes || []), item];
    handleUpdate('grandkidsNotes', next);
    setNote('');
  };

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      <div className="flex items-center gap-4">
        <Baby
          size={32}
          className={eveningMode ? 'text-amber-300' : 'text-pink-500'}
        />
        <h2
          className={`text-3xl font-bold ${
            eveningMode ? 'text-amber-50' : 'text-slate-900'
          }`}
        >
          אזור נכדים
        </h2>
      </div>
      <p
        className={`text-sm leading-relaxed max-w-2xl ${
          eveningMode ? 'text-amber-200/75' : 'text-slate-600'
        }`}
      >
        ממשק פשוט: ברכה קצרה נשמרת כאן לסנכרון עם המשפחה. הקלטה נשארת במכשיר —
        אפשר להוריד קובץ ולשלוח בווטסאפ (מומלץ עד שנחבר איסוף אוטומטי).
      </p>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div
          className={`p-8 rounded-[2rem] border shadow-sm space-y-4 ${
            eveningMode
              ? 'bg-zinc-900/90 border-amber-900/35'
              : 'bg-white border-slate-100'
          }`}
        >
          <h3 className="font-bold flex items-center gap-2">
            <Mic size={18} />
            הקלטה מקומית
          </h3>
          <div className="flex flex-wrap gap-2">
            {recState !== 'recording' ? (
              <button
                type="button"
                onClick={startRec}
                className={`px-4 py-2 rounded-xl font-bold text-sm ${
                  eveningMode
                    ? 'bg-rose-500/20 text-rose-100 hover:bg-rose-500/30'
                    : 'bg-rose-500 text-white hover:bg-rose-600'
                }`}
              >
                התחל הקלטה
              </button>
            ) : (
              <button
                type="button"
                onClick={stopRec}
                className={`px-4 py-2 rounded-xl font-bold text-sm ${
                  eveningMode
                    ? 'bg-zinc-800 text-amber-100 border border-amber-800/50'
                    : 'bg-slate-800 text-white'
                }`}
              >
                עצור
              </button>
            )}
            <button
              type="button"
              disabled={!localUrl}
              onClick={downloadRec}
              className={`px-4 py-2 rounded-xl font-bold text-sm flex items-center gap-2 border disabled:opacity-40 ${
                eveningMode
                  ? 'border-amber-800/50 text-amber-100'
                  : 'border-slate-200 text-slate-700'
              }`}
            >
              <Download size={16} />
              הורד קובץ
            </button>
          </div>
          {localUrl && (
            <audio controls src={localUrl} className="w-full mt-2" />
          )}
        </div>

        <div
          className={`p-8 rounded-[2rem] border shadow-sm space-y-4 ${
            eveningMode
              ? 'bg-zinc-900/90 border-amber-900/35'
              : 'bg-white border-slate-100'
          }`}
        >
          <h3 className="font-bold">ברכה לסבא (טקסט)</h3>
          <input
            placeholder="שם (אופציונלי)"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className={`w-full rounded-xl px-4 py-3 border outline-none ${
              eveningMode
                ? 'bg-zinc-950 border-amber-900/40 text-amber-50'
                : 'bg-slate-50 border-slate-200'
            }`}
          />
          <textarea
            placeholder="משפט או שניים מהלב..."
            value={note}
            onChange={(e) => setNote(e.target.value)}
            rows={4}
            className={`w-full rounded-xl px-4 py-3 border outline-none resize-none ${
              eveningMode
                ? 'bg-zinc-950 border-amber-900/40 text-amber-50'
                : 'bg-slate-50 border-slate-200'
            }`}
          />
          <button
            type="button"
            onClick={addNote}
            className={`w-full py-3 rounded-xl font-bold ${
              eveningMode
                ? 'bg-amber-600 text-zinc-950 hover:bg-amber-500'
                : 'bg-indigo-600 text-white hover:bg-indigo-700'
            }`}
          >
            שמור לרשימה המשותפת
          </button>
        </div>
      </div>

      <div
        className={`rounded-[2rem] border p-8 ${
          eveningMode
            ? 'bg-zinc-900/80 border-amber-900/35'
            : 'bg-white border-slate-100'
        }`}
      >
        <h3 className="font-bold mb-4">ברכות שנשמרו</h3>
        <div className="space-y-3">
          {(data.grandkidsNotes || []).length === 0 && (
            <p
              className={
                eveningMode ? 'text-amber-200/60 text-sm' : 'text-slate-400 text-sm'
              }
            >
              עדיין אין — זה המקום שבו יתאסף החומר לקראת המצגות.
            </p>
          )}
          {(data.grandkidsNotes || []).map((g) => (
            <div
              key={g.id}
              className={`p-4 rounded-2xl flex justify-between gap-4 items-start ${
                eveningMode ? 'bg-zinc-950/80' : 'bg-slate-50'
              }`}
            >
              <div>
                <div className="text-xs font-black opacity-70 mb-1">
                  {g.name}
                </div>
                <div className="leading-relaxed">{g.text}</div>
              </div>
              <button
                type="button"
                onClick={() =>
                  handleUpdate(
                    'grandkidsNotes',
                    (data.grandkidsNotes || []).filter((x) => x.id !== g.id),
                  )
                }
                className={
                  eveningMode
                    ? 'text-zinc-600 hover:text-red-400 shrink-0'
                    : 'text-slate-300 hover:text-red-500 shrink-0'
                }
              >
                <Trash2 size={16} />
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export default App;
