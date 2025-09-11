"""
Test script for MyPage API endpoints
Run this script to test the MyPage functionality

Usage:
    python test_mypage_api.py
"""
import requests
import json
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:8000/api"
TEST_USERNAME = "testuser"
TEST_PASSWORD = "testpass123"

# Colors for terminal output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'


def print_test_header(test_name):
    """Print test header"""
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}Testing: {test_name}{RESET}")
    print(f"{BLUE}{'='*60}{RESET}")


def print_success(message):
    """Print success message"""
    print(f"{GREEN}✓ {message}{RESET}")


def print_error(message):
    """Print error message"""
    print(f"{RED}✗ {message}{RESET}")


def print_info(message):
    """Print info message"""
    print(f"{YELLOW}ℹ {message}{RESET}")


def get_auth_token():
    """Get authentication token"""
    print_test_header("Authentication")
    
    # Try to login
    response = requests.post(
        f"{BASE_URL}/auth/login/",
        json={
            "username": TEST_USERNAME,
            "password": TEST_PASSWORD
        }
    )
    
    if response.status_code == 200:
        token = response.json().get('access')
        print_success(f"Successfully authenticated as {TEST_USERNAME}")
        return token
    else:
        print_error(f"Authentication failed: {response.status_code}")
        print_info("Please ensure test user exists or create one first")
        return None


def test_mypage_profile(token):
    """Test profile endpoint"""
    print_test_header("MyPage Profile")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Get profile
    response = requests.get(f"{BASE_URL}/mypage/profile/", headers=headers)
    
    if response.status_code == 200:
        profile = response.json()
        print_success("Profile fetched successfully")
        print(f"  - Username: {profile.get('username')}")
        print(f"  - Nickname: {profile.get('nickname')}")
        print(f"  - Email: {profile.get('email')}")
        print(f"  - Role: {profile.get('role')}")
        return True
    else:
        print_error(f"Failed to fetch profile: {response.status_code}")
        return False


def test_mypage_stats(token):
    """Test statistics endpoint"""
    print_test_header("MyPage Statistics")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Get stats
    response = requests.get(f"{BASE_URL}/mypage/stats/", headers=headers)
    
    if response.status_code == 200:
        stats = response.json()
        print_success("Statistics fetched successfully")
        
        # Print sales stats
        sales = stats.get('sales', {})
        print(f"\n  Sales Statistics:")
        print(f"    - Active listings: {sales.get('active', 0)}")
        print(f"    - Reserved: {sales.get('reserved', 0)}")
        print(f"    - Completed: {sales.get('completed', 0)}")
        print(f"    - Received offers: {sales.get('received_offers', 0)}")
        
        # Print purchase stats
        purchases = stats.get('purchases', {})
        print(f"\n  Purchase Statistics:")
        print(f"    - Sent offers: {purchases.get('sent_offers', 0)}")
        print(f"    - Accepted offers: {purchases.get('accepted_offers', 0)}")
        print(f"    - Favorites: {purchases.get('favorites', 0)}")
        
        return True
    else:
        print_error(f"Failed to fetch statistics: {response.status_code}")
        return False


def test_my_listings(token):
    """Test my listings endpoint"""
    print_test_header("My Listings (Sales)")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Get my listings
    response = requests.get(f"{BASE_URL}/used/phones/my-listings/", headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        listings = data if isinstance(data, list) else data.get('results', [])
        print_success(f"Found {len(listings)} listings")
        
        for idx, listing in enumerate(listings[:3], 1):  # Show first 3
            print(f"\n  Listing {idx}:")
            print(f"    - Model: {listing.get('brand')} {listing.get('model')}")
            print(f"    - Price: {listing.get('price'):,}원")
            print(f"    - Status: {listing.get('status')}")
            print(f"    - Offers: {listing.get('offer_count', 0)}")
        
        if len(listings) > 3:
            print(f"\n  ... and {len(listings) - 3} more listings")
        
        return True
    else:
        print_error(f"Failed to fetch listings: {response.status_code}")
        return False


def test_sent_offers(token):
    """Test sent offers endpoint"""
    print_test_header("Sent Offers (Purchases)")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Get sent offers
    response = requests.get(f"{BASE_URL}/used/offers/sent/", headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        offers = data.get('results', [])
        print_success(f"Found {len(offers)} sent offers")
        
        for idx, offer in enumerate(offers[:3], 1):  # Show first 3
            phone = offer.get('phone', {})
            print(f"\n  Offer {idx}:")
            print(f"    - Phone: {phone.get('title')}")
            print(f"    - Original price: {phone.get('price', 0):,}원")
            print(f"    - Offered price: {offer.get('offered_price', 0):,}원")
            print(f"    - Status: {offer.get('status')}")
        
        if len(offers) > 3:
            print(f"\n  ... and {len(offers) - 3} more offers")
        
        return True
    else:
        print_error(f"Failed to fetch sent offers: {response.status_code}")
        return False


def test_favorites(token):
    """Test favorites endpoint"""
    print_test_header("Favorites")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Get favorites
    response = requests.get(f"{BASE_URL}/used/favorites/", headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        favorites = data.get('results', [])
        print_success(f"Found {len(favorites)} favorites")
        
        for idx, favorite in enumerate(favorites[:3], 1):  # Show first 3
            phone = favorite.get('phone', {})
            print(f"\n  Favorite {idx}:")
            print(f"    - Phone: {phone.get('title')}")
            print(f"    - Price: {phone.get('price', 0):,}원")
            print(f"    - Seller: {phone.get('seller', {}).get('nickname')}")
        
        if len(favorites) > 3:
            print(f"\n  ... and {len(favorites) - 3} more favorites")
        
        return True
    else:
        print_error(f"Failed to fetch favorites: {response.status_code}")
        return False


def test_received_offers(token):
    """Test received offers endpoint"""
    print_test_header("Received Offers (For Sellers)")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Get received offers
    response = requests.get(f"{BASE_URL}/used/offers/received/", headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        offers = data.get('results', [])
        print_success(f"Found {len(offers)} received offers")
        
        for idx, offer in enumerate(offers[:3], 1):  # Show first 3
            buyer = offer.get('buyer', {})
            print(f"\n  Offer {idx}:")
            print(f"    - Buyer: {buyer.get('nickname')}")
            print(f"    - Offered price: {offer.get('offered_price', 0):,}원")
            print(f"    - Status: {offer.get('status')}")
            print(f"    - Message: {offer.get('message', 'No message')[:50]}...")
        
        if len(offers) > 3:
            print(f"\n  ... and {len(offers) - 3} more offers")
        
        return True
    else:
        print_error(f"Failed to fetch received offers: {response.status_code}")
        return False


def main():
    """Main test function"""
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}MyPage API Test Suite{RESET}")
    print(f"{BLUE}{'='*60}{RESET}")
    print(f"\nBase URL: {BASE_URL}")
    print(f"Test User: {TEST_USERNAME}")
    
    # Get authentication token
    token = get_auth_token()
    if not token:
        print_error("\nFailed to authenticate. Exiting tests.")
        return
    
    # Run tests
    test_results = []
    
    # Test MyPage endpoints
    test_results.append(("Profile", test_mypage_profile(token)))
    test_results.append(("Statistics", test_mypage_stats(token)))
    
    # Test Used Phone endpoints for MyPage
    test_results.append(("My Listings", test_my_listings(token)))
    test_results.append(("Sent Offers", test_sent_offers(token)))
    test_results.append(("Favorites", test_favorites(token)))
    test_results.append(("Received Offers", test_received_offers(token)))
    
    # Print summary
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}Test Summary{RESET}")
    print(f"{BLUE}{'='*60}{RESET}")
    
    passed = sum(1 for _, result in test_results if result)
    total = len(test_results)
    
    for test_name, result in test_results:
        status = f"{GREEN}PASSED{RESET}" if result else f"{RED}FAILED{RESET}"
        print(f"  {test_name}: {status}")
    
    print(f"\n{BLUE}Results: {passed}/{total} tests passed{RESET}")
    
    if passed == total:
        print_success("\n✅ All tests passed!")
    else:
        print_error(f"\n⚠️ {total - passed} test(s) failed")


if __name__ == "__main__":
    main()