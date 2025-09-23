"""
Tests for DAS CMD API Response Parsers
"""

import unittest
from decimal import Decimal
from das_trader.parsers import (
    DASResponseParser,
    SmallCapsParser,
    ParsedOrder,
    ParsedTrade,
    ParsedQuote,
    ParsedShortInfo,
    MessageType
)


class TestDASResponseParser(unittest.TestCase):
    """Test the main DAS response parser"""
    
    def test_identify_message_type(self):
        """Test message type identification"""
        # Test ORDER
        self.assertEqual(
            DASResponseParser.identify_message_type("%ORDER 123 456 CIGL B L 5 0 0 3.50"),
            MessageType.ORDER
        )
        
        # Test TRADE
        self.assertEqual(
            DASResponseParser.identify_message_type("%TRADE 123 CIGL B 10 3.50"),
            MessageType.TRADE
        )
        
        # Test QUOTE
        self.assertEqual(
            DASResponseParser.identify_message_type("$QUOTE AAPL 150.25 150.35 150.30"),
            MessageType.QUOTE
        )
        
        # Test SHORTINFO
        self.assertEqual(
            DASResponseParser.identify_message_type("$SHORTINFO CIGL Y 100000"),
            MessageType.SHORTINFO
        )
        
        # Test ERROR
        self.assertEqual(
            DASResponseParser.identify_message_type("ERROR: Invalid command"),
            MessageType.ERROR
        )
        
        # Test UNKNOWN
        self.assertEqual(
            DASResponseParser.identify_message_type("Some random text"),
            MessageType.UNKNOWN
        )
    
    def test_parse_order_line(self):
        """Test parsing of order lines"""
        line = "%ORDER 52493 586 CIGL B L 5 0 0 2.97 ARCA Executed 09:53:27 0 ZIMDASE9C64 ZIMDASE9C64 Hotkey"
        
        order = DASResponseParser.parse_order_line(line)
        
        self.assertIsNotNone(order)
        self.assertIsInstance(order, ParsedOrder)
        self.assertEqual(order.order_id, "52493")
        self.assertEqual(order.sequence, 586)
        self.assertEqual(order.symbol, "CIGL")
        self.assertEqual(order.side, "B")
        self.assertEqual(order.order_type, "L")
        self.assertEqual(order.quantity, 5)
        self.assertEqual(order.filled, 0)
        self.assertEqual(order.remaining, 0)
        self.assertEqual(order.price, 2.97)
        self.assertEqual(order.route, "ARCA")
        self.assertEqual(order.status, "Executed")
        self.assertEqual(order.time, "09:53:27")
        self.assertEqual(order.account, "ZIMDASE9C64")
        self.assertEqual(order.user, "ZIMDASE9C64")
    
    def test_parse_trade_line(self):
        """Test parsing of trade lines"""
        line = "%TRADE 34277 CIGL B 10 3.8 EDUPRO 09:03:38 33998 - 0.00 0.00"
        
        trade = DASResponseParser.parse_trade_line(line)
        
        self.assertIsNotNone(trade)
        self.assertIsInstance(trade, ParsedTrade)
        self.assertEqual(trade.trade_id, "34277")
        self.assertEqual(trade.symbol, "CIGL")
        self.assertEqual(trade.side, "B")
        self.assertEqual(trade.quantity, 10)
        self.assertEqual(trade.price, 3.8)
        self.assertEqual(trade.route, "EDUPRO")
        self.assertEqual(trade.time, "09:03:38")
        self.assertEqual(trade.execution_id, "33998")
        self.assertEqual(trade.pnl, 0.0)
        self.assertEqual(trade.commission, 0.0)
    
    def test_parse_shortinfo_line(self):
        """Test parsing of short info lines"""
        line = "$SHORTINFO BBLG N 0 N 0 0 N N"
        
        info = DASResponseParser.parse_shortinfo_line(line)
        
        self.assertIsNotNone(info)
        self.assertIsInstance(info, ParsedShortInfo)
        self.assertEqual(info.symbol, "BBLG")
        self.assertEqual(info.shortable, False)
        self.assertEqual(info.shares_available, 0)
        self.assertEqual(info.uptick_rule, False)
    
    def test_parse_shortinfo_shortable(self):
        """Test parsing shortable stock"""
        line = "$SHORTINFO AAPL Y 1000000 N 0 0 N N"
        
        info = DASResponseParser.parse_shortinfo_line(line)
        
        self.assertIsNotNone(info)
        self.assertEqual(info.symbol, "AAPL")
        self.assertEqual(info.shortable, True)
        self.assertEqual(info.shares_available, 1000000)
    
    def test_parse_response_mixed(self):
        """Test parsing a mixed response with multiple message types"""
        response = """
%ORDER 52493 586 CIGL B L 5 0 0 2.97 ARCA Executed 09:53:27 0 ZIMDASE9C64 ZIMDASE9C64 Hotkey
%TRADE 34277 CIGL B 10 3.8 EDUPRO 09:03:38 33998 - 0.00 0.00
$SHORTINFO BBLG N 0 N 0 0 N N
%ORDER 41494 441 CIGL B L 5 0 0 3.97 EDUPRO Executed 09:34:26 0 ZIMDASE9C64 ZIMDASE9C64 Hotkey
Invalid line that should be ignored
ERROR: Something went wrong
"""
        
        result = DASResponseParser.parse_response(response)
        
        self.assertEqual(len(result['orders']), 2)
        self.assertEqual(len(result['trades']), 1)
        self.assertEqual(len(result['short_info']), 1)
        # La línea "Invalid..." también se detecta como error por la palabra "Invalid"
        self.assertEqual(len(result['errors']), 2)
        
        # Check first order
        self.assertEqual(result['orders'][0].order_id, "52493")
        self.assertEqual(result['orders'][0].symbol, "CIGL")
        
        # Check trade
        self.assertEqual(result['trades'][0].trade_id, "34277")
        self.assertEqual(result['trades'][0].symbol, "CIGL")
        
        # Check short info
        self.assertEqual(result['short_info'][0].symbol, "BBLG")
        self.assertEqual(result['short_info'][0].shortable, False)


class TestSmallCapsParser(unittest.TestCase):
    """Test the small caps specific parser"""
    
    def test_is_small_cap(self):
        """Test small cap symbol identification"""
        self.assertTrue(SmallCapsParser.is_small_cap("BBLG"))
        self.assertTrue(SmallCapsParser.is_small_cap("CIGL"))
        self.assertTrue(SmallCapsParser.is_small_cap("HWH"))
        self.assertTrue(SmallCapsParser.is_small_cap("bblg"))  # Case insensitive
        
        self.assertFalse(SmallCapsParser.is_small_cap("AAPL"))
        self.assertFalse(SmallCapsParser.is_small_cap("MSFT"))
        self.assertFalse(SmallCapsParser.is_small_cap("SPY"))
    
    def test_filter_small_caps(self):
        """Test filtering of small caps data"""
        response = """
%ORDER 52493 586 CIGL B L 5 0 0 2.97 ARCA Executed 09:53:27 0 ZIMDASE9C64 ZIMDASE9C64 Hotkey
%ORDER 12345 100 AAPL B L 10 0 0 150.00 NASDAQ Executed 09:30:00 0 USER USER Desktop
%ORDER 41494 441 BBLG B L 5 0 0 3.97 EDUPRO Executed 09:34:26 0 ZIMDASE9C64 ZIMDASE9C64 Hotkey
%TRADE 34277 CIGL B 10 3.8 EDUPRO 09:03:38 33998 - 0.00 0.00
%TRADE 99999 MSFT B 100 350.00 NASDAQ 10:00:00 88888 - 0.00 0.00
$SHORTINFO BBLG N 0 N 0 0 N N
$SHORTINFO AAPL Y 1000000 N 0 0 N N
"""
        
        parsed = DASResponseParser.parse_response(response)
        filtered = SmallCapsParser.filter_small_caps(parsed)
        
        # Should only have small caps
        self.assertEqual(len(filtered['orders']), 2)  # CIGL and BBLG
        self.assertEqual(len(filtered['trades']), 1)  # CIGL only
        self.assertEqual(len(filtered['short_info']), 1)  # BBLG only
        
        # Verify symbols
        for order in filtered['orders']:
            self.assertTrue(SmallCapsParser.is_small_cap(order.symbol))
        
        for trade in filtered['trades']:
            self.assertTrue(SmallCapsParser.is_small_cap(trade.symbol))
        
        for info in filtered['short_info']:
            self.assertTrue(SmallCapsParser.is_small_cap(info.symbol))
    
    def test_get_symbol_summary(self):
        """Test symbol summary generation"""
        response = """
%ORDER 52493 586 CIGL B L 5 0 0 2.97 ARCA Executed 09:53:27 0 ZIMDASE9C64 ZIMDASE9C64 Hotkey
%ORDER 52494 587 CIGL B L 10 0 0 3.00 ARCA Executed 09:54:00 0 ZIMDASE9C64 ZIMDASE9C64 Hotkey
%ORDER 52495 588 CIGL S L 5 0 5 3.10 ARCA Canceled 09:55:00 0 ZIMDASE9C64 ZIMDASE9C64 Hotkey
%ORDER 52496 589 CIGL S L 5 0 0 3.05 ARCA Executed 09:56:00 0 ZIMDASE9C64 ZIMDASE9C64 Hotkey
%TRADE 34277 CIGL B 10 3.8 EDUPRO 09:03:38 33998 - 0.00 0.00
"""
        
        parsed = SmallCapsParser.parse_response(response)
        summary = SmallCapsParser.get_symbol_summary(parsed, "CIGL")
        
        self.assertEqual(summary['symbol'], "CIGL")
        self.assertEqual(summary['total_orders'], 4)
        self.assertEqual(summary['executed_orders'], 3)
        self.assertEqual(summary['canceled_orders'], 1)
        self.assertEqual(summary['total_volume'], 20)  # 5 + 10 + 5
        self.assertAlmostEqual(summary['avg_price'], 3.01, places=2)  # (2.97 + 3.00 + 3.05) / 3
        self.assertEqual(summary['price_range']['min'], 2.97)
        self.assertEqual(summary['price_range']['max'], 3.10)
        self.assertEqual(len(summary['trades']), 1)


class TestIntegration(unittest.TestCase):
    """Integration tests for real-world scenarios"""
    
    def test_zimtra_response(self):
        """Test parsing a real Zimtra response"""
        # Actual response format from Zimtra
        response = """
#LOGIN SUCCESSED
#POS symb type qty avgcost initqty initprice Realized CreatTime Unrealized
%POS BBLG L 100 3.50 100 3.50 0.00 09:00:00 -50.00
%ORDER 81375 794 BBLG SS L 5 0 0 2.88 ARCA Executed 13:00:40 0 ZIMDASE9C64 ZIMDASE9C64 Hotkey
%ORDER 52493 586 CIGL B L 5 0 0 2.97 ARCA Executed 09:53:27 0 ZIMDASE9C64 ZIMDASE9C64 Hotkey
%TRADE 34277 CIGL B 10 3.8 EDUPRO 09:03:38 33998 - 0.00 0.00
$SHORTINFO BBLG N 0 N 0 0 N N
$SHORTINFO CIGL N 0 N 0 0 N N
"""
        
        parsed = DASResponseParser.parse_response(response)
        
        # Check parsing completeness
        self.assertEqual(len(parsed['orders']), 2)
        self.assertEqual(len(parsed['trades']), 1)
        self.assertEqual(len(parsed['positions']), 1)
        self.assertEqual(len(parsed['short_info']), 2)
        
        # Verify position parsing
        position = parsed['positions'][0]
        self.assertEqual(position.symbol, "BBLG")
        self.assertEqual(position.position_type, "L")
        self.assertEqual(position.quantity, 100)
        self.assertEqual(position.avg_cost, 3.50)
        self.assertEqual(position.unrealized_pnl, -50.00)


if __name__ == '__main__':
    unittest.main()