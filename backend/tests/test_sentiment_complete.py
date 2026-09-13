# test_sentiment_complete.py
import asyncio
from backend.app.sentiment import (
    DataIngestionPipeline,
    TextPreprocessor,
    SentimentClassifier,
    SentimentAggregator
)

async def test_complete():
    print("🧠 Testing Complete Sentiment Ecosystem...")
    
    # 1. Test Data Ingestion
    print("\n📥 Testing Data Ingestion...")
    pipeline = DataIngestionPipeline()
    sources = pipeline.get_all_sources()
    print(f"   Sources: {sources}")
    
    # 2. Test Preprocessing
    print("\n🔧 Testing Preprocessing...")
    preprocessor = TextPreprocessor()
    
    test_text = "This is a great day for the economy! #goodnews @finance"
    result = preprocessor.preprocess_text(test_text)
    print(f"   Original: {test_text}")
    print(f"   Clean: {result['clean']}")
    print(f"   Tokens: {result['tokens'][:10]}")
    
    # 3. Test Classifier
    print("\n🧠 Testing Classifier...")
    classifier = SentimentClassifier()
    
    # Load models
    classifier.load_pretrained('finbert')
    classifier.load_pretrained('distilbert')
    
    print(f"   Models loaded: {classifier.get_available_models()}")
    
    # Predict
    texts = [
        "The economy is showing strong growth",
        "Trade tensions are escalating",
        "AI technology is advancing rapidly"
    ]
    
    results = classifier.predict(texts, 'ensemble')
    
    for i, result in enumerate(results):
        print(f"   {i+1}. {result.sentiment.value} (conf: {result.confidence:.2f})")
    
    # 4. Test Aggregator
    print("\n📊 Testing Aggregator...")
    aggregator = SentimentAggregator()
    
    # Convert results to dict format
    sentiment_dict = {
        'global': {
            'score': 0.15,
            'confidence': 0.75,
            'sentiment': 'positive',
            'regions': []
        }
    }
    
    current_state = {'economic_stability': 70, 'trade_stability': 65}
    updates = aggregator.update_environment(sentiment_dict, current_state)
    print(f"   State updates: {updates}")
    
    print("\n✅ Complete Sentiment Ecosystem tested!")

if __name__ == "__main__":
    asyncio.run(test_complete())