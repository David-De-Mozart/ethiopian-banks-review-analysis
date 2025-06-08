# scripts/preprocess.py
import pandas as pd
import numpy as np
import re
import os
from pathlib import Path

def clean_text(text):
    if not isinstance(text, str):
        return ""
    # Remove emojis and special characters
    text = re.sub(r'[^\w\s.,!?;:]', '', text)
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def preprocess_reviews(df):
    # Handle missing data
    print(f"Initial reviews: {len(df)}")
    df = df.dropna(subset=["review"])
    df = df[df["review"] != ""]
    print(f"After removing empty reviews: {len(df)}")
    
    # Remove duplicates
    df = df.drop_duplicates(subset=["review", "bank", "date"])
    print(f"After removing duplicates: {len(df)}")
    
    # Clean text
    df["clean_review"] = df["review"].apply(clean_text)
    
    # Convert date format
    df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.strftime("%Y-%m-%d")
    
    # Filter valid ratings (1-5)
    df = df[df["rating"].between(1, 5)]
    print(f"After rating filter: {len(df)}")
    
    # Select final columns
    return df[["bank", "review", "clean_review", "rating", "date", "source"]]

if __name__ == "__main__":
    # Ensure directories exist
    Path("data/processed").mkdir(parents=True, exist_ok=True)
    
    try:
        raw_df = pd.read_csv("data/raw/reviews_raw.csv")
        cleaned_df = preprocess_reviews(raw_df)
        
        # Save cleaned data
        cleaned_df.to_csv("data/processed/reviews_clean.csv", index=False)
        print(f"\n✅ Processed {len(cleaned_df)} reviews")
        print(f"Bank distribution:\n{cleaned_df['bank'].value_counts()}")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("Ensure you've run scraper.py first")