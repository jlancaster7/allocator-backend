"""Mock data generator utilities"""

import random
import string
from datetime import datetime, timedelta
from typing import Optional
from app.core.config import settings

# Set random seed for reproducibility
random.seed(settings.MOCK_DATA_SEED)


class MockDataGenerator:
    """Utilities for generating realistic mock data"""
    
    @staticmethod
    def generate_cusip() -> str:
        """Generate a realistic CUSIP identifier"""
        # CUSIP format: 6 alphanumeric + 2 numeric + 1 check digit
        issuer = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        issue = ''.join(random.choices(string.digits, k=2))
        check = random.choice(string.digits)
        return f"{issuer}{issue}{check}"
    
    @staticmethod
    def generate_ticker(issuer: str, coupon: float, maturity: str) -> str:
        """Generate a ticker symbol from bond details"""
        maturity_date = datetime.strptime(maturity, "%Y-%m-%d")
        return f"{issuer} {coupon:.2f} {maturity_date.strftime('%m/%d/%y')}"
    
    @staticmethod
    def generate_price(min_price: float = 90.0, max_price: float = 110.0) -> float:
        """Generate a realistic bond price"""
        return round(random.uniform(min_price, max_price), 3)
    
    @staticmethod
    def generate_duration(min_dur: float = 1.0, max_dur: float = 10.0) -> float:
        """Generate a realistic duration"""
        return round(random.uniform(min_dur, max_dur), 2)
    
    @staticmethod
    def generate_spread_duration(duration: float, correlation: float = 0.95) -> float:
        """Generate spread duration correlated with duration"""
        # Spread duration is typically slightly less than duration
        spread_factor = random.uniform(correlation - 0.05, correlation + 0.02)
        return round(duration * spread_factor, 2)
    
    @staticmethod
    def generate_convexity(duration: float) -> float:
        """Generate convexity based on duration"""
        # Convexity is roughly proportional to duration squared
        base_convexity = duration * duration * 0.1
        variation = random.uniform(0.8, 1.2)
        return round(base_convexity * variation, 2)
    
    @staticmethod
    def generate_oas(rating: str = "A") -> float:
        """Generate OAS based on credit rating"""
        oas_ranges = {
            "AAA": (5, 25),
            "AA": (15, 40),
            "A": (30, 80),
            "BBB": (70, 150),
            "BB": (200, 400),
            "B": (400, 700)
        }
        min_oas, max_oas = oas_ranges.get(rating, (50, 100))
        return round(random.uniform(min_oas, max_oas), 0)
    
    @staticmethod
    def generate_maturity_date(min_years: int = 1, max_years: int = 30) -> str:
        """Generate a maturity date"""
        days_ahead = random.randint(min_years * 365, max_years * 365)
        maturity = datetime.now() + timedelta(days=days_ahead)
        return maturity.strftime("%Y-%m-%d")
    
    @staticmethod
    def generate_coupon(min_coupon: float = 1.0, max_coupon: float = 6.0) -> float:
        """Generate a coupon rate"""
        return round(random.uniform(min_coupon, max_coupon) * 2) / 2  # Round to nearest 0.5
    
    @staticmethod
    def generate_account_id(prefix: str = "ACC") -> str:
        """Generate an account ID"""
        return f"{prefix}{random.randint(100000, 999999)}"
    
    @staticmethod
    def generate_nav(min_nav: float = 10_000_000, max_nav: float = 500_000_000) -> float:
        """Generate account NAV"""
        # Use log-normal distribution for more realistic NAV distribution
        log_min = float(f"{min_nav:.0e}".split('e')[1])
        log_max = float(f"{max_nav:.0e}".split('e')[1])
        log_nav = random.uniform(log_min, log_max)
        return round(10 ** log_nav, -6)  # Round to nearest million
    
    @staticmethod
    def generate_cash_percentage(conservative: bool = False) -> float:
        """Generate cash as percentage of NAV"""
        if conservative:
            return random.uniform(0.15, 0.25)  # 15-25% for conservative
        return random.uniform(0.10, 0.20)  # 10-20% normally - increased to allow proper allocation demos