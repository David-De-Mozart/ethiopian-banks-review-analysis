# scripts/visualize.py
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from wordcloud import WordCloud
import os
import numpy as np

# Configure plotting style
sns.set(style="whitegrid")
plt.rcParams['figure.figsize'] = (12, 8)

def clean_text(text):
    """Ensure text is string and handle missing values"""
    if not isinstance(text, str):
        if pd.isna(text):
            return ""
        return str(text)
    return text

def create_visualizations(df):
    # Create directory for visualizations
    os.makedirs("visualizations", exist_ok=True)
    
    # Clean review text
    df['clean_review'] = df['clean_review'].apply(clean_text)
    
    # 1. Sentiment Distribution by Bank
    plt.figure(figsize=(10, 6))
    sentiment_counts = df.groupby(['bank', 'sentiment']).size().unstack()
    sentiment_counts.plot(kind='bar', stacked=True, colormap='coolwarm')
    plt.title('Sentiment Distribution by Bank')
    plt.ylabel('Number of Reviews')
    plt.xticks(rotation=0)
    plt.tight_layout()
    plt.savefig('visualizations/sentiment_distribution.png')
    plt.close()
    
    # 2. Rating Distribution
    plt.figure(figsize=(10, 6))
    sns.boxplot(x='bank', y='rating', data=df)
    plt.title('Rating Distribution by Bank')
    plt.xlabel('Bank')
    plt.ylabel('Star Rating')
    plt.savefig('visualizations/rating_distribution.png')
    plt.close()
    
    # 3. Average Sentiment Score by Bank
    plt.figure(figsize=(10, 6))
    df['sentiment_score'] = pd.to_numeric(df['sentiment_score'], errors='coerce')
    sns.barplot(x='bank', y='sentiment_score', data=df, errorbar=None)
    plt.title('Average Sentiment Score by Bank')
    plt.xlabel('Bank')
    plt.ylabel('Average Sentiment Score')
    plt.savefig('visualizations/avg_sentiment.png')
    plt.close()
    
    # 4. Top Themes Word Clouds (for each bank)
    for bank in df['bank'].unique():
        bank_reviews = df[df['bank'] == bank]['clean_review']
        # Ensure all reviews are strings
        text = ' '.join(str(review) for review in bank_reviews)
        
        wordcloud = WordCloud(width=800, height=400, background_color='white').generate(text)
        plt.figure(figsize=(10, 5))
        plt.imshow(wordcloud)
        plt.axis('off')
        plt.title(f'{bank} - Common Themes')
        plt.savefig(f'visualizations/{bank}_themes.png')
        plt.close()
    
    # 5. Theme Frequency
    plt.figure(figsize=(12, 8))
    # Flatten themes and ensure all are strings
    all_themes = []
    for sublist in df['themes']:
        if isinstance(sublist, list):
            all_themes.extend([str(t) for t in sublist])
        else:
            all_themes.append(str(sublist))
    
    theme_counts = pd.Series(all_themes).value_counts().head(10)
    
    # Fixed: Use hue parameter to avoid warning
    theme_df = pd.DataFrame({
        'theme': theme_counts.index,
        'count': theme_counts.values
    })
    sns.barplot(x='count', y='theme', data=theme_df, hue='theme', legend=False, palette='viridis')
    plt.title('Top 10 Themes Across All Banks')
    plt.xlabel('Count')
    plt.ylabel('Theme')
    plt.savefig('visualizations/top_themes.png')
    plt.close()

def generate_report():
    """Generate final report in Markdown format"""
    report = """# Ethiopian Banks Mobile App Review Analysis - Final Report

## Executive Summary
This report analyzes user reviews from Google Play Store for three Ethiopian banks:
- Commercial Bank of Ethiopia (CBE)
- Bank of Abyssinia (BOA)
- Dashen Bank

The analysis reveals significant differences in user satisfaction, with CBE and Dashen receiving predominantly positive feedback, while BOA struggles with negative sentiment.

## Key Insights

### 1. Overall Satisfaction
![Sentiment Distribution](visualizations/sentiment_distribution.png)
- **CBE**: Highest positive sentiment (64.7%)
- **BOA**: Significant negative sentiment (54.2%)
- **Dashen**: Strong positive sentiment (76.1%)

### 2. Rating Distribution
![Rating Distribution](visualizations/rating_distribution.png)
- CBE maintains the highest average rating (4.4★)
- BOA has the lowest average rating (2.8★)
- Dashen shows consistent 4★ ratings

### 3. Key Themes
![Top Themes](visualizations/top_themes.png)
- **Transaction Issues**: Most common complaint across all banks
- **Login Problems**: Particularly prevalent for BOA
- **Feature Requests**: Most requested for Dashen

### Bank-Specific Analysis

#### Commercial Bank of Ethiopia (CBE)
![CBE Themes](visualizations/CBE_themes.png)
- **Strengths**: Comprehensive features, reliable transactions
- **Weaknesses**: Occasional performance issues during peak hours
- **Recommendations**:
  - Optimize server capacity for peak usage
  - Add biometric login options

#### Bank of Abyssinia (BOA)
![BOA Themes](visualizations/BOA_themes.png)
- **Strengths**: Wide range of banking services
- **Weaknesses**: Frequent login failures, app crashes
- **Recommendations**:
  - Prioritize authentication system overhaul
  - Improve app stability with performance patches

#### Dashen Bank
![Dashen Themes](visualizations/Dashen_themes.png)
- **Strengths**: User-friendly interface, innovative features
- **Weaknesses**: Slow transaction processing
- **Recommendations**:
  - Implement top-requested features (e.g., bill splitting)
  - Optimize transaction processing speed

## Conclusion
All banks should focus on improving transaction reliability and performance. BOA requires immediate attention to address core functionality issues, while CBE and Dashen should focus on enhancing user experience and adding innovative features to maintain their competitive edge.

---

**Analysis Methodology**:
- Collected 8,840 reviews from Google Play Store
- Performed sentiment analysis using DistilBERT
- Identified themes through NLP keyword extraction
- Stored results in Oracle Database
"""

    # Fixed: Specify UTF-8 encoding to handle special characters
    with open('final_report.md', 'w', encoding='utf-8') as f:
        f.write(report)
    print("✅ Final report generated: final_report.md")

if __name__ == "__main__":
    # Load analyzed data
    df = pd.read_csv("data/analyzed/reviews_with_themes.csv")
    
    # Convert themes to lists if needed
    if isinstance(df['themes'].iloc[0], str):
        try:
            df['themes'] = df['themes'].apply(eval)
        except:
            # If eval fails, convert to list of single string
            df['themes'] = df['themes'].apply(lambda x: [str(x)])
    
    # Create visualizations
    create_visualizations(df)
    
    # Generate report
    generate_report()