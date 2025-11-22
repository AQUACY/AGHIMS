"""
Mapper service to convert ASTM analyzer results to lab result template format
Maps Sysmex XN-330 test codes to template field names
"""
import logging
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Mapping of Sysmex XN-330 test codes to template field names
# The analyzer sends codes like: ^^^^WBC^1, ^^^^RBC^1, etc.
SYSMEX_TO_TEMPLATE_MAP = {
    # Basic Parameters (with ^^^^ prefix and ^1 suffix)
    '^^^^WBC^1': 'WBC',  # White Blood Cell Count
    '^^^^RBC^1': 'RBC',  # Red Blood Cell Count
    '^^^^HGB^1': 'HGB',  # Hemoglobin
    '^^^^HCT^1': 'HCT',  # Hematocrit
    '^^^^MCV^1': 'MCV',  # Mean Corpuscular Volume
    '^^^^MCH^1': 'MCH',  # Mean Corpuscular Hemoglobin
    '^^^^MCHC^1': 'MCHC',  # Mean Corpuscular Hemoglobin Concentration
    '^^^^PLT^1': 'PLT',  # Platelet Count
    
    # Differential Count (Absolute)
    '^^^^NEUT#^1': 'NEUT#',  # Neutrophils (Absolute)
    '^^^^LYMPH#^1': 'LYMPH#',  # Lymphocytes (Absolute)
    '^^^^MONO#^1': 'MONO#',  # Monocytes (Absolute)
    '^^^^EO#^1': 'EO#',  # Eosinophils (Absolute)
    '^^^^BASO#^1': 'BASO#',  # Basophils (Absolute)
    
    # Differential Count (%)
    '^^^^NEUT%^1': 'NEUT%',  # Neutrophils (%)
    '^^^^LYMPH%^1': 'LYMPH%',  # Lymphocytes (%)
    '^^^^MONO%^1': 'MONO%',  # Monocytes (%)
    '^^^^EO%^1': 'EO%',  # Eosinophils (%)
    '^^^^BASO%^1': 'BASO%',  # Basophils (%)
    
    # Additional Parameters
    '^^^^IG#^1': 'IG#',  # Immature Granulocytes (Absolute)
    '^^^^IG%^1': 'IG%',  # Immature Granulocytes (%)
    
    # Fallback mappings (without prefix/suffix, for compatibility)
    'WBC': 'WBC',
    'RBC': 'RBC',
    'HGB': 'HGB',
    'HCT': 'HCT',
    'MCV': 'MCV',
    'MCH': 'MCH',
    'MCHC': 'MCHC',
    'PLT': 'PLT',
    'NEUT#': 'NEUT#',
    'LYMPH#': 'LYMPH#',
    'MONO#': 'MONO#',
    'EO#': 'EO#',
    'BASO#': 'BASO#',
    'NEUT%': 'NEUT%',
    'LYMPH%': 'LYMPH%',
    'MONO%': 'MONO%',
    'EO%': 'EO%',
    'BASO%': 'BASO%',
    'IG#': 'IG#',
    'IG%': 'IG%',
}


class AnalyzerMapper:
    """Maps analyzer results to lab result template format"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def map_astm_to_template(
        self,
        astm_data: Dict[str, Any],
        template_structure: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Map ASTM extracted data to template format
        
        Args:
            astm_data: Extracted data from ASTM parser
            template_structure: Template structure from LabResultTemplate
            
        Returns:
            Dictionary in template_data format:
            {
                "field_values": {"WBC": 4.79, ...},
                "messages": {"WBC IP Message": "...", ...},
                "validated_by": "",
                "sample_no": "251100001"
            }
        """
        field_values = {}
        messages = {}
        
        # Get field names from template
        template_fields = template_structure.get('fields', [])
        field_names = {field['name']: field for field in template_fields}
        
        # Map ASTM results to template fields
        for test_id, value in astm_data.get('results', {}).items():
            # Try direct mapping first
            template_field_name = SYSMEX_TO_TEMPLATE_MAP.get(test_id)
            
            # If not found, try case-insensitive match
            if not template_field_name:
                for key, mapped_name in SYSMEX_TO_TEMPLATE_MAP.items():
                    if key.upper() == test_id.upper():
                        template_field_name = mapped_name
                        break
            
            # If still not found, check if test_id matches a field name directly
            if not template_field_name and test_id in field_names:
                template_field_name = test_id
            
            if template_field_name and template_field_name in field_names:
                try:
                    # Convert value to appropriate type
                    field_def = field_names[template_field_name]
                    field_type = field_def.get('type', 'numeric')
                    
                    if field_type == 'numeric':
                        # Try to convert to float
                        try:
                            numeric_value = float(value)
                            field_values[template_field_name] = numeric_value
                        except (ValueError, TypeError):
                            logger.warning(f"Could not convert {test_id} value '{value}' to numeric for field {template_field_name}")
                            field_values[template_field_name] = value
                    else:
                        field_values[template_field_name] = value
                    
                    # Check for abnormal flags and add to messages if needed
                    flags = astm_data.get('flags', {}).get(test_id, '')
                    if flags and flags.strip():
                        # Look for corresponding message field
                        message_field_name = f"{template_field_name} IP Message"
                        message_fields = template_structure.get('message_fields', [])
                        if any(mf.get('name') == message_field_name for mf in message_fields):
                            messages[message_field_name] = flags
                
                except Exception as e:
                    logger.error(f"Error mapping {test_id} to {template_field_name}: {e}")
        
        # Get sample ID from ASTM data
        sample_no = astm_data.get('sample_id', '') or astm_data.get('specimen_id', '')
        
        return {
            'field_values': field_values,
            'messages': messages,
            'validated_by': '',
            'sample_no': sample_no
        }
    
    def find_investigation_by_sample_id(
        self,
        sample_id: str
    ) -> Optional[tuple]:
        """
        Find investigation by sample ID
        
        Returns:
            Tuple of (investigation, is_inpatient) or None if not found
        """
        from app.models.lab_result import LabResult
        from app.models.inpatient_lab_result import InpatientLabResult
        from app.models.investigation import Investigation
        from app.models.inpatient_investigation import InpatientInvestigation
        import json
        
        # Search in OPD lab results
        opd_results = self.db.query(LabResult).filter(
            LabResult.template_data.isnot(None)
        ).all()
        
        for result in opd_results:
            if result.template_data:
                template_data = result.template_data if isinstance(result.template_data, dict) else json.loads(result.template_data)
                if template_data.get('sample_no', '').strip() == sample_id.strip():
                    investigation = self.db.query(Investigation).filter(
                        Investigation.id == result.investigation_id
                    ).first()
                    if investigation:
                        return (investigation, False)
        
        # Search in IPD lab results
        ipd_results = self.db.query(InpatientLabResult).filter(
            InpatientLabResult.template_data.isnot(None)
        ).all()
        
        for result in ipd_results:
            if result.template_data:
                template_data = result.template_data if isinstance(result.template_data, dict) else json.loads(result.template_data)
                if template_data.get('sample_no', '').strip() == sample_id.strip():
                    investigation = self.db.query(InpatientInvestigation).filter(
                        InpatientInvestigation.id == result.investigation_id
                    ).first()
                    if investigation:
                        return (investigation, True)
        
        return None

