# scripts/sentiment_analysis.py
import pandas as pd
import numpy as np
from transformers import pipeline
from tqdm import tqdm
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Create output directory
os.makedirs("data/analyzed", exist_ok=True)

# Initialize sentiment analyzer with updated parameters
sentiment_analyzer = pipeline(
    "sentiment-analysis",
    model="distilbert-base-uncased-finetuned-sst-2-english",
    top_k=2,  # Get both positive and negative scores
    truncation=True,
    device=-1  # Use CPU for stability
)

def classify_sentiment(scores):
    """Classify sentiment with dynamic threshold"""
    pos_score = next((s['score'] for s in scores if s['label'] == 'POSITIVE'), 0)
    neg_score = next((s['score'] for s in scores if s['label'] == 'NEGATIVE'), 0)
    
    # Dynamic neutral threshold
    if abs(pos_score - neg_score) < 0.25:
        return "neutral", max(pos_score, neg_score)
    elif pos_score > neg_score:
        return "positive", pos_score
    else:
        return "negative", neg_score

def analyze_sentiment(df, batch_size=8):
    """Process sentiment with robust error handling"""
    # Ensure all reviews are strings
    df['clean_review'] = df['clean_review'].astype(str)
    
    sentiments = []
    scores = []
    errors = 0
    
    # Process individual reviews with progress tracking
    for i, review in tqdm(enumerate(df['clean_review']), total=len(df)):
        try:
            if len(review.strip()) < 3:  # Skip empty reviews
                sentiments.append("neutral")
                scores.append(0.5)
                continue
                
            result = sentiment_analyzer(review)
            sentiment, score = classify_sentiment(result[0])
            sentiments.append(sentiment)
            scores.append(score)
        except Exception as e:
            errors += 1
            sentiments.append("neutral")
            scores.append(0.5)
            if errors < 10:  # Log first few errors
                logging.warning(f"Error processing review {i}: {str(e)[:100]}...")
    
    df['sentiment'] = sentiments
    df['sentiment_score'] = scores
    logging.info(f"Completed with {errors} errors out of {len(df)} reviews")
    return df

if __name__ == "__main__":
    # Load cleaned data
    df = pd.read_csv("data/processed/reviews_clean.csv")
    print(f"Loaded {len(df)} reviews for sentiment analysis")
    
    # Analyze sentiment
    analyzed_df = analyze_sentiment(df)
    
    # Save results
    output_path = "data/analyzed/reviews_with_sentiment.csv"
    analyzed_df.to_csv(output_path, index=False)
    print(f"✅ Saved sentiment analysis to {output_path}")
    
    # Print summary
    print("\nSentiment Distribution:")
    print(analyzed_df['sentiment'].value_counts())
    
    print("\nBank-wise Sentiment Counts:")
    bank_sentiment = analyzed_df.groupby(['bank', 'sentiment']).size().unstack()
    print(bank_sentiment)
    
    # Calculate percentages
    print("\nBank-wise Sentiment Percentages:")
    bank_percent = bank_sentiment.div(bank_sentiment.sum(axis=1), axis=0) * 100
    print(bank_percent.round(1))