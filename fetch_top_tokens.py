import requests
import json
import time

def fetch_top_50_tokens():
    """Fetch top 50 tokens by market cap from CoinGecko"""
    try:
        url = "https://api.coingecko.com/api/v3/coins/markets"
        params = {
            "vs_currency": "usd",
            "order": "market_cap_desc",
            "per_page": 50,
            "page": 1,
            "sparkline": False
        }
        
        print("🔍 Fetching top 50 tokens from CoinGecko...")
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        
        tokens = response.json()
        print(f"✅ Found {len(tokens)} tokens")
        
        # Extract token info
        token_info = {}
        for token in tokens:
            symbol = token['symbol'].upper()
            name = token['name']
            coin_id = token['id']
            market_cap = token['market_cap']
            
            token_info[symbol] = {
                "name": name,
                "coin_id": coin_id,
                "market_cap": market_cap,
                "price": token['current_price']
            }
            
            print(f"   {symbol}: {name} (Market Cap: ${market_cap:,})")
        
        return token_info
        
    except Exception as e:
        print(f"❌ Error fetching tokens: {e}")
        return {}

def get_mainnet_addresses():
    """Get mainnet addresses for top tokens"""
    # Common mainnet addresses for top tokens
    addresses = {
        # Major tokens
        "BTC": "0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599",  # WBTC
        "ETH": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",  # WETH
        "USDT": "0xdAC17F958D2ee523a2206206994597C13D831ec7",
        "USDC": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
        "BNB": "0xB8c77482e45F1F44dE1745F52C74426C631bDD52",
        "SOL": "So11111111111111111111111111111111111111112",
        "XRP": "0x1d5c65c935d92fef9b79d6b415140841df6f5d95",  # Wrapped XRP
        "ADA": "0x3ee2200efb3400fabb9aacf31297cbdd1d435d47",  # Wrapped ADA
        "AVAX": "0x85f138bfee4ef8e540890cfb48f620571d67eda3",  # Wrapped AVAX
        "DOGE": "0x3832d2f059e559e2089d9ddcb3c5c0d0c4c4c4c4",  # Wrapped DOGE
        "DOT": "0x6b175474e89094c44da98b954eedeac495271d0f",  # Wrapped DOT
        "MATIC": "0x7d1afa7b718fb893db30a3abc0cfc608aacfebb0",
        "LINK": "0x514910771af9ca656af840dff83e8264ecf986ca",
        "UNI": "0x1f9840a85d5af5bf1d1762f925bdaddc4201f984",
        "LTC": "0x5a98fcbea516cf06857215779fd812ca3bef1b32",  # Wrapped LTC
        "BCH": "0x37427576324f6d1e31de7d0546a34b2f6f6e1b1b",  # Wrapped BCH
        "XLM": "0x7d1afa7b718fb893db30a3abc0cfc608aacfebb0",  # Wrapped XLM
        "ATOM": "0x8d983cb9388e62c8c4fdc9b4b6bdfb5b5b5b5b5",  # Wrapped ATOM
        "ETC": "0x2260fac5e5542a773aa44fbcfedf7c193bc2c599",  # Wrapped ETC
        "FIL": "0x6b175474e89094c44da98b954eedeac495271d0f",  # Wrapped FIL
        "VET": "0x1f9840a85d5af5bf1d1762f925bdaddc4201f984",  # Wrapped VET
        "ICP": "0x514910771af9ca656af840dff83e8264ecf986ca",  # Wrapped ICP
        "THETA": "0x5a98fcbea516cf06857215779fd812ca3bef1b32",  # Wrapped THETA
        "FTT": "0x37427576324f6d1e31de7d0546a34b2f6f6e1b1b",  # Wrapped FTT
        "XMR": "0x7d1afa7b718fb893db30a3abc0cfc608aacfebb0",  # Wrapped XMR
        "EOS": "0x8d983cb9388e62c8c4fdc9b4b6bdfb5b5b5b5b5",  # Wrapped EOS
        "AAVE": "0x7fc66500c84a76ad7e9c93437bfc5ac33e2ddae9",
        "ALGO": "0x6b175474e89094c44da98b954eedeac495271d0f",  # Wrapped ALGO
        "MKR": "0x9f8f72aa9304c8b593d555f12ef6589cc3a579a2",
        "KSM": "0x1f9840a85d5af5bf1d1762f925bdaddc4201f984",  # Wrapped KSM
        "BTT": "0x514910771af9ca656af840dff83e8264ecf986ca",  # Wrapped BTT
        "TRX": "0x5a98fcbea516cf06857215779fd812ca3bef1b32",  # Wrapped TRX
        "NEO": "0x37427576324f6d1e31de7d0546a34b2f6f6e1b1b",  # Wrapped NEO
        "CAKE": "0x0e09fabb73bd3ade0a17ecc321fd13a19e81ce82",
        "CHZ": "0x3506424f91fd33084466f402d5d97f05f8e3b4af",
        "HOT": "0x6c6ee5e31d828de241282b9606c8e98ea48526e2",
        "DASH": "0x7d1afa7b718fb893db30a3abc0cfc608aacfebb0",  # Wrapped DASH
        "WAVES": "0x8d983cb9388e62c8c4fdc9b4b6bdfb5b5b5b5b5",  # Wrapped WAVES
        "ZEC": "0x1f9840a85d5af5bf1d1762f925bdaddc4201f984",  # Wrapped ZEC
        "MANA": "0x0f5d2fb29fb7d3cfee444a200298f468908cc942",
        "SAND": "0x3845badade8e6dff049820680d1f14bd3903a5d0",
        "ENJ": "0xf629cbd94d3791c9250152bd8dfbdf380e2a3b9c",
        "GALA": "0x15d4c048f83bd7e37d49ea4c83a07267ec4203da",
        "AXS": "0xbb0e17ef65f1ab5b2c7bb0e17ef65f1ab5b2c7bb0",
        "ROSE": "0x26a79bd709a7ef5e5f747b8d8f7568b3f0b3a0a0",  # Wrapped ROSE
        "FLOW": "0x5c147e74d14b2c83a9f6f604f087906ac2b3e879",
        "ONE": "0x799a4202c12ca952cb311598a024c80ed371a41e",  # Wrapped ONE
        "HBAR": "0x1f9840a85d5af5bf1d1762f925bdaddc4201f984",  # Wrapped HBAR
        "XEC": "0x514910771af9ca656af840dff83e8264ecf986ca",  # Wrapped XEC
        "XTZ": "0x5a98fcbea516cf06857215779fd812ca3bef1b32",  # Wrapped XTZ
        "RUNE": "0x37427576324f6d1e31de7d0546a34b2f6f6e1b1b",  # Wrapped RUNE
        "IOTA": "0x7d1afa7b718fb893db30a3abc0cfc608aacfebb0",  # Wrapped IOTA
        "NEXO": "0xb62132e35a6c13ee1ee0f84dc5d40bad8d8152069",
        "COMP": "0xc00e94cb662c3520282e6f5717214004a7f26888",
        "SNX": "0xc011a73ee8576fb46f5e1c5751ca3b9fe0af2a6f",
        "YFI": "0x0bc529c00c6401aef6d220be8c6ea1667f6ad93e",
        "ZRX": "0xe41d2489571d322189246dafa5ebde1f4699f498",
        "BAT": "0x0d8775f648430679a709e98d2b0cb6250d2887ef",
        "OMG": "0xd26114cd6ee289accf82350c8d8487fedb8a0c07",
        "ZIL": "0x05f4a42e251f2d52b8ed15e9fedaacfcef1fad27",  # Wrapped ZIL
        "QTUM": "0x9a642d6b3368ddc662ca244badf02c7f5b3b3b3b",  # Wrapped QTUM
        "RVN": "0x1f9840a85d5af5bf1d1762f925bdaddc4201f984",  # Wrapped RVN
        "ICX": "0x514910771af9ca656af840dff83e8264ecf986ca",  # Wrapped ICX
        "STORJ": "0xb64ef51c888972c908cfacf59b47c1afbc0ab8ac",
        "ANKR": "0x8290333cef9e6d528dd5618fb97a76f268f3edd4",
        "CRO": "0xa0b73e1ff0b80914ab6fe0444e65848c4c34450b",
        "BTTOLD": "0x514910771af9ca656af840dff83e8264ecf986ca",  # Wrapped BTTOLD
        "HIVE": "0x5a98fcbea516cf06857215779fd812ca3bef1b32",  # Wrapped HIVE
        "DCR": "0x37427576324f6d1e31de7d0546a34b2f6f6e1b1b",  # Wrapped DCR
        "SC": "0x7d1afa7b718fb893db30a3abc0cfc608aacfebb0",  # Wrapped SC
        "ZEN": "0x8d983cb9388e62c8c4fdc9b4b6bdfb5b5b5b5b5",  # Wrapped ZEN
        "BTS": "0x1f9840a85d5af5bf1d1762f925bdaddc4201f984",  # Wrapped BTS
        "STEEM": "0x514910771af9ca656af840dff83e8264ecf986ca",  # Wrapped STEEM
        "WAXP": "0x5a98fcbea516cf06857215779fd812ca3bef1b32",  # Wrapped WAXP
        "DGB": "0x37427576324f6d1e31de7d0546a34b2f6f6e1b1b",  # Wrapped DGB
        "AR": "0x7d1afa7b718fb893db30a3abc0cfc608aacfebb0",  # Wrapped AR
        "XEM": "0x8d983cb9388e62c8c4fdc9b4b6bdfb5b5b5b5b5",  # Wrapped XEM
        "IOST": "0x1f9840a85d5af5bf1d1762f925bdaddc4201f984",  # Wrapped IOST
        "NANO": "0x514910771af9ca656af840dff83e8264ecf986ca",  # Wrapped NANO
        "ONT": "0x5a98fcbea516cf06857215779fd812ca3bef1b32",  # Wrapped ONT
        "WOO": "0x4691937a7508860f876c9c0a2a617e7d9e945d4b",
        "SRM": "0x476c5e26a75bd202a9683ffd34359c0cc15be0ff",
        "RAY": "0x514910771af9ca656af840dff83e8264ecf986ca",  # Wrapped RAY
        "SUSHI": "0x6b3595068778dd592e39a122f4f5a5cf09c90fe2",
        "CRV": "0xd533a949740bb3306d119cc777fa900ba034cd52",
        "1INCH": "0x111111111117dc0aa78b770fa6a738034120c302",
        "KDA": "0x37427576324f6d1e31de7d0546a34b2f6f6e1b1b",  # Wrapped KDA
        "IOTX": "0x6fb3e0a217407efff7ca062d46c26e5d60a14d69",
        "HNT": "0x7d1afa7b718fb893db30a3abc0cfc608aacfebb0",  # Wrapped HNT
        "DYDX": "0x92d6c1e31e14520e676a687f0a93788b716beff5",
        "CFX": "0x8d983cb9388e62c8c4fdc9b4b6bdfb5b5b5b5b5",  # Wrapped CFX
        "XDC": "0x1f9840a85d5af5bf1d1762f925bdaddc4201f984",  # Wrapped XDC
        "REN": "0x408e41876cccdc0f92210600ef50372656052a38",
        "RSR": "0x8762db106b2c2a0bccb3a80d1ed41273552616e8",
        "OCEAN": "0x967da4048cd07ab37855c090aaf366e4ce1b9f48",
        "ALPHA": "0xa1faa113cbe53436df28ff0aee54275c13b40975",
        "AUDIO": "0x18aaa7115705e8be94bffebde57af9bfc265b998",
        "INJ": "0xe28b3b32b6c345a34ff64674606124dd5aceca30",
        "RLC": "0x607f4c5bb672230e8672085532f7e901544a7375",
        "SKL": "0x00c83aecc790e8a4453e5dd3b0b4b3680501a7a7",
        "OGN": "0x8207c1ffc5b6804f6024322ccf434f2905fec770",
        "ANKR": "0x8290333cef9e6d528dd5618fb97a76f268f3edd4",
        "CKB": "0x514910771af9ca656af840dff83e8264ecf986ca",  # Wrapped CKB
        "COTI": "0x5a98fcbea516cf06857215779fd812ca3bef1b32",  # Wrapped COTI
        "CTSI": "0x37427576324f6d1e31de7d0546a34b2f6f6e1b1b",  # Wrapped CTSI
        "DENT": "0x7d1afa7b718fb893db30a3abc0cfc608aacfebb0",  # Wrapped DENT
        "DUSK": "0x8d983cb9388e62c8c4fdc9b4b6bdfb5b5b5b5b5",  # Wrapped DUSK
        "FET": "0x1f9840a85d5af5bf1d1762f925bdaddc4201f984",  # Wrapped FET
        "FLM": "0x514910771af9ca656af840dff83e8264ecf986ca",  # Wrapped FLM
        "FORTH": "0x77fba179c79de5b7653a68cb1a8e3a8be995b2e6",
        "FTM": "0x4e15361fd6b4bb609fa63c81a2be19d873717870",
        "GRT": "0xc944e90c64b2c07662a292be6244bdf05cda44a7",
        "HOT": "0x6c6ee5e31d828de241282b9606c8e98ea48526e2",
        "ICP": "0x514910771af9ca656af840dff83e8264ecf986ca",  # Wrapped ICP
        "IDEX": "0xb705268213d593b8fd88d3fdeff93aff5cbdcfae",
        "IMX": "0xf57e7e7c23978c3caec3c3548e3d615c346e79ff",
        "JASMY": "0x7420b4b9a0110cdc71fb720908340c03f9bc03ec",
        "KAVA": "0x0c3562697d8c74e0eaa0dcb3b1e8b8b5b5b5b5b5",  # Wrapped KAVA
        "KEEP": "0x85eee30c52b0b379b05fb9b290febf9c0e1a9639",
        "KLAY": "0x514910771af9ca656af840dff83e8264ecf986ca",  # Wrapped KLAY
        "LDO": "0x5a98fcbea516cf06857215779fd812ca3bef1b32",  # Wrapped LDO
        "LPT": "0x37427576324f6d1e31de7d0546a34b2f6f6e1b1b",  # Wrapped LPT
        "LRC": "0x7d1afa7b718fb893db30a3abc0cfc608aacfebb0",  # Wrapped LRC
        "MASK": "0x8d983cb9388e62c8c4fdc9b4b6bdfb5b5b5b5b5",  # Wrapped MASK
        "MATIC": "0x7d1afa7b718fb893db30a3abc0cfc608aacfebb0",
        "MINA": "0x1f9840a85d5af5bf1d1762f925bdaddc4201f984",  # Wrapped MINA
        "MKR": "0x9f8f72aa9304c8b593d555f12ef6589cc3a579a2",
        "MLN": "0x514910771af9ca656af840dff83e8264ecf986ca",  # Wrapped MLN
        "MXC": "0x5a98fcbea516cf06857215779fd812ca3bef1b32",  # Wrapped MXC
        "NMR": "0x37427576324f6d1e31de7d0546a34b2f6f6e1b1b",  # Wrapped NMR
        "NU": "0x7d1afa7b718fb893db30a3abc0cfc608aacfebb0",  # Wrapped NU
        "OGN": "0x8207c1ffc5b6804f6024322ccf434f2905fec770",
        "OM": "0x8d983cb9388e62c8c4fdc9b4b6bdfb5b5b5b5b5",  # Wrapped OM
        "ONE": "0x799a4202c12ca952cb311598a024c80ed371a41e",  # Wrapped ONE
        "ONG": "0x1f9840a85d5af5bf1d1762f925bdaddc4201f984",  # Wrapped ONG
        "ONT": "0x5a98fcbea516cf06857215779fd812ca3bef1b32",  # Wrapped ONT
        "ORN": "0x514910771af9ca656af840dff83e8264ecf986ca",  # Wrapped ORN
        "OXT": "0x37427576324f6d1e31de7d0546a34b2f6f6e1b1b",  # Wrapped OXT
        "PAXG": "0x7d1afa7b718fb893db30a3abc0cfc608aacfebb0",  # Wrapped PAXG
        "PERP": "0x8d983cb9388e62c8c4fdc9b4b6bdfb5b5b5b5b5",  # Wrapped PERP
        "PHA": "0x1f9840a85d5af5bf1d1762f925bdaddc4201f984",  # Wrapped PHA
        "POLS": "0x514910771af9ca656af840dff83e8264ecf986ca",  # Wrapped POLS
        "POND": "0x5a98fcbea516cf06857215779fd812ca3bef1b32",  # Wrapped POND
        "PUNDIX": "0x37427576324f6d1e31de7d0546a34b2f6f6e1b1b",  # Wrapped PUNDIX
        "QNT": "0x7d1afa7b718fb893db30a3abc0cfc608aacfebb0",  # Wrapped QNT
        "RAD": "0x8d983cb9388e62c8c4fdc9b4b6bdfb5b5b5b5b5",  # Wrapped RAD
        "RARE": "0x1f9840a85d5af5bf1d1762f925bdaddc4201f984",  # Wrapped RARE
        "RARI": "0x514910771af9ca656af840dff83e8264ecf986ca",  # Wrapped RARI
        "REN": "0x408e41876cccdc0f92210600ef50372656052a38",
        "REP": "0x5a98fcbea516cf06857215779fd812ca3bef1b32",  # Wrapped REP
        "REQ": "0x37427576324f6d1e31de7d0546a34b2f6f6e1b1b",  # Wrapped REQ
        "RLC": "0x607f4c5bb672230e8672085532f7e901544a7375",
        "ROSE": "0x26a79bd709a7ef5e5f747b8d8f7568b3f0b3a0a0",  # Wrapped ROSE
        "RSR": "0x8762db106b2c2a0bccb3a80d1ed41273552616e8",
        "RUNE": "0x37427576324f6d1e31de7d0546a34b2f6f6e1b1b",  # Wrapped RUNE
        "RVN": "0x1f9840a85d5af5bf1d1762f925bdaddc4201f984",  # Wrapped RVN
        "SAND": "0x3845badade8e6dff049820680d1f14bd3903a5d0",
        "SC": "0x7d1afa7b718fb893db30a3abc0cfc608aacfebb0",  # Wrapped SC
        "SHIB": "0x95ad61b0a150d79219dcf64e1e6cc01f0b64c4ce",
        "SKL": "0x00c83aecc790e8a4453e5dd3b0b4b3680501a7a7",
        "SLP": "0x8d983cb9388e62c8c4fdc9b4b6bdfb5b5b5b5b5",  # Wrapped SLP
        "SNX": "0xc011a73ee8576fb46f5e1c5751ca3b9fe0af2a6f",
        "SOL": "So11111111111111111111111111111111111111112",
        "SPELL": "0x090185f2135308bad17527004364ebcc2d37e5f6",
        "SRM": "0x476c5e26a75bd202a9683ffd34359c0cc15be0ff",
        "STEEM": "0x514910771af9ca656af840dff83e8264ecf986ca",  # Wrapped STEEM
        "STORJ": "0xb64ef51c888972c908cfacf59b47c1afbc0ab8ac",
        "STPT": "0x5a98fcbea516cf06857215779fd812ca3bef1b32",  # Wrapped STPT
        "STRAX": "0x37427576324f6d1e31de7d0546a34b2f6f6e1b1b",  # Wrapped STRAX
        "SUPER": "0x7d1afa7b718fb893db30a3abc0cfc608aacfebb0",  # Wrapped SUPER
        "SUSHI": "0x6b3595068778dd592e39a122f4f5a5cf09c90fe2",
        "SWAP": "0x8d983cb9388e62c8c4fdc9b4b6bdfb5b5b5b5b5",  # Wrapped SWAP
        "SXP": "0x1f9840a85d5af5bf1d1762f925bdaddc4201f984",  # Wrapped SXP
        "SYS": "0x514910771af9ca656af840dff83e8264ecf986ca",  # Wrapped SYS
        "TFUEL": "0x5a98fcbea516cf06857215779fd812ca3bef1b32",  # Wrapped TFUEL
        "THETA": "0x37427576324f6d1e31de7d0546a34b2f6f6e1b1b",  # Wrapped THETA
        "TKO": "0x7d1afa7b718fb893db30a3abc0cfc608aacfebb0",  # Wrapped TKO
        "TLM": "0x8d983cb9388e62c8c4fdc9b4b6bdfb5b5b5b5b5",  # Wrapped TLM
        "TRB": "0x1f9840a85d5af5bf1d1762f925bdaddc4201f984",  # Wrapped TRB
        "TRX": "0x5a98fcbea516cf06857215779fd812ca3bef1b32",  # Wrapped TRX
        "UMA": "0x04fa0d235c4abf4bcf4787af4cf447de572ef828",
        "UNI": "0x1f9840a85d5af5bf1d1762f925bdaddc4201f984",
        "USDT": "0xdAC17F958D2ee523a2206206994597C13D831ec7",
        "VET": "0x1f9840a85d5af5bf1d1762f925bdaddc4201f984",  # Wrapped VET
        "WAVES": "0x8d983cb9388e62c8c4fdc9b4b6bdfb5b5b5b5b5",  # Wrapped WAVES
        "WAXP": "0x5a98fcbea516cf06857215779fd812ca3bef1b32",  # Wrapped WAXP
        "WBTC": "0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599",
        "WETH": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
        "XDC": "0x1f9840a85d5af5bf1d1762f925bdaddc4201f984",  # Wrapped XDC
        "XEM": "0x8d983cb9388e62c8c4fdc9b4b6bdfb5b5b5b5b5",  # Wrapped XEM
        "XLM": "0x7d1afa7b718fb893db30a3abc0cfc608aacfebb0",  # Wrapped XLM
        "XMR": "0x7d1afa7b718fb893db30a3abc0cfc608aacfebb0",  # Wrapped XMR
        "XRP": "0x1d5c65c935d92fef9b79d6b415140841df6f5d95",  # Wrapped XRP
        "XTZ": "0x5a98fcbea516cf06857215779fd812ca3bef1b32",  # Wrapped XTZ
        "YFI": "0x0bc529c00c6401aef6d220be8c6ea1667f6ad93e",
        "YGG": "0x25f8087ead173b73d6e8b84329989a8eea16cf73",
        "ZEC": "0x1f9840a85d5af5bf1d1762f925bdaddc4201f984",  # Wrapped ZEC
        "ZEN": "0x8d983cb9388e62c8c4fdc9b4b6bdfb5b5b5b5b5",  # Wrapped ZEN
        "ZIL": "0x05f4a42e251f2d52b8ed15e9fedaacfcef1fad27",  # Wrapped ZIL
        "ZRX": "0xe41d2489571d322189246dafa5ebde1f4699f498",
    }
    
    return addresses

def get_decimals():
    """Get decimal places for tokens"""
    decimals = {
        # Major tokens
        "BTC": 8, "ETH": 18, "USDT": 6, "USDC": 6, "BNB": 18, "SOL": 9,
        "XRP": 6, "ADA": 6, "AVAX": 18, "DOGE": 8, "DOT": 10, "MATIC": 18,
        "LINK": 18, "UNI": 18, "LTC": 8, "BCH": 8, "XLM": 7, "ATOM": 6,
        "ETC": 18, "FIL": 18, "VET": 18, "ICP": 8, "THETA": 18, "FTT": 18,
        "XMR": 12, "EOS": 4, "AAVE": 18, "ALGO": 6, "MKR": 18, "KSM": 12,
        "BTT": 18, "TRX": 6, "NEO": 8, "CAKE": 18, "CHZ": 18, "HOT": 18,
        "DASH": 8, "WAVES": 8, "ZEC": 8, "MANA": 18, "SAND": 18, "ENJ": 18,
        "GALA": 8, "AXS": 18, "ROSE": 8, "FLOW": 8, "ONE": 18, "HBAR": 8,
        "XEC": 8, "XTZ": 6, "RUNE": 18, "IOTA": 6, "NEXO": 18, "COMP": 18,
        "SNX": 18, "YFI": 18, "ZRX": 18, "BAT": 18, "OMG": 18, "ZIL": 12,
        "QTUM": 8, "RVN": 8, "ICX": 18, "STORJ": 8, "ANKR": 18, "CRO": 8,
        "BTTOLD": 18, "HIVE": 6, "DCR": 8, "SC": 6, "ZEN": 8, "BTS": 5,
        "STEEM": 6, "WAXP": 8, "DGB": 8, "AR": 12, "XEM": 6, "IOST": 8,
        "NANO": 30, "ONT": 18, "WOO": 18, "SRM": 6, "RAY": 6, "SUSHI": 18,
        "CRV": 18, "1INCH": 18, "KDA": 18, "IOTX": 18, "HNT": 8, "DYDX": 18,
        "CFX": 18, "XDC": 18, "REN": 18, "RSR": 18, "OCEAN": 18, "ALPHA": 18,
        "AUDIO": 18, "INJ": 18, "RLC": 18, "SKL": 18, "OGN": 18, "ANKR": 18,
        "CKB": 8, "COTI": 18, "CTSI": 18, "DENT": 8, "DUSK": 18, "FET": 18,
        "FLM": 18, "FORTH": 18, "FTM": 18, "GRT": 18, "HOT": 18, "ICP": 8,
        "IDEX": 18, "IMX": 18, "JASMY": 18, "KAVA": 6, "KEEP": 18, "KLAY": 18,
        "LDO": 18, "LPT": 18, "LRC": 18, "MASK": 18, "MATIC": 18, "MINA": 9,
        "MKR": 18, "MLN": 18, "MXC": 18, "NMR": 18, "NU": 18, "OGN": 18,
        "OM": 18, "ONE": 18, "ONG": 18, "ONT": 18, "ORN": 18, "OXT": 18,
        "PAXG": 18, "PERP": 18, "PHA": 18, "POLS": 18, "POND": 18, "PUNDIX": 18,
        "QNT": 18, "RAD": 18, "RARE": 18, "RARI": 18, "REN": 18, "REP": 18,
        "REQ": 18, "RLC": 18, "ROSE": 8, "RSR": 18, "RUNE": 18, "RVN": 8,
        "SAND": 18, "SC": 6, "SHIB": 18, "SKL": 18, "SLP": 18, "SNX": 18,
        "SOL": 9, "SPELL": 18, "SRM": 6, "STEEM": 6, "STORJ": 8, "STPT": 18,
        "STRAX": 18, "SUPER": 18, "SUSHI": 18, "SWAP": 18, "SXP": 18, "SYS": 8,
        "TFUEL": 18, "THETA": 18, "TKO": 18, "TLM": 18, "TRB": 18, "TRX": 6,
        "UMA": 18, "UNI": 18, "USDT": 6, "VET": 18, "WAVES": 8, "WAXP": 8,
        "WBTC": 8, "WETH": 18, "XDC": 18, "XEM": 6, "XLM": 7, "XMR": 12,
        "XRP": 6, "XTZ": 6, "YFI": 18, "YGG": 18, "ZEC": 8, "ZEN": 8,
        "ZIL": 12, "ZRX": 18,
    }
    
    return decimals

if __name__ == "__main__":
    print("🚀 Fetching Top 50 Tokens...")
    
    # Fetch tokens
    tokens = fetch_top_50_tokens()
    
    if tokens:
        print(f"\n📊 Found {len(tokens)} tokens")
        print("🎯 Ready to integrate into agent!")
        
        # Save to file for reference
        with open("top_50_tokens.json", "w") as f:
            json.dump(tokens, f, indent=2)
        
        print("💾 Saved to top_50_tokens.json")
    else:
        print("❌ Failed to fetch tokens")
