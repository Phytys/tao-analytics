import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import CoinGeckoPrice
from config import DB_URL, COINGECKO_API_KEY
from services.cache import clear_all_caches
import coingecko

COIN_ID = 'bittensor'
VS_CURRENCY = 'usd'

if not COINGECKO_API_KEY:
    raise RuntimeError("COINGECKO_API_KEY is not set in your environment or config.py")

def fetch_tao_data():
    client = coingecko.CoinGeckoDemoClient(api_key=COINGECKO_API_KEY)
    
    # Get price and market cap data
    response = client.simple.get_price(
        ids=COIN_ID, 
        vs_currencies=VS_CURRENCY,
        include_market_cap=True
    )
    
    coin_data = response.get(COIN_ID, {})
    price_usd = coin_data.get(VS_CURRENCY)
    market_cap_usd = coin_data.get(f'{VS_CURRENCY}_market_cap')
    
    if price_usd is None:
        raise ValueError("TAO price not found in CoinGecko response")
    if market_cap_usd is None:
        raise ValueError("TAO market cap not found in CoinGecko response")
    
    return float(price_usd), float(market_cap_usd)

def save_data_to_db(price_usd, market_cap_usd):
    engine = create_engine(DB_URL)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        price_entry = CoinGeckoPrice(
            price_usd=price_usd, 
            market_cap_usd=market_cap_usd,
            fetched_at=datetime.utcnow()
        )
        session.add(price_entry)
        session.commit()
        print(f"Saved TAO data: ${price_usd:.4f} price, ${market_cap_usd:,.0f} market cap at {price_entry.fetched_at}")
    finally:
        session.close()

def main():
    price_usd, market_cap_usd = fetch_tao_data()
    save_data_to_db(price_usd, market_cap_usd)
    
    # Clear cache to ensure new data is immediately visible
    clear_all_caches()
    print("✅ Cache cleared - new TAO price/market cap is now visible in the app!")

if __name__ == "__main__":
    main() 