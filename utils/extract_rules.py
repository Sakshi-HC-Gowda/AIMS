# utils/extract_rules.py
import re
from collections import Counter, defaultdict
from math import log

# ------------------------------------------
# 🧩 Improved Stopwords and Helpers
# ------------------------------------------
BASE_STOPWORDS = {
    'the','and','for','with','that','this','from','are','was','were','have','has','will','shall','should',
    'to','of','in','on','we','he','she','they','it','is','as','by','an','a','at','be','been','or','not','if','but',
    'i','you','your','our','us','me','my','mine','them','their','they','so','just','also','do','did','does',
    'yeah','yes','no','okay','ok','thanks','thank','everyone','all','right','alright','really','actually','good',
    'can','could','would','may','might','also','still','maybe','please','let','lets','let\'s','hello','hi'
}

SENT_SPLIT_RE = re.compile(r'[.!?;\n]')
PHRASE_SPLIT_RE = re.compile(r'[\s,:\-\(\)\[\]\/]+')

def build_stopwords(extra=None):
    s = set(BASE_STOPWORDS)
    if extra:
        s.update(w.lower().strip() for w in extra)
    return s

def is_filler(token, stopwords):
    t = token.lower()
    return (t in stopwords) or (len(t) <= 2) or (not re.match(r'^[a-zA-Z0-9\-]+$', t))

def extract_candidate_phrases(text, stopwords):
    text_norm = text.replace('\n', ' ')
    sentences = SENT_SPLIT_RE.split(text_norm)
    phrases = []
    for sent in sentences:
        tokens = PHRASE_SPLIT_RE.split(sent)
        current = []
        for tok in tokens:
            if not tok:
                continue
            if is_filler(tok, stopwords):
                if current:
                    phrases.append(" ".join(current))
                    current = []
            else:
                current.append(tok)
        if current:
            phrases.append(" ".join(current))
    return phrases

def rake_keywords(text, top_n=6, extra_stopwords=None):
    stopwords = build_stopwords(extra_stopwords)
    cand_phrases = extract_candidate_phrases(text, stopwords)
    if not cand_phrases:
        return []
    word_freq = Counter()
    word_degree = defaultdict(int)
    phrase_words = []
    for phrase in cand_phrases:
        words = [w.lower() for w in PHRASE_SPLIT_RE.split(phrase) if w and not is_filler(w, stopwords)]
        if not words:
            continue
        phrase_words.append(words)
        length = len(words)
        for w in words:
            word_freq[w] += 1
            word_degree[w] += (length - 1)
    word_score = {w: (word_degree[w] + word_freq[w]) / max(1, word_freq[w]) for w in word_freq}
    phrase_scores = {}
    for words in phrase_words:
        score = sum(word_score.get(w, 0) for w in words)
        phrase = " ".join(words)
        norm_score = score / (1 + 0.1 * (len(words)-1))
        phrase_scores[phrase] = max(phrase_scores.get(phrase, 0), norm_score)
    sorted_phrases = sorted(phrase_scores.items(), key=lambda x: x[1], reverse=True)
    filtered = []
    seen = set()
    for phrase, sc in sorted_phrases:
        if len(filtered) >= top_n:
            break
        if re.match(r'^[0-9\W]+$', phrase): continue
        if phrase in seen or len(phrase) < 3: continue
        filtered.append(phrase)
        seen.add(phrase)
    if len(filtered) < top_n:
        single_words = [w for w,_ in Counter([w for ph in phrase_words for w in ph]).most_common(20)]
        for w in single_words:
            if len(filtered) >= top_n:
                break
            if w in seen or is_filler(w, stopwords): continue
            filtered.append(w)
            seen.add(w)
    return filtered[:top_n]

# ------------------------------------------
# Core Extraction (used by Flask app)
# ------------------------------------------

DECISION_CUES = ['decided', 'agreed', 'approved', 'concluded', 'finalized', 'resolved']
ACTION_CUES = ['will', 'shall', 'should', 'must', 'to do', 'responsible', 'assign', 'complete', 'finish', 'submit']

def split_sentences(text):
    return [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if s.strip()]

def extract_person(text):
    m = re.search(r'\b[A-Z][a-z]+:', text)
    return m.group(0).replace(':', '') if m else None

def extract_date(text):
    date_pattern = r'\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s*\d{1,2}(?:,\s*\d{4})?)\b'
    m = re.search(date_pattern, text)
    return m.group(0) if m else None

def extract_from_brat(text, entities=None, relations=None):
    if not text.strip():
        return {"summary": "No content provided", "key_topics": [], "decisions": [], "actions": []}

    sentences = split_sentences(text)

    # --- Detect decisions ---
    decisions = [s for s in sentences if any(cue in s.lower() for cue in DECISION_CUES)]

    # --- Detect actions ---
    actions = []
    for s in sentences:
        if any(c in s.lower() for c in ACTION_CUES):
            actions.append({
                "task": s,
                "person": extract_person(s),
                "due": extract_date(s),
                "raw": s
            })

    # --- Create summary (simple heuristic) ---
    top_sentences = []
    for s in sentences:
        if any(c in s.lower() for c in DECISION_CUES + ACTION_CUES):
            top_sentences.append(s)
    if not top_sentences:
        top_sentences = sentences[:3]
    summary = " ".join(top_sentences)
    if len(summary) > 700:
        summary = summary[:700].rsplit('.', 1)[0] + '.'

    # --- Extract key topics using improved RAKE ---
    key_topics = rake_keywords(text, top_n=6)

    return {
        "summary": summary,
        "key_topics": key_topics,
        "decisions": decisions,
        "actions": actions
    }