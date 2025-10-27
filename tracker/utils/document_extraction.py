import os
import re
import json
from pathlib import Path
from typing import Dict, Any, Tuple, Optional
import logging

logger = logging.getLogger(__name__)

try:
    import PyPDF2
    HAS_PYPDF2 = True
except ImportError:
    HAS_PYPDF2 = False

try:
    import fitz
    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False

try:
    from PIL import Image
    import pytesseract
    HAS_OCR = True
except ImportError:
    HAS_OCR = False

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False


class DocumentExtractor:
    """Extract structured data from documents (PDF, images, scanned docs)"""
    
    # Pattern definitions for common fields
    PATTERNS = {
        'phone': r'(?:\+\d{1,3}[-.\s]?)?\d{3,4}[-.\s]?\d{3,4}[-.\s]?\d{4}',
        'email': r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
        'plate': r'[A-Z]{2,3}[-\s]?\d{2,4}[-\s]?[A-Z]{2,3}|\d{2,4}[-\s]?[A-Z]{2,4}',
        'currency_amount': r'(?:\$|SAR|AED|KWD|QAR|OMR|BHD)?\s*[\d,]+\.?\d*',
        'vehicle_make': r'\b(Toyota|Honda|Ford|BMW|Mercedes|Audi|Hyundai|KIA|Nissan|Chevrolet|Volkswagen|Mazda|Lexus|Jeep|Suzuki)\b',
    }
    
    def __init__(self):
        self.extraction_metadata = {}
    
    def extract_from_file(self, file_path: str) -> Dict[str, Any]:
        """Extract text and structured data from a file"""
        try:
            file_ext = Path(file_path).suffix.lower()
            
            if file_ext == '.pdf':
                return self._extract_from_pdf(file_path)
            elif file_ext in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff']:
                return self._extract_from_image(file_path)
            else:
                return {
                    'success': False,
                    'error': f'Unsupported file type: {file_ext}'
                }
        except Exception as e:
            logger.error(f"Error extracting from file {file_path}: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _extract_from_pdf(self, file_path: str) -> Dict[str, Any]:
        """Extract text from PDF using PyPDF2"""
        if not HAS_PYPDF2:
            return {
                'success': False,
                'error': 'PyPDF2 is not installed. Please install it with: pip install PyPDF2'
            }
        
        try:
            raw_text = ""
            with open(file_path, 'rb') as pdf_file:
                pdf_reader = PyPDF2.PdfReader(pdf_file)
                num_pages = len(pdf_reader.pages)
                
                for page_num in range(min(num_pages, 10)):  # Extract first 10 pages
                    page = pdf_reader.pages[page_num]
                    raw_text += page.extract_text() or ""
            
            return {
                'success': True,
                'raw_text': raw_text,
                'source': 'pdf',
                'pages_processed': min(num_pages, 10),
                'structured_data': self._parse_text(raw_text)
            }
        except Exception as e:
            logger.error(f"PDF extraction error: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'source': 'pdf'
            }
    
    def _extract_from_image(self, file_path: str) -> Dict[str, Any]:
        """Extract text from image using OCR"""
        if not HAS_OCR:
            return {
                'success': False,
                'error': 'pytesseract is not installed. Please install it: pip install pytesseract'
            }
        
        try:
            image = Image.open(file_path)
            
            # Image preprocessing for better OCR results
            preprocessed = self._preprocess_image(image)
            
            # Extract text using Tesseract
            raw_text = pytesseract.image_to_string(preprocessed)
            
            if not raw_text.strip():
                raw_text = pytesseract.image_to_string(image)
            
            return {
                'success': True,
                'raw_text': raw_text,
                'source': 'image_ocr',
                'image_size': image.size,
                'structured_data': self._parse_text(raw_text)
            }
        except Exception as e:
            logger.error(f"Image OCR error: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'source': 'image_ocr'
            }
    
    def _preprocess_image(self, image: 'Image') -> 'Image':
        """Preprocess image for better OCR results"""
        try:
            if not HAS_NUMPY:
                return image
            
            # Convert to grayscale if needed
            if image.mode != 'L':
                image = image.convert('L')
            
            # Resize for better OCR (if image is too small)
            if image.size[0] < 400 or image.size[1] < 400:
                new_size = (image.size[0] * 2, image.size[1] * 2)
                image = image.resize(new_size, Image.Resampling.LANCZOS)
            
            return image
        except Exception as e:
            logger.warning(f"Image preprocessing failed: {str(e)}")
            return image
    
    def _parse_text(self, raw_text: str) -> Dict[str, Any]:
        """Parse raw text to extract structured data"""
        structured = {}
        
        # Extract phone numbers
        phones = re.findall(self.PATTERNS['phone'], raw_text)
        if phones:
            structured['phone_numbers'] = [self._clean_phone(p) for p in phones]
        
        # Extract emails
        emails = re.findall(self.PATTERNS['email'], raw_text)
        if emails:
            structured['emails'] = emails
        
        # Extract vehicle plates
        plates = re.findall(self.PATTERNS['plate'], raw_text)
        if plates:
            structured['vehicle_plates'] = [self._clean_plate(p) for p in plates]
        
        # Extract vehicle makes
        makes = re.findall(self.PATTERNS['vehicle_make'], raw_text)
        if makes:
            structured['vehicle_makes'] = list(set(makes))
        
        # Extract currency amounts
        amounts = re.findall(self.PATTERNS['currency_amount'], raw_text)
        if amounts:
            structured['amounts'] = amounts
        
        # Extract common service keywords
        structured['keywords'] = self._extract_keywords(raw_text)
        
        return structured
    
    def _clean_phone(self, phone: str) -> str:
        """Normalize phone number"""
        return re.sub(r'[^0-9+]', '', phone)
    
    def _clean_plate(self, plate: str) -> str:
        """Normalize vehicle plate"""
        return re.sub(r'[^A-Z0-9]', '', plate.upper())
    
    def _extract_keywords(self, raw_text: str) -> list:
        """Extract relevant service/item keywords"""
        service_keywords = [
            'service', 'maintenance', 'repair', 'tire', 'tyre', 'oil',
            'brake', 'battery', 'alignment', 'inspection', 'diagnostic',
            'installation', 'replacement', 'change', 'wash', 'clean',
            'balance', 'rotation', 'check', 'engine', 'transmission'
        ]
        
        found_keywords = []
        text_lower = raw_text.lower()
        
        for keyword in service_keywords:
            if keyword in text_lower:
                found_keywords.append(keyword)
        
        return found_keywords
    
    def match_with_existing(self, extracted_data: Dict[str, Any], 
                           vehicle_plate: Optional[str] = None,
                           customer_phone: Optional[str] = None) -> Dict[str, Any]:
        """
        Match extracted data with existing records
        
        Returns:
            Dictionary with matched_vehicle, matched_customer, matched_order
        """
        from tracker.models import Vehicle, Customer, Order
        
        matches = {
            'vehicle': None,
            'customer': None,
            'order': None,
            'confidence': 0
        }
        
        # Try to match by vehicle plate
        if vehicle_plate:
            try:
                vehicle = Vehicle.objects.filter(plate_number__iexact=vehicle_plate).first()
                if vehicle:
                    matches['vehicle'] = {
                        'id': vehicle.id,
                        'plate': vehicle.plate_number,
                        'make': vehicle.make,
                        'model': vehicle.model,
                        'customer_id': vehicle.customer.id,
                    }
                    matches['customer'] = {
                        'id': vehicle.customer.id,
                        'name': vehicle.customer.full_name,
                        'phone': vehicle.customer.phone,
                    }
            except Exception as e:
                logger.warning(f"Vehicle matching error: {str(e)}")
        
        # Try to match by customer phone
        if customer_phone:
            try:
                customer = Customer.objects.filter(phone__icontains=customer_phone).first()
                if customer:
                    matches['customer'] = {
                        'id': customer.id,
                        'name': customer.full_name,
                        'phone': customer.phone,
                    }
            except Exception as e:
                logger.warning(f"Customer matching error: {str(e)}")
        
        # Try to match by extracted phone from document
        extracted_phones = extracted_data.get('structured_data', {}).get('phone_numbers', [])
        if extracted_phones and not customer_phone:
            for phone in extracted_phones:
                try:
                    customer = Customer.objects.filter(phone__icontains=phone).first()
                    if customer:
                        matches['customer'] = {
                            'id': customer.id,
                            'name': customer.full_name,
                            'phone': customer.phone,
                        }
                        break
                except Exception:
                    pass
        
        return matches
    
    def prepare_extraction_data(self, extracted_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare extraction data for database storage
        Handles data cleaning and validation
        """
        structured = extracted_data.get('structured_data', {})
        
        return {
            'raw_text': extracted_data.get('raw_text', '')[:10000],
            'extracted_customer_name': self._extract_name(extracted_data.get('raw_text', '')),
            'extracted_customer_phone': self._get_first(structured.get('phone_numbers', [])),
            'extracted_customer_email': self._get_first(structured.get('emails', [])),
            'extracted_vehicle_plate': self._get_first(structured.get('vehicle_plates', [])),
            'extracted_vehicle_make': self._get_first(structured.get('vehicle_makes', [])),
            'extracted_service_type': self._extract_service_type(structured.get('keywords', [])),
            'extracted_quantity': self._extract_quantity(extracted_data.get('raw_text', '')),
            'extracted_amount': self._get_first(structured.get('amounts', [])),
            'confidence_overall': self._calculate_confidence(structured),
            'extracted_data_json': structured,
        }
    
    def _extract_name(self, text: str, lines_to_check: int = 5) -> Optional[str]:
        """Extract customer name from first few lines"""
        try:
            lines = text.split('\n')[:lines_to_check]
            for line in lines:
                line = line.strip()
                if len(line) > 4 and len(line) < 100 and not any(char.isdigit() for char in line[:10]):
                    return line
        except Exception:
            pass
        return None
    
    def _extract_service_type(self, keywords: list) -> Optional[str]:
        """Extract service type from keywords"""
        if keywords:
            return ', '.join(keywords[:3])
        return None
    
    def _extract_quantity(self, text: str) -> Optional[str]:
        """Extract quantity information"""
        try:
            quantities = re.findall(r'(?:qty|quantity|q\.?t\.?y\.?|count|amount)[\s:=]+(\d+)', text, re.IGNORECASE)
            if quantities:
                return quantities[0]
        except Exception:
            pass
        return None
    
    def _calculate_confidence(self, structured_data: Dict) -> int:
        """Calculate overall confidence score (0-100)"""
        confidence = 0
        max_score = 0
        
        checks = {
            'phone_numbers': (20, lambda x: len(x) > 0),
            'emails': (20, lambda x: len(x) > 0),
            'vehicle_plates': (30, lambda x: len(x) > 0),
            'vehicle_makes': (15, lambda x: len(x) > 0),
            'amounts': (15, lambda x: len(x) > 0),
        }
        
        for field, (score, check) in checks.items():
            max_score += score
            if check(structured_data.get(field, [])):
                confidence += score
        
        return min(100, int((confidence / max_score * 100)) if max_score > 0 else 0)
    
    def _get_first(self, items: list) -> Optional[str]:
        """Get first item from list or None"""
        return items[0] if items else None


def extract_document(file_path: str) -> Dict[str, Any]:
    """Convenience function to extract data from a document"""
    extractor = DocumentExtractor()
    return extractor.extract_from_file(file_path)


def match_document_to_records(extracted_data: Dict[str, Any],
                             vehicle_plate: Optional[str] = None,
                             customer_phone: Optional[str] = None) -> Dict[str, Any]:
    """Convenience function to match extracted data to existing records"""
    extractor = DocumentExtractor()
    return extractor.match_with_existing(extracted_data, vehicle_plate, customer_phone)
