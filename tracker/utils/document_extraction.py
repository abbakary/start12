import os
import re
import json
import io
import os
import shutil
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

# Do not use pytesseract OCR: user prefers PDF/text extraction only.
# Import PIL.Image if available for image metadata, but disable OCR entirely.
try:
    from PIL import Image
    HAS_PIL = True
except Exception:
    HAS_PIL = False

# Explicitly disable OCR usage (pytesseract) to avoid accidental OCR attempts
HAS_OCR = False

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

try:
    import pdfplumber
    HAS_PDFPLUMBER = True
except Exception:
    HAS_PDFPLUMBER = False


class DocumentExtractor:
    """Extract structured data from documents (PDF, images, scanned docs)"""
    
    # Pattern definitions for common fields
    PATTERNS = {
        'phone': r'(?:\+\d{1,3}[-.\s]?)?\d{3,4}[-.\s]?\d{3,4}[-.\s]?\d{4}',
        'email': r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[A-Za-z]{2,}',
        'plate': r'[A-Z]{2,3}[-\s]?\d{2,4}[-\s]?[A-Z]{2,3}|\d{2,4}[-\s]?[A-Z]{2,4}',
        'currency_amount': r'(?:\$|SAR|AED|KWD|QAR|OMR|BHD|TSH)?\s*[\d,]+\.?\d*',
        'vehicle_make': r'\b(Toyota|Honda|Ford|BMW|Mercedes|Audi|Hyundai|KIA|Nissan|Chevrolet|Volkswagen|Mazda|Lexus|Jeep|Suzuki)\b',
        # Invoice / header fields
        'invoice_no': r'\b(?:PI|Invoice|Proforma\s*Invoice)[\s#:\-]*([A-Z0-9-]+)\b',
        'date': r'\b(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})\b',
        'tax_id': r'(?:Tax\s*ID\s*No\.?|Tax\s*ID)[:\s]*([A-Z0-9-]+)',
        'vat_reg': r'(?:VAT\s*Reg\.?.*?)[:\s]*([A-Z0-9-]+)',
        'vat_amount': r'VAT[\s:]*([\d,]+\.?\d{0,2})',
        'gross_value': r'Gross\s*Value[\s:]*([\d,]+\.?\d{0,2})',
        'net_value': r'Net\s*Value[\s:]*([\d,]+\.?\d{0,2})',
        'customer_name': r'(?:Customer\s*Name|Customer)[:\s]*([A-Z0-9 &,.\-\/]*)',
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
        """Extract text from PDF using PyMuPDF (preferred) or PyPDF2"""

        # Try PyMuPDF first (better performance and accuracy)
        if HAS_PYMUPDF:
            try:
                raw_text = ""
                doc = fitz.open(file_path)
                num_pages = doc.page_count

                for page_num in range(min(num_pages, 10)):  # Extract first 10 pages
                    page = doc[page_num]
                    raw_text += page.get_text() or ""

                doc.close()

                # Return extracted text from PDF via PyMuPDF (no OCR fallback)
                return {
                    'success': True,
                    'raw_text': raw_text,
                    'source': 'pdf_pymupdf',
                    'pages_processed': min(num_pages, 10),
                    'structured_data': self._parse_text(raw_text)
                }
            except Exception as e:
                logger.warning(f"PyMuPDF extraction failed, trying PyPDF2: {str(e)}")

        # Fallback to PyPDF2
        if not HAS_PYPDF2:
            # If PyPDF2 not available, try pdfplumber
            if not HAS_PDFPLUMBER:
                return {
                    'success': False,
                    'error': 'No suitable PDF extraction library installed. Install PyMuPDF, PyPDF2 or pdfplumber.'
                }

        try:
            raw_text = ""
            if HAS_PYPDF2:
                with open(file_path, 'rb') as pdf_file:
                    pdf_reader = PyPDF2.PdfReader(pdf_file)
                    num_pages = len(pdf_reader.pages)

                    for page_num in range(min(num_pages, 10)):  # Extract first 10 pages
                        page = pdf_reader.pages[page_num]
                        raw_text += page.extract_text() or ""

                result = {
                    'success': True,
                    'raw_text': raw_text,
                    'source': 'pdf_pypdf2',
                    'pages_processed': min(num_pages, 10),
                    'structured_data': self._parse_text(raw_text)
                }
                # If amounts not found, try pdfplumber tables
                if not result['structured_data'].get('amounts') and HAS_PDFPLUMBER:
                    try:
                        table_text, table_amounts = self._extract_with_pdfplumber(file_path)
                        if table_text:
                            raw_text += '\n' + table_text
                        if table_amounts:
                            result['structured_data']['amounts'] = table_amounts
                            result['structured_data']['table_amounts'] = table_amounts
                    except Exception as e:
                        logger.warning(f"pdfplumber fallback failed: {e}")

                return result

            # If PyPDF2 not available but pdfplumber is
            if HAS_PDFPLUMBER:
                try:
                    table_text, table_amounts = self._extract_with_pdfplumber(file_path)
                    composed_text = table_text or ''
                    return {
                        'success': True,
                        'raw_text': composed_text,
                        'source': 'pdf_pdfplumber',
                        'pages_processed': 0,
                        'structured_data': self._parse_text(composed_text)
                    }
                except Exception as e:
                    logger.error(f"pdfplumber extraction error: {e}")
                    return {'success': False, 'error': str(e)}

        except Exception as e:
            logger.error(f"PDF extraction error: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'source': 'pdf'
            }
    
    def _extract_from_image(self, file_path: str) -> Dict[str, Any]:
        """Extract text from image files.
        OCR is intentionally disabled in this deployment. This method will not
        attempt pytesseract-based OCR. Instead, it returns guidance to the
        caller to provide a PDF or text-based document for extraction.
        """
        try:
            if HAS_PIL:
                try:
                    image = Image.open(file_path)
                    image_size = image.size
                except Exception:
                    image_size = None
            else:
                image_size = None

            return {
                'success': False,
                'error': 'OCR disabled: image-to-text extraction is not available. Please provide a PDF or text-based document instead.',
                'source': 'image_no_ocr',
                'image_size': image_size
            }
        except Exception as e:
            logger.error(f"Image handling error: {str(e)}")
            return {'success': False, 'error': str(e), 'source': 'image_no_ocr'}
    
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
    
    def _extract_with_pdfplumber(self, file_path: str) -> Tuple[str, list]:
        """Extract text and table amounts using pdfplumber"""
        if not HAS_PDFPLUMBER:
            return '', []
        composed_text = ''
        amounts = []
        try:
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages[:10]:
                    try:
                        text = page.extract_text() or ''
                        composed_text += text + '\n'
                    except Exception:
                        pass
                    try:
                        tables = page.extract_tables()
                        for table in tables:
                            # Flatten table to text
                            for row in table:
                                if row:
                                    composed_text += ' | '.join([str(c or '') for c in row]) + '\n'
                                    # Try to find amounts in row
                                    for cell in row:
                                        if cell and isinstance(cell, str) and re.search(r'[\d,]+\.?\d*', cell):
                                            parsed = self._parse_amount_str(cell)
                                            if parsed is not None:
                                                amounts.append(parsed)
                    except Exception:
                        pass
        except Exception as e:
            logger.warning(f"pdfplumber extraction error: {e}")
        return composed_text, amounts

    def _parse_text(self, raw_text: str) -> Dict[str, Any]:
        """Parse raw text to extract structured data with enhanced header and items detection."""
        structured: Dict[str, Any] = {}

        # Normalize newlines and strip common repeated whitespace
        text = re.sub(r'\r\n|\r', '\n', raw_text)
        text = re.sub(r'\t', ' ', text)

        # Extract header fields using patterns
        def _first_match(key):
            try:
                m = re.search(self.PATTERNS[key], text, re.IGNORECASE | re.MULTILINE)
                return m.group(1).strip() if m else None
            except Exception:
                return None

        invoice_no = _first_match('invoice_no')
        if invoice_no:
            structured['invoice_no'] = invoice_no

        date = _first_match('date')
        if date:
            structured['date'] = date

        tax_id = _first_match('tax_id') or _first_match('vat_reg')
        if tax_id:
            structured['tax_id'] = tax_id

        vat_amount = _first_match('vat_amount')
        if vat_amount:
            structured['vat_amount'] = self._parse_amount_str(vat_amount)

        gross_value = _first_match('gross_value')
        if gross_value:
            structured['gross_value'] = self._parse_amount_str(gross_value)

        net_value = _first_match('net_value')
        if net_value:
            structured['net_value'] = self._parse_amount_str(net_value)

        customer = _first_match('customer_name')
        if customer:
            structured['customer_name'] = customer

        # Extract emails, phones, plates and amounts (general)
        phones = re.findall(self.PATTERNS['phone'], text)
        if phones:
            structured['phone_numbers'] = [self._clean_phone(p) for p in phones]

        emails = re.findall(self.PATTERNS['email'], text)
        if emails:
            structured['emails'] = list(dict.fromkeys(emails))

        plates = re.findall(self.PATTERNS['plate'], text)
        if plates:
            structured['vehicle_plates'] = [self._clean_plate(p) for p in plates]

        makes = re.findall(self.PATTERNS['vehicle_make'], text)
        if makes:
            structured['vehicle_makes'] = list(set(makes))

        # Extract items and table-like structures
        items = self._extract_items(text)
        if items:
            structured['items'] = items

        # Extract general currency amounts
        amounts = re.findall(self.PATTERNS['currency_amount'], text)
        if amounts:
            parsed_amounts = []
            for a in amounts:
                parsed = self._parse_amount_str(a)
                if parsed is not None:
                    parsed_amounts.append(parsed)
            structured['amounts'] = parsed_amounts

        # Extract common service keywords and a likely service description
        structured['keywords'] = self._extract_keywords(text)
        # Heuristic: service_description = first line containing any service keyword
        for ln in text.splitlines():
            for kw in structured['keywords']:
                if kw in ln.lower():
                    structured['service_description'] = ln.strip()
                    break
            if structured.get('service_description'):
                break

        return structured

    def _extract_items(self, text: str) -> list:
        """Heuristic extraction of line items from invoice-like text.
        Returns a list of dicts: {description, qty, rate, value, code}
        """
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        items = []
        amount_re = re.compile(r'([\d,]+\.?\d{0,2})')

        for idx, line in enumerate(lines):
            # Skip header lines
            if re.search(r'^(proforma|invoice|customer|address|tel|fax|email|tax|vat|page)\b', line, re.I):
                continue

            # If line has both letters and digits and looks like item description/code
            if re.search(r'[A-Za-z]', line) and re.search(r'\d', line):
                # Look for amounts on the same line
                amounts = amount_re.findall(line.replace(',', ''))
                qty = None
                rate = None
                value = None
                code = None

                # Attempt to find an item code pattern like A01218 or numeric codes
                code_match = re.search(r'\b([A-Z0-9]{3,}[\/-]?[A-Z0-9]*)\b', line)
                if code_match:
                    code = code_match.group(1)

                # If amounts found on the same line, guess last is value
                if amounts:
                    nums = [self._parse_amount_str(a) for a in amounts if self._parse_amount_str(a) is not None]
                    if nums:
                        value = nums[-1]
                        if len(nums) >= 2:
                            rate = nums[-2]
                        if len(nums) >= 3:
                            qty = nums[-3]

                # Otherwise look ahead in next 2 lines for numeric columns
                if not value:
                    look_ahead = ' '.join(lines[idx:idx+3])
                    nums = amount_re.findall(look_ahead.replace(',', ''))
                    nums = [self._parse_amount_str(n) for n in nums if self._parse_amount_str(n) is not None]
                    if nums:
                        value = nums[-1]
                        if len(nums) >= 2:
                            rate = nums[-2]
                        if len(nums) >= 3:
                            qty = nums[-3]

                items.append({
                    'description': line,
                    'code': code,
                    'qty': qty,
                    'rate': rate,
                    'value': value,
                })

        # Filter out false positives (lines with no numeric value)
        filtered = [it for it in items if it.get('value') is not None or it.get('qty') is not None]
        return filtered
    
    def _clean_phone(self, phone: str) -> str:
        """Normalize phone number"""
        return re.sub(r'[^0-9+]', '', phone)
    
    def _clean_plate(self, plate: str) -> str:
        """Normalize vehicle plate to uppercase alphanumeric (keep spaces optional)"""
        try:
            cleaned = re.sub(r'[^A-Z0-9]', '', plate.upper())
            # Optionally insert a space between letters and digits for readability (e.g., ABC123 -> ABC 123)
            m = re.match(r'^([A-Z]+)(\d+)([A-Z]*)$', cleaned)
            if m:
                parts = [m.group(1), m.group(2), m.group(3)]
                return ' '.join([p for p in parts if p])
            return cleaned
        except Exception:
            return plate.upper().strip()

    def _normalize_name(self, name: str) -> str:
        """Normalize person/company names: title case unless it's clearly an acronym"""
        if not name:
            return ''
        n = name.strip()
        # If more than 60% of letters are uppercase, assume all-caps and title-case it
        letters = re.findall(r'[A-Za-z]', n)
        if letters:
            upper_count = sum(1 for c in letters if c.isupper())
            if upper_count / len(letters) > 0.6:
                return n.title()
        # Otherwise, just title-case common name formats
        return n.title()

    def _parse_amount_str(self, s: str) -> Optional[str]:
        """Parse a string containing an amount and return normalized numeric string"""
        try:
            # Remove currency symbols and words
            s_clean = re.sub(r'[A-Za-z\$€£¥₹,\s]', '', s)
            s_clean = s_clean.replace('(', '-').replace(')', '')
            # Keep only digits and dot and dash
            m = re.search(r'-?\d+\.?\d*', s_clean)
            if m:
                return m.group(0)
        except Exception:
            pass
        return None

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
        
        raw_name = self._extract_name(extracted_data.get('raw_text', ''))
        extracted_amount_raw = self._get_first(structured.get('amounts', [])) or self._get_first(structured.get('table_amounts', []))
        parsed_amount = None
        if extracted_amount_raw:
            parsed_amount = self._parse_amount_str(str(extracted_amount_raw))

        return {
            'raw_text': extracted_data.get('raw_text', '')[:10000],
            'extracted_customer_name': self._normalize_name(raw_name) if raw_name else None,
            'extracted_customer_phone': self._clean_phone(self._get_first(structured.get('phone_numbers', [])) or ''),
            'extracted_customer_email': (self._get_first(structured.get('emails', [])) or '').lower() or None,
            'extracted_vehicle_plate': self._clean_plate(self._get_first(structured.get('vehicle_plates', [])) or ''),
            'extracted_vehicle_make': (self._get_first(structured.get('vehicle_makes', [])) or '').title() or None,
            'extracted_service_type': self._extract_service_type(structured.get('keywords', [])),
            'extracted_quantity': self._extract_quantity(extracted_data.get('raw_text', '')),
            'extracted_amount': parsed_amount,
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
                    return self._normalize_name(line)
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
                             customer_phone: Optional[str] = None,
                             auto_link: bool = True) -> Dict[str, Any]:
    """
    Convenience function to match extracted data to existing records

    Args:
        extracted_data: Extracted data from document
        vehicle_plate: Vehicle plate from upload form or extracted
        customer_phone: Customer phone from upload form or extracted
        auto_link: Whether to automatically link records (default True)

    Returns:
        Dictionary with matched records and linking suggestions
    """
    from tracker.models import Vehicle, Customer, Order

    matches = {
        'vehicle': None,
        'customer': None,
        'orders': [],
        'confidence': 0,
        'auto_link_suggested': False
    }

    if not auto_link:
        return matches

    extractor = DocumentExtractor()
    base_matches = extractor.match_with_existing(extracted_data, vehicle_plate, customer_phone)

    # Enhance matches with additional linking suggestions
    try:
        # If we found a vehicle, get recent orders
        if base_matches.get('vehicle'):
            vehicle_id = base_matches['vehicle'].get('id')
            if vehicle_id:
                orders = Order.objects.filter(
                    vehicle_id=vehicle_id
                ).order_by('-created_at')[:3]

                matches['orders'] = [
                    {
                        'id': order.id,
                        'order_number': order.order_number,
                        'status': order.status,
                        'created_at': order.created_at.isoformat(),
                    }
                    for order in orders
                ]

        # Suggest auto-linking if confidence is high
        extracted_phone = extracted_data.get('structured_data', {}).get('phone_numbers', [None])[0]
        extracted_plate = extracted_data.get('structured_data', {}).get('vehicle_plates', [None])[0]

        if (extracted_phone and customer_phone and extracted_phone in customer_phone) or \
           (extracted_plate and vehicle_plate and extracted_plate.upper() in vehicle_plate.upper()):
            matches['auto_link_suggested'] = True

        matches.update(base_matches)
    except Exception as e:
        logger.warning(f"Error enhancing matches: {str(e)}")
        matches.update(base_matches)

    return matches
