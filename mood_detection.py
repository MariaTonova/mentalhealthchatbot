from textblob import TextBlob

def get_mood(text):
    analysis = TextBlob(text)
    polarity = analysis.sentiment.polarity
    if polarity < -0.3:
        return "sad"
    elif polarity < 0.3:
        return "neutral"
    else:
        return "happy"
