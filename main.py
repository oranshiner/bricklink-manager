#!/usr/bin/env python3
"""
BrickLink Inventory Manager - XML Edition
Simple command-line script to get prices for minifigures, parts, and sets from BrickLink XML inventory.

Requirements:
- BrickLink API credentials in .env file
- pip install requests requests-oauthlib python-dotenv

Usage:
    python main.py --xml Minifigures.xml
    python main.py --xml Parts.xml
    python main.py --xml Sets.xml
    python main.py --xml Minifigures.xml --condition U --export prices --markup 15
"""

import os
import sys
import argparse
import json
import xml.etree.ElementTree as ET
from xml.dom import minidom
from typing import List, Dict, Any
import requests
from requests_oauthlib import OAuth1Session
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Maps XML ITEMTYPE codes to BrickLink API type strings
ITEM_TYPE_MAP = {
    'M': 'MINIFIG',
    'P': 'PART',
    'S': 'SET',
}

ITEM_TYPE_LABELS = {
    'M': 'minifigure',
    'P': 'part',
    'S': 'set',
}


class BricklinkAPI:
    """
    A wrapper for the BrickLink API (v1) to fetch minifigure price data.
    Handles OAuth1 authentication and API requests.
    """
    def __init__(self):
        """Initialize with OAuth credentials from .env file."""
        self.consumer_key = os.getenv('BRICKLINK_CONSUMER_KEY')
        self.consumer_secret = os.getenv('BRICKLINK_CONSUMER_SECRET')
        self.token_key = os.getenv('BRICKLINK_TOKEN_KEY')
        self.token_secret = os.getenv('BRICKLINK_TOKEN_SECRET')

        if not all([self.consumer_key, self.consumer_secret, self.token_key, self.token_secret]):
            raise ValueError(
                "Missing BrickLink API credentials. Please create a .env file with:\n"
                "BRICKLINK_CONSUMER_KEY=your_consumer_key\n"
                "BRICKLINK_CONSUMER_SECRET=your_consumer_secret\n"
                "BRICKLINK_TOKEN_KEY=your_token_key\n"
                "BRICKLINK_TOKEN_SECRET=your_token_secret"
            )
        
        # BrickLink API v1 base URL
        self.base_url = 'https://api.bricklink.com/api/store/v1'
        
        self.session = OAuth1Session(
            self.consumer_key,
            client_secret=self.consumer_secret,
            resource_owner_key=self.token_key,
            resource_owner_secret=self.token_secret,
            signature_method='HMAC-SHA1'
        )
    
    def get_item_price(self, item_id: str, item_type: str = 'MINIFIG', condition: str = 'N', debug: bool = False) -> Dict[str, Any]:
        """
        Get price information for a specific item (minifigure, part, or set).

        Args:
            item_id: Item number (e.g., 'sp006', '3001', '75192-1')
            item_type: API item type string: 'MINIFIG', 'PART', or 'SET'
            condition: 'N' for new, 'U' for used
            debug: If True, print debug information

        Returns:
            API response dictionary with price data
        """
        # IMPORTANT: Item type must be UPPERCASE
        url = f"{self.base_url}/items/{item_type}/{item_id}/price"
        params = {
            'new_or_used': condition,
            'guide_type': 'stock',
            'currency_code': 'USD'
        }
        
        if debug:
            print(f"\nDEBUG: Requesting URL: {url}")
            print(f"DEBUG: Parameters: {params}")
            print(f"DEBUG: Consumer Key: {self.consumer_key[:8]}...")
            print(f"DEBUG: Token Key: {self.token_key[:8]}...")
        
        try:
            response = self.session.get(url, params=params)
            
            if debug:
                print(f"DEBUG: Response Status Code: {response.status_code}")
                print(f"DEBUG: Response Headers: {dict(response.headers)}")
                print(f"DEBUG: Response Text: {response.text[:500]}")
            
            # Don't raise for status yet, so we can see the full error
            data = response.json()
            
            if debug:
                print(f"DEBUG: Full Response JSON: {json.dumps(data, indent=2)}")
            
            if data.get('meta', {}).get('code') == 200:
                return {
                    'success': True,
                    'itemid': item_id,
                    'item_type': item_type,
                    'condition': condition,
                    'data': data.get('data', {})
                }
            else:
                error_msg = data.get('meta', {}).get('message', 'Unknown error')
                error_desc = data.get('meta', {}).get('description', '')
                full_error = f"{error_msg}" + (f" - {error_desc}" if error_desc else "")

                return {
                    'success': False,
                    'itemid': item_id,
                    'item_type': item_type,
                    'error': full_error,
                    'status_code': response.status_code
                }

        except Exception as e:
            error_msg = str(e)
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_data = e.response.json()
                    error_msg = error_data.get('meta', {}).get('message', str(e))
                    if debug:
                        print(f"DEBUG: Exception Response: {error_data}")
                except:
                    error_msg = f"HTTP {e.response.status_code}: {e.response.text}"

            if debug:
                print(f"DEBUG: Exception occurred: {type(e).__name__}: {e}")

            return {
                'success': False,
                'itemid': item_id,
                'item_type': item_type,
                'error': error_msg,
                'status_code': getattr(e.response, 'status_code', None) if hasattr(e, 'response') else None
            }


def parse_xml_inventory(xml_file: str) -> List[Dict[str, Any]]:
    """
    Parse BrickLink XML inventory file and extract item data.
    Supports minifigures (M), parts (P), and sets (S).

    Args:
        xml_file: Path to the XML inventory file

    Returns:
        List of dictionaries containing item information
    """
    try:
        tree = ET.parse(xml_file)
        root = tree.getroot()

        items = []
        for item in root.findall('.//ITEM'):
            itemtype = item.find('ITEMTYPE')
            itemid = item.find('ITEMID')
            color = item.find('COLOR')
            qty = item.find('QTY')
            condition = item.find('CONDITION')

            if (itemtype is not None and itemtype.text in ITEM_TYPE_MAP and
                    itemid is not None and itemid.text):

                items.append({
                    'itemid': itemid.text,
                    'itemtype': itemtype.text,
                    'color': color.text if color is not None else '0',
                    'quantity': int(qty.text) if qty is not None and qty.text.isdigit() else 1,
                    'condition': condition.text if condition is not None else 'U'
                })

        return items

    except ET.ParseError as e:
        print(f"Error parsing XML file: {e}")
        return []
    except FileNotFoundError:
        print(f"Error: XML file '{xml_file}' not found.")
        return []
    except Exception as e:
        print(f"Error reading XML file: {e}")
        return []


def format_price_data(price_data: Dict[str, Any]) -> str:
    """
    Format price data dictionary into a human-readable string.
    """
    if not price_data:
        return "No price data available"
    
    lines = []
    
    avg_price = price_data.get('avg_price')
    if avg_price:
        lines.append(f"Average: ${avg_price}")
    
    min_price = price_data.get('min_price')
    max_price = price_data.get('max_price')
    if min_price and max_price:
        lines.append(f"Range: ${min_price} - ${max_price}")
    
    qty_avg_price = price_data.get('qty_avg_price')
    if qty_avg_price:
        lines.append(f"Qty Available: {qty_avg_price}")
    
    unit_quantity = price_data.get('unit_quantity', 1)
    if unit_quantity > 1:
        lines.append(f"Price per {unit_quantity} units")
    
    return " | ".join(lines) if lines else "No pricing information"


def get_prices_for_inventory(api: 'BricklinkAPI', items: List[Dict[str, Any]],
                             condition_filter: str = None, debug: bool = False) -> List[Dict[str, Any]]:
    """
    Get prices for all items in inventory.
    """
    results = []
    processed_items = set()

    print(f"Getting prices for {len(items)} entries...")

    for i, item in enumerate(items, 1):
        itemid = item['itemid']
        itemtype = item['itemtype']
        condition = item['condition']
        quantity = item['quantity']
        api_type = ITEM_TYPE_MAP[itemtype]

        if condition_filter and condition != condition_filter:
            continue

        unique_key = f"{itemid}_{itemtype}_{condition}"
        if unique_key in processed_items:
            continue
        processed_items.add(unique_key)

        print(f"[{i}/{len(items)}] Getting price for {itemid} ({api_type}, {condition})...")

        result = api.get_item_price(itemid, api_type, condition, debug=(debug or i == 1))
        result['quantity'] = quantity

        # If used price not found, try new price as fallback
        if condition == 'U' and result['success'] and not result['data'].get('avg_price'):
            print(f"  No used price found, checking new price...")
            new_result = api.get_item_price(itemid, api_type, 'N', debug=debug)
            if new_result['success'] and new_result['data'].get('avg_price'):
                result['data'] = new_result['data']
                print(f"  Using new price: ${new_result['data']['avg_price']}")

        results.append(result)

        import time
        time.sleep(0.1)

    return results


def print_price_summary(results: List[Dict[str, Any]]):
    """
    Print a formatted summary of price results.
    """
    successful = [r for r in results if r['success']]
    failed = [r for r in results if not r['success']]
    
    print(f"\n{'='*80}")
    print(f"PRICE SUMMARY")
    print(f"{'='*80}")
    print(f"Successfully retrieved: {len(successful)} prices")
    print(f"Failed: {len(failed)} items")
    print(f"{'='*80}")
    
    if successful:
        total_estimated_value = 0
        print(f"\n{'Item':<12} {'Cond':<4} {'Qty':<3} {'Price Info'}")
        print(f"{'-'*12} {'-'*4} {'-'*3} {'-'*50}")
        
        for result in successful:
            itemid = result['itemid']
            condition = result['condition']
            quantity = result.get('quantity', 1)
            price_info = format_price_data(result['data'])

            print(f"{itemid:<12} {condition:<4} {quantity:<3} {price_info}")

            avg_price = result['data'].get('avg_price')
            if avg_price:
                try:
                    total_estimated_value += float(avg_price) * quantity
                except (ValueError, TypeError):
                    pass

        if total_estimated_value > 0:
            print(f"\nEstimated Total Collection Value: ${total_estimated_value:.2f}")

    if failed:
        print(f"\nFAILED TO GET PRICES FOR:")
        for result in failed:
            print(f"  {result['itemid']}: {result['error']}")


def create_bricklink_upload_xml(results: List[Dict[str, Any]], markup_percent: float = 10.0) -> str:
    """
    Create BrickLink Mass Upload XML format.
    
    Args:
        results: Full results from price lookup
        markup_percent: Percentage to add to prices (default 10%)
        
    Returns:
        XML string in BrickLink Mass Upload format
    """
    # Build XML manually to match BrickLink's exact format
    lines = ['<INVENTORY>']
    
    for result in results:
        lines.append('    <ITEM>')
        
        # CATEGORY - empty for minifigs
        lines.append('        <CATEGORY></CATEGORY>')
        
        # COLOR - default to 0 for minifigs
        lines.append('        <COLOR>0</COLOR>')
        
        # PRICE - use average price if available, add markup
        if result['success']:
            avg_price = result['data'].get('avg_price')
            if avg_price:
                # Add markup percentage
                price_with_markup = float(avg_price) * (1 + markup_percent / 100)
                price_value = f"{price_with_markup:.2f}"
            else:
                price_value = '0.00'
        else:
            price_value = '0.00'
        lines.append(f'        <PRICE>{price_value}</PRICE>')
        
        # QTY
        quantity = result.get('quantity', 1)
        lines.append(f'        <QTY>{quantity}</QTY>')
        
        # BULK
        lines.append('        <BULK>1</BULK>')
        
        # DESCRIPTION - empty
        lines.append('        <DESCRIPTION></DESCRIPTION>')
        
        # CONDITION
        condition = result.get('condition', 'U')
        lines.append(f'        <CONDITION>{condition}</CONDITION>')

        # ITEMTYPE - from result
        api_type = result.get('item_type', 'MINIFIG')
        xml_type = {v: k for k, v in ITEM_TYPE_MAP.items()}.get(api_type, 'M')
        lines.append(f'        <ITEMTYPE>{xml_type}</ITEMTYPE>')

        # ITEMID
        itemid = result['itemid']
        lines.append(f'        <ITEMID>{itemid}</ITEMID>')
        
        lines.append('    </ITEM>')
    
    lines.append('</INVENTORY>')
    
    return '\n'.join(lines)


def create_simplified_json(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Create a simplified JSON export with minifig number, amount, and average price.
    
    Args:
        results: Full results from price lookup
        
    Returns:
        List of simplified dictionaries for export
    """
    simplified = []
    
    for result in results:
        if result['success']:
            avg_price = result['data'].get('avg_price')
            entry = {
                'item_id': result['itemid'],
                'item_type': result.get('item_type', 'MINIFIG'),
                'amount': result.get('quantity', 1),
                'average_price': float(avg_price) if avg_price else None,
                'condition': result['condition']
            }
            simplified.append(entry)
        else:
            entry = {
                'item_id': result['itemid'],
                'item_type': result.get('item_type', 'MINIFIG'),
                'amount': result.get('quantity', 1),
                'average_price': None,
                'condition': result.get('condition', 'U'),
                'error': result.get('error')
            }
            simplified.append(entry)
    
    return simplified


def print_setup_instructions():
    """Print instructions for setting up API credentials."""
    print("\n" + "="*60)
    print("SETUP REQUIRED: BrickLink API Credentials")
    print("="*60)
    print("1. Go to: https://www.bricklink.com/v2/api/register_consumer.page")
    print("2. Register your application and get 4 credentials")
    print("3. Create a .env file in the same directory with:")
    print("")
    print("   BRICKLINK_CONSUMER_KEY=your_consumer_key")
    print("   BRICKLINK_CONSUMER_SECRET=your_consumer_secret")
    print("   BRICKLINK_TOKEN_KEY=your_token_value")
    print("   BRICKLINK_TOKEN_SECRET=your_token_secret")
    print("")
    print("4. Install required Python packages:")
    print("   pip install requests requests-oauthlib python-dotenv")
    print("="*60)


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description='Get prices for items from BrickLink XML inventory (minifigures, parts, sets)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  python main.py --xml Minifigures.xml
  python main.py --xml Parts.xml
  python main.py --xml Sets.xml
  python main.py --xml Minifigures.xml --condition U --export prices --markup 15
        '''
    )
    
    parser.add_argument('--xml', '-x', type=str, 
                       help='Path to BrickLink XML inventory file')
    parser.add_argument('--condition', '-c', choices=['N', 'U'], 
                       help='Filter by condition: N (new) or U (used)')
    parser.add_argument('--prices-only', '-p', action='store_true',
                       help='Only show price information (no summary)')
    parser.add_argument('--export', '-e', type=str,
                       help='Export results (creates .xml and .json files)')
    parser.add_argument('--markup', '-m', type=float, default=10.0,
                       help='Markup percentage to add to prices (default: 10%%)')
    parser.add_argument('--setup', action='store_true',
                       help='Show setup instructions')
    parser.add_argument('--debug', '-d', action='store_true',
                       help='Enable debug output for API calls')
    
    args = parser.parse_args()
    
    if args.setup:
        print_setup_instructions()
        return
    
    if not args.xml:
        for default in ('Minifigures.xml', 'Parts.xml', 'Sets.xml'):
            if os.path.exists(default):
                args.xml = default
                print(f"No XML file specified, using '{default}'")
                break
        else:
            print("Error: No XML file specified.")
            print("Usage: python main.py --xml your_file.xml")
            return

    print(f"Parsing XML inventory: {args.xml}")
    items = parse_xml_inventory(args.xml)

    if not items:
        print("No supported items found in XML file!")
        return

    item_types_found = set(m['itemtype'] for m in items)
    type_labels = ', '.join(ITEM_TYPE_LABELS.get(t, t) for t in sorted(item_types_found))
    print(f"Found {len(items)} entries in XML ({type_labels})")

    if not args.prices_only:
        unique_items = set(m['itemid'] for m in items)
        conditions = set(m['condition'] for m in items)
        total_quantity = sum(m['quantity'] for m in items)

        print(f"  Unique items: {len(unique_items)}")
        print(f"  Total quantity: {total_quantity}")
        print(f"  Conditions: {', '.join(sorted(conditions))}")

        if args.condition:
            filtered_count = len([m for m in items if m['condition'] == args.condition])
            print(f"  Filtering for condition '{args.condition}': {filtered_count} items")
    
    try:
        api = BricklinkAPI()
        if args.debug:
            print("\n=== DEBUG MODE ENABLED ===")
            print(f"API Base URL: {api.base_url}")
            print(f"Consumer Key: {api.consumer_key[:10]}...{api.consumer_key[-4:]}")
            print(f"Consumer Secret: {api.consumer_secret[:10]}...{api.consumer_secret[-4:]}")
            print(f"Token Key: {api.token_key[:10]}...{api.token_key[-4:]}")
            print(f"Token Secret: {api.token_secret[:10]}...{api.token_secret[-4:]}")
            print("=" * 30)
    except ValueError as e:
        print(f"\nError: {e}")
        print("\nRun with --setup for instructions:")
        print("python bricklink_xml_manager.py --setup")
        return
    
    results = get_prices_for_inventory(api, items, args.condition, args.debug)
    
    if not results:
        print("No results to display!")
        return
    
    print_price_summary(results)
    
    if args.export:
        try:
            base_name = args.export.rsplit('.', 1)[0]
            
            # Create and save BrickLink Mass Upload XML with markup
            xml_output = create_bricklink_upload_xml(results, args.markup)
            xml_filename = f"{base_name}.xml"
            with open(xml_filename, 'w', encoding='utf-8') as f:
                f.write(xml_output)
            print(f"\nBrickLink Mass Upload XML exported to: {xml_filename}")
            print(f"  (Prices increased by {args.markup}%)")
            
            # Create and save simplified JSON
            simplified_data = create_simplified_json(results)
            json_filename = f"{base_name}.json"
            with open(json_filename, 'w') as f:
                json.dump(simplified_data, f, indent=2)
            print(f"Simplified JSON exported to: {json_filename}")
            
            # Also save full detailed results
            detailed_export = f"{base_name}_detailed.json"
            with open(detailed_export, 'w') as f:
                json.dump(results, f, indent=2)
            print(f"Detailed results exported to: {detailed_export}")
            
        except Exception as e:
            print(f"Error exporting results: {e}")


if __name__ == '__main__':
    main()