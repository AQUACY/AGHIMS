"""
ASTM E1394-97 Parser for Sysmex XN-330 Analyzer
Parses ASTM messages received from the analyzer and extracts lab results
"""
import re
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)

# ASTM Frame delimiters
STX = '\x02'  # Start of text
ETX = '\x03'  # End of text
ENQ = '\x05'  # Enquiry
ACK = '\x06'  # Acknowledge
NAK = '\x15'  # Negative acknowledge
EOT = '\x04'  # End of transmission
CR = '\r'     # Carriage return
LF = '\n'     # Line feed

# ASTM Record types
RECORD_TYPE_PATIENT = 'P'
RECORD_TYPE_ORDER = 'O'
RECORD_TYPE_RESULT = 'R'
RECORD_TYPE_COMMENT = 'C'
RECORD_TYPE_TERMINATOR = 'L'


class ASTMParser:
    """Parser for ASTM E1394-97 protocol messages"""
    
    def __init__(self):
        self.buffer = ""
        self.current_message = []
        
    def parse_frame(self, data: bytes) -> List[Dict[str, Any]]:
        """
        Parse ASTM frame data and return list of parsed records
        
        Args:
            data: Raw bytes received from analyzer
            
        Returns:
            List of parsed record dictionaries
        """
        # Convert bytes to string
        try:
            text = data.decode('ascii', errors='ignore')
        except Exception as e:
            logger.error(f"Error decoding ASTM data: {e}")
            return []
        
        # Add to buffer
        self.buffer += text
        
        records = []
        
        # Process complete frames (STX ... ETX)
        while STX in self.buffer and ETX in self.buffer:
            start_idx = self.buffer.find(STX)
            end_idx = self.buffer.find(ETX, start_idx)
            
            if end_idx == -1:
                break
                
            # Extract frame
            frame = self.buffer[start_idx + 1:end_idx]  # Exclude STX and ETX
            self.buffer = self.buffer[end_idx + 1:]  # Remove processed frame
            
            # Parse frame into records (records are separated by CR or CRLF)
            frame_records = self._parse_frame_records(frame)
            records.extend(frame_records)
        
        return records
    
    def _parse_frame_records(self, frame: str) -> List[Dict[str, Any]]:
        """Parse a frame into individual records"""
        records = []
        
        # Split by CR or CRLF
        record_strings = re.split(r'\r\n|\r|\n', frame)
        
        for record_str in record_strings:
            record_str = record_str.strip()
            if not record_str:
                continue
                
            # Parse record (fields are separated by |)
            record = self._parse_record(record_str)
            if record:
                records.append(record)
        
        return records
    
    def _parse_record(self, record_str: str) -> Optional[Dict[str, Any]]:
        """Parse a single ASTM record"""
        if not record_str or len(record_str) < 1:
            return None
        
        # Split by pipe delimiter
        fields = record_str.split('|')
        
        if len(fields) < 1:
            return None
        
        record_type = fields[0]
        
        record = {
            'type': record_type,
            'raw': record_str,
            'fields': fields
        }
        
        # Parse based on record type
        if record_type == RECORD_TYPE_PATIENT:
            record.update(self._parse_patient_record(fields))
        elif record_type == RECORD_TYPE_ORDER:
            record.update(self._parse_order_record(fields))
        elif record_type == RECORD_TYPE_RESULT:
            record.update(self._parse_result_record(fields))
        elif record_type == RECORD_TYPE_COMMENT:
            record.update(self._parse_comment_record(fields))
        elif record_type == RECORD_TYPE_TERMINATOR:
            record.update(self._parse_terminator_record(fields))
        
        return record
    
    def _parse_patient_record(self, fields: List[str]) -> Dict[str, Any]:
        """Parse Patient (P) record"""
        # P|1|PatientID|LastName^FirstName^MiddleName|Sex|DOB|Race|Address|...
        return {
            'patient_id': fields[2] if len(fields) > 2 else '',
            'patient_name': fields[3] if len(fields) > 3 else '',
            'sex': fields[4] if len(fields) > 4 else '',
            'dob': fields[5] if len(fields) > 5 else '',
        }
    
    def _parse_order_record(self, fields: List[str]) -> Dict[str, Any]:
        """Parse Order (O) record"""
        # O|1|SpecimenID|InstrumentSpecimenID|TestID|Priority|RequestedDateTime|...
        # Sysmex format: O|1||^^                   866^M|^^^^WBC\^^^^RBC\...|...
        # Sample ID is often in field 3 (InstrumentSpecimenID) or field 2 (SpecimenID)
        specimen_id = fields[2] if len(fields) > 2 else ''
        instrument_specimen_id = fields[3] if len(fields) > 3 else ''
        
        # Extract sample ID from instrument_specimen_id if it contains the ID
        # Format might be: ^^                   866^M| or just 866
        sample_id = ''
        if instrument_specimen_id:
            # Try to extract numeric ID from the field
            import re
            # Look for pattern like "866" in "^^                   866^M|"
            match = re.search(r'(\d+)', instrument_specimen_id)
            if match:
                sample_id = match.group(1)
        elif specimen_id:
            # Try specimen_id if instrument_specimen_id doesn't have it
            import re
            match = re.search(r'(\d+)', specimen_id)
            if match:
                sample_id = match.group(1)
        
        return {
            'specimen_id': specimen_id,
            'instrument_specimen_id': instrument_specimen_id,
            'sample_id': sample_id,  # Extracted numeric sample ID
            'test_id': fields[4] if len(fields) > 4 else '',
            'priority': fields[5] if len(fields) > 5 else '',
            'requested_datetime': fields[6] if len(fields) > 6 else '',
        }
    
    def _parse_result_record(self, fields: List[str]) -> Dict[str, Any]:
        """Parse Result (R) record"""
        # R|1|TestID|Value|Units|ReferenceRange|AbnormalFlags|Status|...
        return {
            'test_id': fields[2] if len(fields) > 2 else '',
            'value': fields[3] if len(fields) > 3 else '',
            'units': fields[4] if len(fields) > 4 else '',
            'reference_range': fields[5] if len(fields) > 5 else '',
            'abnormal_flags': fields[6] if len(fields) > 6 else '',
            'status': fields[7] if len(fields) > 7 else '',
        }
    
    def _parse_comment_record(self, fields: List[str]) -> Dict[str, Any]:
        """Parse Comment (C) record"""
        # C|1|CommentType|CommentText|...
        return {
            'comment_type': fields[2] if len(fields) > 2 else '',
            'comment_text': fields[3] if len(fields) > 3 else '',
        }
    
    def _parse_terminator_record(self, fields: List[str]) -> Dict[str, Any]:
        """Parse Terminator (L) record"""
        # L|1|TerminatorCode|...
        return {
            'terminator_code': fields[2] if len(fields) > 2 else '',
        }
    
    def extract_results(self, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Extract structured results from parsed ASTM records
        
        Returns:
            Dictionary with:
            - sample_id: Sample ID from order record
            - patient_id: Patient ID
            - results: Dictionary of test_id -> value mappings
            - units: Dictionary of test_id -> units mappings
            - flags: Dictionary of test_id -> abnormal flags
        """
        extracted = {
            'sample_id': '',
            'patient_id': '',
            'specimen_id': '',
            'results': {},
            'units': {},
            'flags': {},
            'comments': []
        }
        
        for record in records:
            if record['type'] == RECORD_TYPE_PATIENT:
                extracted['patient_id'] = record.get('patient_id', '')
            elif record['type'] == RECORD_TYPE_ORDER:
                # Sample ID is typically in specimen_id or instrument_specimen_id
                extracted['specimen_id'] = record.get('specimen_id', '')
                extracted['instrument_specimen_id'] = record.get('instrument_specimen_id', '')
                # Use extracted sample_id from parser if available, otherwise fallback
                extracted['sample_id'] = record.get('sample_id', '') or record.get('instrument_specimen_id', '') or record.get('specimen_id', '')
            elif record['type'] == RECORD_TYPE_RESULT:
                test_id = record.get('test_id', '')
                if test_id:
                    extracted['results'][test_id] = record.get('value', '')
                    extracted['units'][test_id] = record.get('units', '')
                    extracted['flags'][test_id] = record.get('abnormal_flags', '')
            elif record['type'] == RECORD_TYPE_COMMENT:
                extracted['comments'].append(record.get('comment_text', ''))
        
        return extracted

