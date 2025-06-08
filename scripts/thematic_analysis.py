# scripts/thematic_analysis.py
import pandas as pd
import spacy
import os
import re
from pathlib import Path
import logging
from wordcloud import WordCloud
import matplotlib.pyplot as plt
import numpy as np

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load spaCy model
nlp = spacy.load("en_core_web_sm")

# Theme mapping configuration
THEME_MAP = {
    'transaction_issues': [
        'transfer', 'transaction', 'payment', 'send', 'receive', 'fail', 
        'stuck', 'pending', 'delay', 'timeout', 'amount', 'money', 'fund',
        'disappear', 'deduct', 'balance', 'reversal', 'bill', 'utility',
        'failed transaction', 'money not sent', 'payment pending'
    ],
    'login_authentication': [
        'login', 'password', 'authenticate', 'signin', 'biometric', 
        'fingerprint', 'face', 'id', 'verify', 'otp', 'sms', 'code',
        'block', 'lock', 'access', 'unauthorized', 'security', 'forgot password',
        'cant login', 'login problem'
    ],
    'app_performance': [
        'slow', 'crash', 'lag', 'freeze', 'load', 'speed', 'hang',
        'responsive', 'close', 'exit', 'bug', 'error', 'problem',
        'update', 'version', 'install', 'compatible', 'device', 'app crash',
        'too slow', 'loading time'
    ],
    'account_management': [
        'account', 'balance', 'statement', 'detail', 'information',
        'history', 'activity', 'check', 'view', 'update', 'change',
        'personal', 'data', 'profile', 'security', 'privacy', 'account balance',
        'transaction history'
    ],
    'customer_support': [
        'support', 'help', 'response', 'service', 'assistance',
        'contact', 'call', 'email', 'team', 'resolve', 'complaint',
        'agent', 'representative', 'wait', 'time', 'hour', 'day', 'poor support',
        'no response'
    ],
    'ui_ux_design': [
        'interface', 'design', 'navigate', 'layout', 'user', 'experience',
        'easy', 'simple', 'improve', 'look', 'feel', 'intuitive', 'button',
        'menu', 'option', 'feature', 'function', 'tool', 'section', 'tab',
        'user interface', 'easy to use'
    ],
    'service_features': [
        'feature', 'request', 'add', 'should', 'could', 'would',
        'want', 'need', 'missing', 'suggest', 'include', 'wish',
        'allow', 'option', 'function', 'mobile banking', 'app',
        'digital', 'online', 'service', 'notification', 'alert',
        'new feature', 'add feature'
    ]
}

def clean_text(text):
    """Ensure text is clean and string type"""
    if not isinstance(text, str):
        return ""
    # Remove special characters
    text = re.sub(r'[^\w\s.,!?;:]', '', text)
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text.lower()

def extract_keywords(text):
    """keyword extraction with banking context"""
    text = clean_text(text)
    if len(text) < 3:
        return []
    
    doc = nlp(text)
    
    # Focus on meaningful banking terms
    keywords = []
    for token in doc:
        # Include relevant nouns, verbs, and adjectives
        if token.pos_ in ['NOUN', 'VERB', 'ADJ'] and not token.is_stop:
            # Handle compound nouns (e.g., "mobile banking")
            if token.dep_ == 'compound' and token.head.pos_ == 'NOUN':
                keyword = f"{token.lemma_}_{token.head.lemma_}"
                keywords.append(keyword)
            elif len(token.lemma_) > 2:
                keywords.append(token.lemma_.lower())
    
    return keywords

def assign_themes(keywords):
    """Assign themes based on keyword matching"""
    themes = []
    for theme, terms in THEME_MAP.items():
        if any(term in keywords for term in terms):
            themes.append(theme)
    return themes if themes else ['other']

def generate_wordcloud(df, bank_name):
    """Generate word cloud for a specific bank"""
    try:
        # Combine all keywords for the bank
        all_keywords = [kw for sublist in df[df['bank'] == bank_name]['keywords'] for kw in sublist]
        if not all_keywords:
            logging.warning(f"No keywords found for {bank_name}")
            return
            
        text = ' '.join(all_keywords)
        wordcloud = WordCloud(width=800, height=400, background_color='white').generate(text)
        plt.figure(figsize=(10, 5))
        plt.imshow(wordcloud)
        plt.axis('off')
        plt.title(f'{bank_name} Common Themes')
        
        # Save visualization
        vis_dir = Path("visualizations")
        vis_dir.mkdir(exist_ok=True)
        plt.savefig(vis_dir / f'{bank_name}_wordcloud.png')
        plt.close()
        logging.info(f"Generated word cloud for {bank_name}")
    except Exception as e:
        logging.error(f"Error generating word cloud for {bank_name}: {str(e)}")

def main():
    # Create directories
    Path("data/analyzed").mkdir(parents=True, exist_ok=True)
    
    try:
        # Load sentiment data
        input_path = "data/analyzed/reviews_with_sentiment.csv"
        df = pd.read_csv(input_path)
        logging.info(f"Loaded {len(df)} reviews for thematic analysis")
        
        # Clean and prepare text
        df['clean_review'] = df['clean_review'].fillna('').astype(str)
        
        # Extract keywords
        logging.info("Extracting keywords...")
        df['keywords'] = df['clean_review'].apply(extract_keywords)
        
        # Assign themes
        logging.info("Assigning themes...")
        df['themes'] = df['keywords'].apply(assign_themes)
        
        # Save results
        output_path = "data/analyzed/reviews_with_themes.csv"
        df.to_csv(output_path, index=False)
        logging.info(f"✅ Saved thematic analysis to {output_path}")
        
        # Generate visualizations
        for bank in df['bank'].unique():
            generate_wordcloud(df, bank)
        
        # Print theme distribution
        logging.info("\nTheme Distribution:")
        all_themes = [theme for sublist in df['themes'] for theme in sublist]
        theme_counts = pd.Series(all_themes).value_counts()
        print(theme_counts.head(10))
        
        # Print bank-specific insights
        logging.info("\nBank-specific Themes:")
        for bank in df['bank'].unique():
            bank_df = df[df['bank'] == bank]
            bank_themes = [theme for sublist in bank_df['themes'] for theme in sublist]
            print(f"\n{bank} Top Themes:")
            print(pd.Series(bank_themes).value_counts().head(5))
            
        return True
    except Exception as e:
        logging.error(f"Thematic analysis failed: {str(e)}")
        return False

if __name__ == "__main__":
    main()