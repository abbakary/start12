"""
Invoice extraction utilities using template-based pattern matching.
Provides functions to extract customer, vehicle, service, and financial data from invoice text.
"""

import re
import logging
from typing import Dict, List, Optional, Tuple
from decimal import Decimal

logger = logging.getLogger(__name__)


class InvoiceExtractor:
    """Template-based invoice field extractor using regex patterns."""
    
    def __init__(self):
        """Initialize the extractor (patterns loaded from database on first use)."""
        self.patterns = {}
        self.service_templates = {}
        self._patterns_loaded = False
    
    def _load_patterns_from_db(self):
        """Load extraction patterns from database."""
        if self._patterns_loaded:
            return
        
        try:
            from .models import InvoicePatternMatcher, ServiceTemplate
            
            patterns = InvoicePatternMatcher.objects.filter(is_active=True).order_by('priority')
            for pattern in patterns:
                field_type = pattern.field_type
                if field_type not in self.patterns:
                    self.patterns[field_type] = []
                self.patterns[field_type].append({
                    'name': pattern.name,
                    'regex': pattern.regex_pattern,
                    'group': pattern.extract_group,
                    'priority': pattern.priority,
                })
            
            # Load service templates for keyword matching
            templates = ServiceTemplate.objects.filter(is_active=True)
            for template in templates:
                keywords = [k.strip().lower() for k in (template.keywords or '').split(',') if k.strip()]
                self.service_templates[template.name] = {
                    'keywords': keywords,
                    'minutes': template.estimated_minutes,
                    'service_type': template.service_type,
                }
            
            self._patterns_loaded = True
        except Exception as e:
            logger.error(f"Error loading patterns from database: {str(e)}")
            self._patterns_loaded = True  # Prevent repeated attempts
    
    def _default_patterns(self) -> Dict:
        """Return default patterns if database patterns are unavailable."""
        return {
            'plate_number': [
                {
                    'name': 'Plate in reference field',
                    'regex': r'(?:REFERENCE|REF|Plate|License)[\s:]*([A-Z]{3}\s?[A-Z]?\s?\d+\s?[A-Z]{3})',
                    'group': 1,
                    'priority': 10,
                },
                {
                    'name': 'Standard plate format',
                    'regex': r'(?<![A-Z0-9])([A-Z]{2,3}\s?[A-Z]?\s?(?:\d+\s)?[A-Z]{2,3})(?![A-Z0-9])',
                    'group': 1,
                    'priority': 20,
                },
            ],
            'amount': [
                {
                    'name': 'Amount with currency symbol',
                    'regex': r'(?:Total|TOTAL|Amount|AMOUNT|Due)[\s:]*([A-Z])?[\s]*([\d,]+\.?\d{0,2})',
                    'group': 2,
                    'priority': 10,
                },
                {
                    'name': 'Numeric amount',
                    'regex': r'([\d,]+\.?\d{0,2})',
                    'group': 1,
                    'priority': 100,
                },
            ],
            'customer_phone': [
                {
                    'name': 'Tanzania phone format',
                    'regex': r'(?:Phone|Tel|Mobile|Contact)[\s:]*(\+?255\s?\d{3}\s?\d{3}\s?\d{3}|0[67]\d{2}\s?\d{3}\s?\d{3})',
                    'group': 1,
                    'priority': 10,
                },
                {
                    'name': 'General phone format',
                    'regex': r'(\+?\d{1,3}\s?\d{2,4}\s?\d{3,4})',
                    'group': 1,
                    'priority': 20,
                },
            ],
            'customer_name': [
                {
                    'name': 'Name after customer label',
                    'regex': r'(?:CUSTOMER|Customer|Name)[\s:]*([A-Za-z\s]+?)(?:\n|$|Phone|Tel|Address)',
                    'group': 1,
                    'priority': 10,
                },
            ],
            'customer_email': [
                {
                    'name': 'Email pattern',
                    'regex': r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
                    'group': 1,
                    'priority': 10,
                },
            ],
            'service_description': [
                {
                    'name': 'Service/description field',
                    'regex': r'(?:SERVICE|Service|Description|Item|ITEM)[\s:]*([A-Za-z0-9\s,.-]+?)(?:\n|Qty|Quantity|$)',
                    'group': 1,
                    'priority': 10,
                },
            ],
            'quantity': [
                {
                    'name': 'Quantity field',
                    'regex': r'(?:QTY|Quantity|Qty)[\s:]*(\d+)',
                    'group': 1,
                    'priority': 10,
                },
            ],
            'reference': [
                {
                    'name': 'Invoice/Reference number',
                    'regex': r'(?:REF|Reference|Invoice|INV)[\s#:]*([A-Z0-9-]+)',
                    'group': 1,
                    'priority': 10,
                },
            ],
        }
    
    def extract_field(self, text: str, field_type: str) -> Optional[str]:
        """
        Extract a specific field from invoice text using regex patterns.
        
        Args:
            text: Raw invoice text
            field_type: Type of field to extract (e.g., 'plate_number', 'amount')
        
        Returns:
            Extracted value or None
        """
        self._load_patterns_from_db()
        
        patterns = self.patterns.get(field_type)
        if not patterns:
            patterns = self._default_patterns().get(field_type, [])
        
        for pattern_info in patterns:
            try:
                match = re.search(pattern_info['regex'], text, re.IGNORECASE | re.MULTILINE)
                if match:
                    value = match.group(pattern_info.get('group', 1))
                    if value:
                        return value.strip()
            except Exception as e:
                logger.warning(f"Error matching pattern {pattern_info['name']}: {str(e)}")
        
        return None
    
    def extract_amount(self, text: str) -> Optional[Decimal]:
        """Extract and parse monetary amount from text."""
        amount_str = self.extract_field(text, 'amount')
        if not amount_str:
            return None
        
        try:
            # Remove non-numeric characters except decimal point
            amount_str = re.sub(r'[^\d.]', '', amount_str)
            return Decimal(amount_str)
        except Exception as e:
            logger.warning(f"Error parsing amount '{amount_str}': {str(e)}")
            return None
    
    def match_service_template(self, description: str) -> Optional[Tuple[str, int]]:
        """
        Match a service description to a template and return estimated minutes.
        
        Args:
            description: Service description text
        
        Returns:
            Tuple of (service_name, estimated_minutes) or None
        """
        if not description:
            return None
        
        description_lower = description.lower()
        
        # Find best matching template based on keywords
        best_match = None
        best_match_count = 0
        
        for service_name, template in self.service_templates.items():
            match_count = sum(1 for kw in template['keywords'] if kw in description_lower)
            if match_count > best_match_count:
                best_match = (service_name, template['minutes'])
                best_match_count = match_count
        
        return best_match
    
    def extract_all(self, text: str) -> Dict:
        """
        Extract all available fields from invoice text.
        
        Args:
            text: Raw invoice text
        
        Returns:
            Dictionary with extracted fields
        """
        self._load_patterns_from_db()
        
        extracted = {
            'plate_number': self.extract_field(text, 'plate_number'),
            'customer_name': self.extract_field(text, 'customer_name'),
            'customer_phone': self.extract_field(text, 'customer_phone'),
            'customer_email': self.extract_field(text, 'customer_email'),
            'service_description': self.extract_field(text, 'service_description'),
            'item_name': self.extract_field(text, 'service_description'),
            'quantity': self.extract_field(text, 'quantity'),
            'amount': str(self.extract_amount(text)) if self.extract_amount(text) else None,
            'reference': self.extract_field(text, 'reference'),
        }
        
        # Try to match service template if we have a service description
        if extracted['service_description']:
            match = self.match_service_template(extracted['service_description'])
            if match:
                extracted['matched_service'] = match[0]
                extracted['estimated_minutes'] = match[1]
        
        # Remove None values
        return {k: v for k, v in extracted.items() if v is not None}


def extract_text_from_image(image_path: str) -> str:
    """
    Image text extraction is disabled (OCR not used). This function will
    return an empty string and log a warning. If you need text extraction
    from images, enable an OCR solution or provide PDF/text documents.
    """
    logger.warning('OCR disabled: extract_text_from_image called but OCR is not enabled')
    return ""


def process_invoice_extraction(document_scan) -> Dict:
    """
    Process a document scan and extract all available data.
    
    Args:
        document_scan: DocumentScan instance with uploaded file
    
    Returns:
        Dictionary of extracted data
    """
    extractor = InvoiceExtractor()
    text = ""
    
    try:
        # Try to extract text from file
        if document_scan.file.name.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
            # OCR disabled — instruct user to upload a PDF or text-based document
            logger.warning('Image upload detected but OCR is disabled — extraction aborted')
            return {'error': 'Image extraction disabled. Please upload a PDF or text-based document.'}
        else:
            # If it's a PDF, attempt binary-based extraction
            try:
                # Prefer using PDF extraction utilities instead of raw decode
                from tracker.utils.document_extraction import DocumentExtractor
                dext = DocumentExtractor()
                # Save uploaded file to a temporary path and extract
                tmp_path = None
                try:
                    tmp_path = document_scan.file.path
                except Exception:
                    # Fallback: write content to a temp file
                    import tempfile
                    tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.' + document_scan.file.name.split('.')[-1])
                    tmp.write(document_scan.file.read())
                    tmp.close()
                    tmp_path = tmp.name

                result = dext.extract_from_file(tmp_path)
                if result.get('success'):
                    text = result.get('raw_text', '')
                else:
                    logger.warning(f"Document extraction failed: {result.get('error')}")
                    return {'error': result.get('error', 'Extraction failed')}
            except Exception as e:
                logger.warning(f"Could not extract file using PDF extractor: {e}")
                try:
                    text = document_scan.file.read().decode('utf-8')
                except Exception:
                    logger.warning(f"Could not read file as text: {document_scan.file.name}")
                    return {'error': 'Could not extract text from document'}
        
        # If we used the DocumentExtractor earlier (result variable), merge its structured output
        merged_result = None
        try:
            if 'result' in locals() and isinstance(result, dict) and result.get('success'):
                doc_struct = result.get('structured_data', {}) or {}
                # Use InvoiceExtractor to get field-level parsing and service template matching
                invoice_fields = extractor.extract_all(text)

                # Merge doc_struct into invoice_fields, preferring invoice_fields but filling gaps
                merged = dict(invoice_fields)
                for k, v in doc_struct.items():
                    if not merged.get(k) and v:
                        merged[k] = v
                    elif isinstance(v, list) and isinstance(merged.get(k), list):
                        # combine unique
                        merged[k] = list(dict.fromkeys(merged.get(k) + v))

                merged['raw_text'] = text[:5000]

                # Attempt to match service template if not already matched
                service_desc = merged.get('service_description') or merged.get('item_name') or merged.get('description')
                if service_desc:
                    match = extractor.match_service_template(service_desc)
                    if match:
                        merged['matched_service'] = match[0]
                        merged['estimated_minutes'] = match[1]

                merged_result = merged
            else:
                # No DocumentExtractor result; fall back to InvoiceExtractor output
                extracted_data = extractor.extract_all(text)
                extracted_data['raw_text'] = text[:5000]
                merged_result = extracted_data
        except Exception as e:
            logger.warning(f"Error merging extraction results: {e}")
            extracted_data = extractor.extract_all(text)
            extracted_data['raw_text'] = text[:5000]
            merged_result = extracted_data

        return merged_result
    
    except Exception as e:
        logger.error(f"Error processing invoice extraction: {str(e)}")
        return {'error': str(e)}


# Global extractor instance
_extractor_instance = None

def get_extractor() -> InvoiceExtractor:
    """Get or create global extractor instance."""
    global _extractor_instance
    if _extractor_instance is None:
        _extractor_instance = InvoiceExtractor()
    return _extractor_instance
