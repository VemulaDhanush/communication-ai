from flask import Flask, request, jsonify
from flask_cors import CORS
import re
import requests
from textblob import TextBlob
from collections import Counter

app = Flask(__name__)
CORS(app)

# ---------------- UTIL FUNCTIONS ---------------- #

def calculate_confidence(word_count):
    if word_count > 80:
        return "High"
    elif word_count > 40:
        return "Medium"
    else:
        return "Low"


def calculate_level(score):
    if score >= 85:
        return "Expert"
    elif score >= 70:
        return "Advanced"
    elif score >= 50:
        return "Intermediate"
    else:
        return "Beginner"


def check_grammar(text):
    try:
        url = "https://api.languagetool.org/v2/check"
        data = {
            "text": text,
            "language": "en-US"
        }

        response = requests.post(url, data=data, timeout=5)
        result = response.json()

        errors = result.get("matches", [])
        error_count = len(errors)

        grammar_score = max(20 - error_count * 2, 0)

        return grammar_score, error_count

    except:
        return 15, 0


def generate_suggestions(score, filler_count, word_count, grammar_errors):
    suggestions = []

    if word_count < 30:
        suggestions.append("Try to give more detailed answers.")

    if filler_count > 3:
        suggestions.append("Reduce filler words like um, uh, like.")

    if grammar_errors > 2:
        suggestions.append("Improve grammar and sentence correctness.")

    if score < 50:
        suggestions.append("Work on sentence clarity and structure.")
    elif score < 70:
        suggestions.append("Improve explanation depth and confidence.")
    else:
        suggestions.append("Excellent performance. Maintain consistency.")

    return suggestions


# ---------------- ENGLISH ANALYSIS ---------------- #



def analyze_english(text):

    base_score = 30
    words = text.split()
    word_count = len(words)

    # ---------------- LENGTH SCORE ----------------
    length_score = 0
    if word_count > 80:
        length_score = 20
    elif word_count > 40:
        length_score = 10

    # ---------------- STRUCTURE SCORE ----------------
    sentences = [s for s in re.split(r'[.!?]', text) if s.strip()]
    structure_score = 10 if len(sentences) >= 3 else 0

    # ---------------- FILLER DETECTION ----------------
    filler_words = ["um", "uh", "like", "basically", "actually"]
    filler_count = sum(
        len(re.findall(r'\b' + f + r'\b', text.lower()))
        for f in filler_words
    )
    filler_penalty = filler_count * 2

    # ---------------- GRAMMAR CHECK ----------------
    grammar_score, grammar_errors = check_grammar(text)

    # ---------------- SENTIMENT ANALYSIS ----------------
    blob = TextBlob(text)
    polarity = blob.sentiment.polarity

    if polarity > 0.2:
        sentiment = "Positive"
        sentiment_score = 10
    elif polarity < -0.2:
        sentiment = "Negative"
        sentiment_score = 5
    else:
        sentiment = "Neutral"
        sentiment_score = 7

    # ---------------- VOCABULARY RICHNESS ----------------
    unique_words = len(set(words))
    vocab_ratio = unique_words / word_count if word_count > 0 else 0
    vocabulary_score = round(vocab_ratio * 10, 1)

    # ---------------- REPETITION DETECTION ----------------
    word_freq = Counter(words)
    repeated_words = [word for word, count in word_freq.items() if count > 3]

    repetition_penalty = len(repeated_words) * 2

    # ---------------- FINAL SCORE ----------------
    total_score = (
        base_score
        + length_score
        + structure_score
        + grammar_score
        + sentiment_score
        + vocabulary_score
        - filler_penalty
        - repetition_penalty
    )

    total_score = max(min(round(total_score), 100), 0)

    confidence = calculate_confidence(word_count)
    level = calculate_level(total_score)

    suggestions = generate_suggestions(
        total_score,
        filler_count,
        word_count,
        grammar_errors
    )

    if repeated_words:
        suggestions.append("Avoid repeating words frequently.")

    return {
        "overall_score": total_score,
        "length_score": length_score,
        "structure_score": structure_score,
        "grammar_score": grammar_score,
        "grammar_errors": grammar_errors,
        "filler_penalty": -filler_penalty,
        "sentiment": sentiment,
        "vocabulary_score": vocabulary_score,
        "repetition_penalty": -repetition_penalty,
        "confidence": confidence,
        "level": level,
        "suggestions": suggestions
    }
# ---------------- HR ANALYSIS ---------------- #

def analyze_hr(text):
    return analyze_english(text)


# ---------------- MAIN ROUTE ---------------- #

@app.route('/analyze', methods=['POST'])
def analyze():

    data = request.json

    text = data.get("text", "")
    category = data.get("category", "english")
    mode = data.get("mode", "practice")

    if not text.strip():
        return jsonify({
            "overall_score": 0,
            "suggestions": ["Empty response."]
        })

    if mode == "practice":
        result = analyze_english(text)

    elif mode == "interview":
        if category == "hr":
            result = analyze_hr(text)
        else:
            result = analyze_english(text)

    else:
        result = {
            "overall_score": 0,
            "suggestions": ["Invalid mode."]
        }

    return jsonify(result)


if __name__ == "__main__":
    app.run()