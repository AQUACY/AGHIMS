"""
TCP/IP Server for receiving data from Sysmex XN-330 Analyzer
Listens on configured port and processes ASTM messages
"""
import socket
import threading
import logging
import asyncio
from typing import Optional
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.core.config import settings
from app.services.astm_parser import ASTMParser
from app.services.analyzer_mapper import AnalyzerMapper
from app.models.lab_result import LabResult
from app.models.inpatient_lab_result import InpatientLabResult
from app.models.lab_result_template import LabResultTemplate
from sqlalchemy.orm.attributes import flag_modified
import json
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

# Directory for storing raw analyzer data
RAW_DATA_DIR = Path("analyzer_raw_data")
RAW_DATA_DIR.mkdir(exist_ok=True)


class AnalyzerServer:
    """TCP server for receiving analyzer data"""
    
    def __init__(self):
        self.server_socket: Optional[socket.socket] = None
        self.running = False
        self.parser = ASTMParser()
        self.thread: Optional[threading.Thread] = None
    
    def start(self):
        """Start the TCP server in a background thread"""
        if self.running:
            logger.warning("Analyzer server is already running")
            return
        
        if not settings.ANALYZER_ENABLED:
            logger.info("Analyzer integration is disabled in configuration (set ANALYZER_ENABLED=true in .env)")
            return
        
        try:
            # Use both print and logger to ensure visibility
            print("=" * 70)
            print("Starting Analyzer Server...")
            print(f"  Host: {settings.ANALYZER_HOST}")
            print(f"  Port: {settings.ANALYZER_PORT}")
            print(f"  Equipment IP: {settings.ANALYZER_EQUIPMENT_IP}")
            print("=" * 70)
            
            logger.info("=" * 70)
            logger.info("Starting Analyzer Server...")
            logger.info(f"  Host: {settings.ANALYZER_HOST}")
            logger.info(f"  Port: {settings.ANALYZER_PORT}")
            logger.info(f"  Equipment IP: {settings.ANALYZER_EQUIPMENT_IP}")
            logger.info("=" * 70)
            
            self.running = True
            self.thread = threading.Thread(target=self._run_server, daemon=True, name="AnalyzerServer")
            
            print("Starting server thread...")
            logger.info("Starting server thread...")
            
            self.thread.start()
            
            # Give it a moment to start and bind
            import time
            time.sleep(1.0)  # Increased wait time
            
            if self.thread.is_alive():
                print("✓ Analyzer server thread is alive")
                logger.info(f"✓ Analyzer server thread is alive")
                
                # Check if socket was created
                if self.server_socket:
                    print(f"✓ Server socket created: {self.server_socket}")
                    logger.info(f"✓ Server socket created: {self.server_socket}")
                else:
                    print("⚠ Server socket not yet created (may still be initializing)")
                    logger.warning("Server socket not yet created")
            else:
                print("✗ Analyzer server thread died immediately!")
                print("  Check logs above for errors")
                logger.error(f"✗ Analyzer server thread died immediately!")
                self.running = False
        except Exception as e:
            logger.error(f"Failed to start analyzer server: {e}", exc_info=True)
            self.running = False
    
    def stop(self):
        """Stop the TCP server"""
        self.running = False
        if self.server_socket:
            try:
                self.server_socket.close()
            except Exception as e:
                logger.error(f"Error closing server socket: {e}")
        logger.info("Analyzer server stopped")
    
    def _run_server(self):
        """Run the TCP server (blocking)"""
        try:
            print("Creating socket...")
            logger.info("Creating socket...")
            
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
            bind_address = settings.ANALYZER_HOST
            bind_port = settings.ANALYZER_PORT
            
            print(f"Attempting to bind analyzer server to {bind_address}:{bind_port}")
            logger.info(f"Attempting to bind analyzer server to {bind_address}:{bind_port}")
            
            try:
                self.server_socket.bind((bind_address, bind_port))
                print(f"✓ Successfully bound to {bind_address}:{bind_port}")
                logger.info(f"✓ Successfully bound to {bind_address}:{bind_port}")
            except OSError as e:
                error_msg = f"Failed to bind to {bind_address}:{bind_port}: {e}"
                print(f"✗ {error_msg}")
                print(f"  Port {bind_port} may already be in use or address not available")
                logger.error(error_msg)
                logger.error(f"Port {bind_port} may already be in use or address not available")
                self.running = False
                return
            except Exception as e:
                error_msg = f"Unexpected error binding socket: {e}"
                print(f"✗ {error_msg}")
                logger.error(error_msg, exc_info=True)
                self.running = False
                return
            
            print("Setting up listener...")
            logger.info("Setting up listener...")
            
            self.server_socket.listen(5)
            self.server_socket.settimeout(1.0)  # Allow periodic checking of self.running
            
            print(f"✓ Analyzer server is now listening on {bind_address}:{bind_port}")
            print(f"  Equipment IP: {settings.ANALYZER_EQUIPMENT_IP}")
            print(f"  Ready to receive data from analyzer")
            print(f"  Configure analyzer to connect to: 10.10.17.223:{bind_port}")
            print("=" * 70)
            
            logger.info(f"✓ Analyzer server is now listening on {bind_address}:{bind_port}")
            logger.info(f"  Equipment IP: {settings.ANALYZER_EQUIPMENT_IP}")
            logger.info(f"  Ready to receive data from analyzer")
            logger.info(f"  Configure analyzer to connect to: 10.10.17.223:{bind_port}")
            
            print("Waiting for connections...")
            logger.info("Waiting for connections...")
            
            connection_count = 0
            while self.running:
                try:
                    client_socket, address = self.server_socket.accept()
                    connection_count += 1
                    
                    print(f"🔌 NEW CONNECTION #{connection_count} from {address[0]}:{address[1]}")
                    logger.info(f"🔌 NEW CONNECTION #{connection_count} from {address[0]}:{address[1]}")
                    print(f"   Connection accepted, starting handler thread...")
                    logger.info(f"   Connection accepted, starting handler thread...")
                    
                    # Handle client in a separate thread
                    client_thread = threading.Thread(
                        target=self._handle_client,
                        args=(client_socket, address),
                        daemon=True,
                        name=f"AnalyzerClient-{connection_count}"
                    )
                    client_thread.start()
                    print(f"   Handler thread started for {address}")
                    logger.info(f"   Handler thread started for {address}")
                
                except socket.timeout:
                    # Timeout is expected, continue loop to check self.running
                    continue
                except Exception as e:
                    if self.running:
                        error_msg = f"Error accepting connection: {e}"
                        print(f"✗ {error_msg}")
                        logger.error(error_msg, exc_info=True)
        
        except Exception as e:
            error_msg = f"Error in analyzer server: {e}"
            print(f"✗ {error_msg}")
            logger.error(error_msg, exc_info=True)
        finally:
            print("Analyzer server thread ending...")
            logger.info("Analyzer server thread ending...")
            if self.server_socket:
                try:
                    self.server_socket.close()
                    print("Server socket closed")
                    logger.info("Server socket closed")
                except Exception as e:
                    print(f"Error closing socket: {e}")
                    logger.error(f"Error closing socket: {e}")
    
    def _handle_client(self, client_socket: socket.socket, address: tuple):
        """Handle a client connection"""
        try:
            client_socket.settimeout(settings.ANALYZER_TIMEOUT)
            
            buffer = b''
            connection_id = datetime.now().strftime("%Y%m%d_%H%M%S")
            raw_data_file = None
            
            # Peek at first data to check if it's HTTP (browser/health check)
            try:
                first_data = client_socket.recv(1024, socket.MSG_PEEK)
                logger.info(f"📥 First data from {address}: {len(first_data)} bytes")
                logger.debug(f"   First 50 bytes (hex): {first_data[:50].hex()}")
                logger.debug(f"   First 50 bytes (readable): {first_data[:50]}")
                
                if first_data.startswith(b'GET ') or first_data.startswith(b'POST ') or first_data.startswith(b'HTTP/'):
                    logger.warning(f"⚠️  Ignoring HTTP request from {address} (not analyzer data)")
                    client_socket.close()
                    return
                else:
                    logger.info(f"✓ Non-HTTP data received, processing as analyzer data")
            except Exception as e:
                logger.warning(f"Could not peek data from {address}: {e}")
            
            while self.running:
                try:
                    data = client_socket.recv(4096)
                    if not data:
                        break
                    
                    # Skip HTTP requests
                    if data.startswith(b'GET ') or data.startswith(b'POST ') or data.startswith(b'HTTP/'):
                        logger.info(f"Ignoring HTTP request from {address}")
                        client_socket.close()
                        return
                    
                    # Save raw data to file
                    if raw_data_file is None:
                        raw_data_file = RAW_DATA_DIR / f"raw_data_{connection_id}.txt"
                        logger.info(f"💾 Receiving analyzer data from {address}")
                        logger.info(f"   Saving to: {raw_data_file}")
                        logger.info(f"   First data chunk: {len(data)} bytes")
                    
                    # Append raw bytes to file
                    with open(raw_data_file, 'ab') as f:
                        f.write(data)
                    
                    # Also save a readable hex dump
                    hex_file = RAW_DATA_DIR / f"hex_dump_{connection_id}.txt"
                    with open(hex_file, 'a', encoding='utf-8') as f:
                        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
                        f.write(f"\n=== Data received at {timestamp} ===\n")
                        f.write(f"Length: {len(data)} bytes\n")
                        f.write("Hex dump:\n")
                        for i in range(0, len(data), 16):
                            hex_part = ' '.join(f'{b:02x}' for b in data[i:i+16])
                            ascii_part = ''.join(chr(b) if 32 <= b < 127 else '.' for b in data[i:i+16])
                            f.write(f"{i:04x}: {hex_part:<48} {ascii_part}\n")
                        f.write("\n")
                    
                    buffer += data
                    
                    # Process complete messages
                    # ASTM messages typically end with ETX + checksum + CRLF
                    # Sysmex sends individual records, each starting with STX and ending with ETX
                    # Look for ETX (end of record) or CRLF (record separator)
                    if b'\x03' in buffer:  # ETX (end of record)
                        # Find complete frame
                        etx_pos = buffer.find(b'\x03')
                        if etx_pos > 0:
                            frame_data = buffer[:etx_pos + 1]
                            buffer = buffer[etx_pos + 1:]
                    elif b'\r\n' in buffer or b'\n' in buffer:  # CRLF or LF (record separator)
                        # Some analyzers send records separated by newlines
                        # Process complete records
                        sep = b'\r\n' if b'\r\n' in buffer else b'\n'
                        sep_pos = buffer.find(sep)
                        if sep_pos > 0:
                            frame_data = buffer[:sep_pos]
                            buffer = buffer[sep_pos + len(sep):]
                        else:
                            continue  # Wait for more data
                    else:
                        continue  # Wait for more data
                    
                    if 'frame_data' not in locals():
                        continue
                            
                            # Save parsed frame to readable file
                            parsed_file = RAW_DATA_DIR / f"parsed_{connection_id}.txt"
                            with open(parsed_file, 'a', encoding='utf-8') as f:
                                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
                                f.write(f"\n=== Parsed frame at {timestamp} ===\n")
                                try:
                                    # Try to decode as ASCII/UTF-8 for readability
                                    readable = frame_data.decode('ascii', errors='replace')
                                    f.write(f"Readable content:\n{readable}\n")
                                except:
                                    f.write(f"Binary data (could not decode): {frame_data}\n")
                                f.write(f"\nHex: {frame_data.hex()}\n")
                                f.write("\n" + "="*80 + "\n")
                            
                            # Parse and process
                            self._process_astm_data(frame_data, address)
                            
                            # Send ACK
                            client_socket.send(b'\x06')  # ACK
                            logger.info(f"Sent ACK to analyzer at {address}")
                
                except socket.timeout:
                    # Process any remaining data in buffer
                    if buffer:
                        logger.info(f"Processing remaining buffer data ({len(buffer)} bytes)")
                        self._process_astm_data(buffer, address)
                        buffer = b''
                    break
                except Exception as e:
                    logger.error(f"Error receiving data from {address}: {e}", exc_info=True)
                    break
            
            if raw_data_file:
                logger.info(f"Raw data saved to: {raw_data_file}")
                logger.info(f"Hex dump saved to: {hex_file}")
                logger.info(f"Parsed frames saved to: {parsed_file}")
        
        except Exception as e:
            logger.error(f"Error handling client {address}: {e}", exc_info=True)
        finally:
            try:
                client_socket.close()
            except Exception:
                pass
            logger.info(f"Analyzer connection from {address} closed")
    
    def _process_astm_data(self, data: bytes, address: tuple):
        """Process received ASTM data"""
        try:
            # Log raw data for debugging
            logger.debug(f"Processing {len(data)} bytes from {address}")
            logger.debug(f"Raw data (hex): {data.hex()}")
            
            # Parse ASTM frame
            records = self.parser.parse_frame(data)
            
            if not records:
                logger.warning(f"No records parsed from data from {address}")
                logger.warning(f"Raw data: {data.hex()}")
                return
            
            logger.info(f"Parsed {len(records)} ASTM records from {address}")
            
            # Log parsed records for debugging
            for i, record in enumerate(records):
                logger.debug(f"Record {i+1}: {record}")
            
            # Extract results
            extracted = self.parser.extract_results(records)
            
            sample_id = extracted.get('sample_id', '').strip()
            if not sample_id:
                logger.warning(f"No sample ID found in ASTM data from {address}")
                return
            
            logger.info(f"Processing analyzer results for sample ID: {sample_id}")
            
            # Process in database session
            db = SessionLocal()
            try:
                mapper = AnalyzerMapper(db)
                
                # Find investigation by sample ID
                investigation_info = mapper.find_investigation_by_sample_id(sample_id)
                
                if not investigation_info:
                    logger.warning(f"No investigation found for sample ID: {sample_id}")
                    return
                
                investigation, is_inpatient = investigation_info
                
                # Get lab result
                if is_inpatient:
                    lab_result = db.query(InpatientLabResult).filter(
                        InpatientLabResult.investigation_id == investigation.id
                    ).first()
                else:
                    lab_result = db.query(LabResult).filter(
                        LabResult.investigation_id == investigation.id
                    ).first()
                
                if not lab_result:
                    logger.warning(f"No lab result found for investigation {investigation.id}")
                    return
                
                # Get template
                if not lab_result.template_id:
                    logger.warning(f"No template ID for lab result {lab_result.id}")
                    return
                
                template = db.query(LabResultTemplate).filter(
                    LabResultTemplate.id == lab_result.template_id
                ).first()
                
                if not template:
                    logger.warning(f"Template {lab_result.template_id} not found")
                    return
                
                # Map ASTM data to template format
                template_data = mapper.map_astm_to_template(
                    extracted,
                    template.template_structure
                )
                
                # Preserve existing sample_no if not in analyzer data
                if not template_data.get('sample_no'):
                    if lab_result.template_data:
                        existing_data = lab_result.template_data if isinstance(lab_result.template_data, dict) else json.loads(lab_result.template_data)
                        template_data['sample_no'] = existing_data.get('sample_no', '')
                
                # Merge with existing template_data (preserve existing field_values and messages)
                if lab_result.template_data:
                    existing_data = lab_result.template_data if isinstance(lab_result.template_data, dict) else json.loads(lab_result.template_data)
                    
                    # Merge field_values (analyzer data takes precedence)
                    existing_field_values = existing_data.get('field_values', {})
                    existing_field_values.update(template_data.get('field_values', {}))
                    template_data['field_values'] = existing_field_values
                    
                    # Merge messages (analyzer data takes precedence)
                    existing_messages = existing_data.get('messages', {})
                    existing_messages.update(template_data.get('messages', {}))
                    template_data['messages'] = existing_messages
                    
                    # Preserve validated_by
                    if 'validated_by' in existing_data:
                        template_data['validated_by'] = existing_data['validated_by']
                
                # Update lab result
                lab_result.template_data = template_data
                flag_modified(lab_result, 'template_data')
                
                db.commit()
                
                logger.info(f"Successfully updated lab result {lab_result.id} with analyzer data for sample {sample_id}")
            
            except Exception as e:
                db.rollback()
                logger.error(f"Error processing analyzer data for sample {sample_id}: {e}", exc_info=True)
            finally:
                db.close()
        
        except Exception as e:
            logger.error(f"Error processing ASTM data from {address}: {e}", exc_info=True)


# Global server instance
_analyzer_server: Optional[AnalyzerServer] = None


def get_analyzer_server() -> AnalyzerServer:
    """Get or create the global analyzer server instance"""
    global _analyzer_server
    if _analyzer_server is None:
        _analyzer_server = AnalyzerServer()
    return _analyzer_server


def start_analyzer_server():
    """Start the analyzer server (called on application startup)"""
    server = get_analyzer_server()
    server.start()


def stop_analyzer_server():
    """Stop the analyzer server (called on application shutdown)"""
    server = get_analyzer_server()
    server.stop()

