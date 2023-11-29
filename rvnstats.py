import os
from flask import Flask, jsonify
import time
import requests
import json
from decimal import Decimal, getcontext

rpc_url = 'http://127.0.0.1:8766/'  # Replace with your node's RPC URL
rpc_user = 'raven'
rpc_password = 'raven'
headers = {'content-type': 'application/json'}

app = Flask(__name__)

ILLEGAL_RVN_SUPPLY = Decimal("301804400.51605644") 

# Function to get current Unix time in milliseconds
def get_current_unix_time_ms():
    return int(time.time() * 1000)


def truncate_decimal_to_eight_places(d):
    # Define the quantizing value to 8 decimal places
    eight_places = Decimal('0.00000001')

    # Truncate/quantize the Decimal object to 8 decimal places
    return d.quantize(eight_places)


# Optimization to prevent overloading cryptoscope.io
def persist_decimal_for_10_minutes(decimal_value=None):
    filename = 'decimal_data.json';

    if decimal_value is not None:
        # If a new value is provided, save it with the current timestamp
        with open(filename, 'w') as file:
            data = {
                'value': str(decimal_value),  # Convert Decimal to string for JSON serialization
                'timestamp': time.time()
            }
            json.dump(data, file)
    else:
        # Check if the file exists
        if not os.path.exists(filename):
            return None

        # Retrieve the stored value and its timestamp
        with open(filename, 'r') as file:
            data = json.load(file)
            saved_time = data['timestamp']
            saved_value = Decimal(data['value'])

            # Check if 10 minutes have passed
            if time.time() - saved_time > 600:  # 600 seconds = 10 minutes
                return None
            else:
                return saved_value



def get_block_height():
    payload = {
        "method": "getinfo",  # The RPC method to call; might differ based on the node's API
        "params": [],  # Any parameters required for the method
        "jsonrpc": "2.0",
        "id": 0,
    }

    response = requests.post(rpc_url, auth=(rpc_user, rpc_password), headers=headers, data=json.dumps(payload))

    if response.status_code == 200:
        result = response.json()
        # Extract the relevant data (like circulating supply) from the result
        # Note: You may need to adjust the key names based on the actual response structure
        block_height = result['result'].get('blocks', None)
        return block_height
    else:
        return 0


def calculate_ravencoin_supply(block_height):
    # Initial block reward in RVN
    initial_block_reward = 5000

    # Halving interval in blocks
    halving_interval = 2100000

    # Calculate the number of halvings that have occurred
    num_halvings = block_height // halving_interval

    # Total supply starts at 0
    total_supply = 0

    # For each halving, add the RVN created in that era
    for i in range(num_halvings):
        # Calculate the number of blocks in this era
        blocks_this_era = halving_interval

        # Calculate the block reward for this era
        block_reward = initial_block_reward / (2 ** i)

        # Add the RVN created in this era to the total
        total_supply += block_reward * blocks_this_era

    # Add the RVN created in the current era (post-last halving)
    blocks_current_era = block_height % halving_interval
    current_era_reward = initial_block_reward / (2 ** num_halvings)
    total_supply += blocks_current_era * current_era_reward

    return total_supply


ravencoin_burn_addresses = [
    "RXissueAssetXXXXXXXXXXXXXXXXXhhZGt",
    "RXBurnXXXXXXXXXXXXXXXXXXXXXXWUo9FV",
    "RXReissueAssetXXXXXXXXXXXXXXVEFAWu",
    "RXissueSubAssetXXXXXXXXXXXXXWcwhwL",
    "RXissueUniqueAssetXXXXXXXXXXWEAe58",
    "RXissueQuaLifierXXXXXXXXXXXXUgEDbC",
    "RXissueRestrictedXXXXXXXXXXXXzJZ1q",
    "RXissueMsgChanneLAssetXXXXXXSjHvAY",
    "RXissueSubQuaLifierXXXXXXXXXVTzvv5",
    "RXaddTagBurnXXXXXXXXXXXXXXXXZQm5ya",
    "RVNAssetHoLeXXXXXXXXXXXXXXXXZCEMy6"
]

# Get the sum of burn balances
def get_total_ravencoin_balance(addresses):
    # Set to 8 decimal precision
    getcontext().prec = 19
    
    base_url = "https://rvn.cryptoscope.io/api/getbalance/?address={}&legacy=1"

    total_balance = Decimal(0.0)

    for address in addresses:
        url = base_url.format(address)
        try:
            response = requests.get(url)
            if response.status_code == 200:
                balance_data = response.json()  # Assuming the API returns JSON data
                total_balance += truncate_decimal_to_eight_places(Decimal(balance_data))  # Add the balance for this address
            else:
                print(f"Failed to get balance for address {address}: HTTP {response.status_code}")
        except requests.RequestException as e:
            print(f"Request failed for address {address}: {e}")

    return total_balance    

def update_data_fields(data):
    burned_supply = persist_decimal_for_10_minutes();
    if (burned_supply == None):
        burned_supply = Decimal(get_total_ravencoin_balance(ravencoin_burn_addresses));
        persist_decimal_for_10_minutes(truncate_decimal_to_eight_places(burned_supply));
    block_height = get_block_height();
    supply = calculate_ravencoin_supply(block_height)
    for item in data:
        item['blockHeight'] = block_height;
        item['maxSupply'] = Decimal('21000000000.0') + Decimal(ILLEGAL_RVN_SUPPLY)
        item['burnedSupply'] = burned_supply;
        item['price'] = None
        item['lastUpdatedTimestamp'] = get_current_unix_time_ms();
        item['circulatingSupply'] = Decimal(supply) + Decimal(ILLEGAL_RVN_SUPPLY) - burned_supply ;
    return data

# Example data
def get_data_template():
    return [
        {
        "symbol": "RVN",
        "currencyCode": "USD",
        "price": None,
        "marketCap": None,
        "blockHeight": None,
        "accTradePrice24h": None,
        "circulatingSupply": None,
        "maxSupply": None,
        "burnedSupply": None,
        "provider": "Ravencoin Foundation",
        "lastUpdatedTimestamp": None
        }
    ]


@app.route('/api/RVN/info', methods=['GET'])
def get_info():
    # Here you would typically fetch or compute the data dynamically.
    # For simplicity, we are returning the static data defined above.

    data = get_data_template();
    data = update_data_fields(data)

    return jsonify(data)

if __name__ == '__main__':
    app.run(debug=True)
