# scraper.py
from google_play_scraper import reviews_all
import pandas as pd
from tqdm import tqdm
import json

BANK_APPS = {
    "CBE": "com.combanketh.mobilebanking",
    "BOA": "com.boa.boaMobileBanking",
    "Dashen": "com.dashen.dashensuperapp"
}

def scrape_reviews():
    all_reviews = []
    
    for bank_name, app_id in BANK_APPS.items():
        print(f"Scraping {bank_name} reviews...")
        reviews = reviews_all(
            app_id,
            sleep_milliseconds=1000,  # Avoid rate limiting
            lang='en',
            country='et',
            sort=1  # Sort by newest
        )
        
        for review in tqdm(reviews):
            all_reviews.append({
                "bank": bank_name,
                "review": review.get("content", ""),
                "rating": review.get("score", 0),
                "date": review.get("at", "").strftime("%Y-%m-%d") if review.get("at") else "",
                "source": "Google Play"
            })
            
    return pd.DataFrame(all_reviews)

def save_data(df):
    df.to_csv("data/raw/reviews_raw.csv", index=False)
    print(f"Saved {len(df)} reviews to data/raw/reviews_raw.csv")

if __name__ == "__main__":
    reviews_df = scrape_reviews()
    save_data(reviews_df)