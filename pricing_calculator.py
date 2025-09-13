"""
Pricing Calculator for Product Adder
Ported from edit_price system with exact same formulas
"""

import math
import logging
from typing import Optional, Dict, Any

# Module-level logger
logger = logging.getLogger(__name__)

class PricingCalculator:
    """Handles price calculations using the same formulas as edit_price system"""
    
    def __init__(self):
        # Pricing formulas from edit_price system
        self.regular_formula = "math.ceil(x * 2.5) - 0.01"
        self.under5_formula = "x * 3"
    
    def calculate_price(self, formula: str, x, under5_formula: Optional[str] = None) -> float:
        """
        Calculate price using the exact same logic as edit_price system
        
        Args:
            formula: Main pricing formula (string) - limited to predefined formulas
            x: Input value (JDS lessThanCasePrice) - can be string or numeric
            under5_formula: Optional formula for prices under $5
            
        Returns:
            Calculated price
        """
        try:
            # Convert x to float, handling both string and numeric inputs
            x_float = float(x) if x is not None else 0.0
            
            # Use under5_formula if provided and x < 5
            if under5_formula and x_float < 5:
                return self._evaluate_safe_formula(under5_formula, x_float)
            else:
                return self._evaluate_safe_formula(formula, x_float)
        except Exception as e:
            logger.exception("Error calculating price")
            return 0.0
    
    def _evaluate_safe_formula(self, formula: str, x: float) -> float:
        """Safely evaluate predefined pricing formulas"""
        try:
            if formula == "math.ceil(x * 2.5) - 0.01":
                return math.ceil(x * 2.5) - 0.01
            elif formula == "x * 3":
                return x * 3
            else:
                raise ValueError(f"Unknown formula: {formula}")
        except Exception as e:
            logger.exception("Error evaluating formula")
            return 0.0
    
    def calculate_shopify_price(self, jds_price) -> float:
        """
        Calculate Shopify price from JDS lessThanCasePrice using standard formulas
        
        Args:
            jds_price: JDS lessThanCasePrice value (can be string or numeric)
            
        Returns:
            Calculated Shopify price
        """
        return self.calculate_price(self.regular_formula, jds_price, self.under5_formula)
    
    def calculate_all_tiers(self, jds_product: Dict[str, Any]) -> Dict[str, float]:
        """
        Calculate Shopify prices for all JDS pricing tiers
        
        Args:
            jds_product: JDS product data dictionary
            
        Returns:
            Dictionary with calculated prices for each tier
        """
        results = {}
        
        # Define tier mappings
        tier_mappings = {
            'less_than_case_price': 'less_than_case',
            'one_case': 'one_case',
            'five_cases': 'five_cases',
            'ten_cases': 'ten_cases',
            'twenty_cases': 'twenty_cases',
            'forty_cases': 'forty_cases'
        }
        
        # Calculate for all tiers
        for jds_key, result_key in tier_mappings.items():
            price = jds_product.get(jds_key)
            if price and self._is_valid_price(price):
                results[result_key] = self.calculate_shopify_price(price)
        
        return results
    
    def _is_valid_price(self, price) -> bool:
        """Check if a price value is valid and greater than 0"""
        try:
            price_float = float(price) if price is not None else 0.0
            return price_float > 0
        except (ValueError, TypeError):
            return False
    
    def get_recommended_price(self, jds_product: Dict[str, Any]) -> float:
        """
        Get the recommended Shopify price (using less_than_case_price as base)
        
        Args:
            jds_product: JDS product data dictionary
            
        Returns:
            Recommended Shopify price
        """
        less_than_case_price = jds_product.get('less_than_case_price')
        if not less_than_case_price:
            return 0.0
        
        return self.calculate_shopify_price(less_than_case_price)
    
    def validate_pricing_data(self, jds_product: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate JDS product pricing data and return validation results
        
        Args:
            jds_product: JDS product data dictionary
            
        Returns:
            Dictionary with validation results and calculated prices
        """
        validation = {
            'is_valid': True,
            'errors': [],
            'warnings': [],
            'calculated_prices': {},
            'recommended_price': 0.0
        }
        
        # Check if we have at least one price
        price_fields = ['less_than_case_price', 'one_case', 'five_cases', 'ten_cases', 'twenty_cases', 'forty_cases']
        has_any_price = any(jds_product.get(field) for field in price_fields)
        
        if not has_any_price:
            validation['is_valid'] = False
            validation['errors'].append("No pricing data available")
            return validation
        
        # Calculate prices for all available tiers
        validation['calculated_prices'] = self.calculate_all_tiers(jds_product)
        validation['recommended_price'] = self.get_recommended_price(jds_product)
        
        # Check for missing recommended price
        if validation['recommended_price'] <= 0:
            validation['warnings'].append("No recommended price calculated")
        
        # Check for unusually high or low prices
        if validation['recommended_price'] > 0:
            if validation['recommended_price'] > 1000:
                validation['warnings'].append("Price seems unusually high")
            elif validation['recommended_price'] < 1:
                validation['warnings'].append("Price seems unusually low")
        
        return validation

# Global pricing calculator instance
pricing_calculator = PricingCalculator()

def calculate_shopify_price(jds_price: float) -> float:
    """Convenience function for calculating Shopify price"""
    return pricing_calculator.calculate_shopify_price(jds_price)

def get_recommended_price(jds_product: Dict[str, Any]) -> float:
    """Convenience function for getting recommended price"""
    return pricing_calculator.get_recommended_price(jds_product)

def validate_pricing_data(jds_product: Dict[str, Any]) -> Dict[str, Any]:
    """Convenience function for validating pricing data"""
    return pricing_calculator.validate_pricing_data(jds_product)