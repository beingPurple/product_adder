"""
Pricing Calculator for Product Adder
Ported from edit_price system with exact same formulas
"""

import math
from typing import Optional, Dict, Any

class PricingCalculator:
    """Handles price calculations using the same formulas as edit_price system"""
    
    def __init__(self):
        # Pricing formulas from edit_price system
        self.regular_formula = "math.ceil(x * 2.5) - 0.01"
        self.under5_formula = "x * 3"
    
    def calculate_price(self, formula: str, x: float, under5_formula: Optional[str] = None) -> float:
        """
        Calculate price using the exact same logic as edit_price system
        
        Args:
            formula: Main pricing formula (string)
            x: Input value (JDS lessThanCasePrice)
            under5_formula: Optional formula for prices under $5
            
        Returns:
            Calculated price
        """
        try:
            # Use under5_formula if provided and x < 5
            if under5_formula and float(x) < 5:
                return eval(under5_formula, {"x": float(x), "math": math, "__builtins__": {}})
            else:
                return eval(formula, {"x": float(x), "math": math, "__builtins__": {}})
        except Exception as e:
            print(f"Error calculating price: {e}")
            return 0.0
    
    def calculate_shopify_price(self, jds_price: float) -> float:
        """
        Calculate Shopify price from JDS lessThanCasePrice using standard formulas
        
        Args:
            jds_price: JDS lessThanCasePrice value
            
        Returns:
            Calculated Shopify price
        """
        if not jds_price or jds_price <= 0:
            return 0.0
        
        return self.calculate_price(
            formula=self.regular_formula,
            x=jds_price,
            under5_formula=self.under5_formula
        )
    
    def calculate_all_tiers(self, jds_product: Dict[str, Any]) -> Dict[str, float]:
        """
        Calculate Shopify prices for all JDS pricing tiers
        
        Args:
            jds_product: JDS product data dictionary
            
        Returns:
            Dictionary with calculated prices for each tier
        """
        results = {}
        
        # Calculate for less_than_case_price (main price)
        if jds_product.get('less_than_case_price'):
            results['less_than_case'] = self.calculate_shopify_price(
                jds_product['less_than_case_price']
            )
        
        # Calculate for one_case
        if jds_product.get('one_case'):
            results['one_case'] = self.calculate_shopify_price(
                jds_product['one_case']
            )
        
        # Calculate for five_cases
        if jds_product.get('five_cases'):
            results['five_cases'] = self.calculate_shopify_price(
                jds_product['five_cases']
            )
        
        # Calculate for ten_cases
        if jds_product.get('ten_cases'):
            results['ten_cases'] = self.calculate_shopify_price(
                jds_product['ten_cases']
            )
        
        # Calculate for twenty_cases
        if jds_product.get('twenty_cases'):
            results['twenty_cases'] = self.calculate_shopify_price(
                jds_product['twenty_cases']
            )
        
        # Calculate for forty_cases
        if jds_product.get('forty_cases'):
            results['forty_cases'] = self.calculate_shopify_price(
                jds_product['forty_cases']
            )
        
        return results
    
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

