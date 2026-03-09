"""
DynamoDB client utility for storing and retrieving architecture analysis results.

This module provides a simple interface to interact with DynamoDB for the 
architecture hub storage, similar to how Harvester uses S3.
"""

import os
import json
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class DynamoDBClient:
    """Client for interacting with the architecture hub DynamoDB table."""
    
    def __init__(self, table_name: Optional[str] = None):
        """
        Initialize DynamoDB client.
        
        Args:
            table_name: Name of the DynamoDB table. If not provided, 
                       tries to read from SSM parameter store, then falls back to hardcoded default.
        """
        if table_name:
            self.table_name = table_name
        else:
            # Try environment variable first
            env_table = os.environ.get('DYNAMODB_TABLE_NAME') or os.environ.get('DYNAMODB_TABLE')
            if env_table:
                self.table_name = env_table
                logger.info(f"Using table name from environment: {self.table_name}")
            else:
                # Try to get table name from SSM parameter store
                self.table_name = self._get_table_name_from_ssm()
                if not self.table_name:
                    # Fallback to hardcoded default
                    self.table_name = "staging-repo-swarm-results"
                    logger.info(f"Using hardcoded default table name: {self.table_name}")
        
        # Initialize boto3 DynamoDB resource
        # Support local DynamoDB for development
        endpoint_url = os.environ.get('DYNAMODB_ENDPOINT')
        kwargs = {'region_name': os.environ.get('AWS_DEFAULT_REGION', 'us-east-1')}
        if endpoint_url:
            kwargs['endpoint_url'] = endpoint_url
            logger.info(f"Using DynamoDB endpoint: {endpoint_url}")
        self.dynamodb = boto3.resource('dynamodb', **kwargs)
        self.table = self.dynamodb.Table(self.table_name)
        
        logger.info(f"Initialized DynamoDB client for table: {self.table_name}")
    
    def _get_table_name_from_ssm(self) -> Optional[str]:
        """
        Try to get the DynamoDB table name from SSM parameter store.
        
        Returns:
            Table name from SSM or None if parameter doesn't exist or access fails.
        """
        try:
            # Try common SSM parameter paths
            ssm_paths = [
                "/staging/repo-swarm/dynamodb_table_name",
                "/repo-swarm/staging/dynamodb_table_name", 
                "/staging/repo-swarm-results/table_name",
                os.environ.get('DYNAMODB_TABLE_NAME')  # Also check env var as backup
            ]
            
            ssm_client = boto3.client('ssm', region_name=os.environ.get('AWS_DEFAULT_REGION', 'us-east-1'))
            
            for path in ssm_paths:
                if not path:  # Skip None values
                    continue
                    
                try:
                    response = ssm_client.get_parameter(Name=path, WithDecryption=True)
                    table_name = response['Parameter']['Value']
                    if table_name:
                        logger.info(f"Found DynamoDB table name in SSM parameter: {path}")
                        return table_name
                except ClientError as e:
                    if e.response['Error']['Code'] == 'ParameterNotFound':
                        logger.debug(f"SSM parameter not found: {path}")
                        continue
                    else:
                        logger.warning(f"Error accessing SSM parameter {path}: {e}")
                        continue
            
            logger.info("No DynamoDB table name found in SSM parameters")
            return None
            
        except Exception as e:
            logger.warning(f"Failed to read from SSM parameter store: {e}")
            return None
    
    def save_investigation_metadata(self,
                                   repository_name: str,
                                   repository_url: str,
                                   latest_commit: str,
                                   branch_name: str,
                                   analysis_type: str = "investigation",
                                   analysis_data: Optional[Dict[str, Any]] = None,
                                   ttl_days: Optional[int] = 90) -> Dict[str, Any]:
        """
        Save repository investigation metadata to DynamoDB.
        
        Args:
            repository_name: Name of the repository analyzed
            repository_url: URL of the repository
            latest_commit: SHA of the latest commit processed
            branch_name: Name of the branch processed
            analysis_type: Type of analysis (defaults to 'investigation')
            analysis_data: Optional analysis results as a dictionary
            ttl_days: Number of days before the item expires (optional)
        
        Returns:
            The saved item including generated timestamps
        """
        try:
            # Generate timestamps
            current_timestamp = int(datetime.now(timezone.utc).timestamp())
            
            # Prepare item
            item = {
                'repository_name': repository_name,
                'repository_url': repository_url,
                'analysis_timestamp': current_timestamp,
                'analysis_type': analysis_type,
                'latest_commit': latest_commit,
                'branch_name': branch_name,
                'created_at': datetime.now(timezone.utc).isoformat(),
                'updated_at': datetime.now(timezone.utc).isoformat(),
            }
            
            # Add analysis data if provided
            if analysis_data:
                item['analysis_data'] = json.dumps(analysis_data)  # Store as JSON string
            
            # Add TTL if specified
            if ttl_days:
                ttl_timestamp = current_timestamp + (ttl_days * 24 * 60 * 60)
                item['ttl_timestamp'] = ttl_timestamp
            
            # Convert floats to Decimal for DynamoDB compatibility
            item = self._convert_floats_to_decimal(item)
            
            # Save to DynamoDB
            self.table.put_item(Item=item)
            
            logger.info(f"Saved investigation metadata for {repository_name} (commit: {latest_commit[:8]}) at timestamp {current_timestamp}")
            return item
            
        except ClientError as e:
            logger.error(f"Error saving to DynamoDB: {e}")
            raise
    
    def get_latest_investigation(self,
                                repository_name: str) -> Optional[Dict[str, Any]]:
        """
        Get the latest investigation metadata for a repository.
        
        Args:
            repository_name: Name of the repository
        
        Returns:
            The latest investigation metadata or None if not found
        """
        try:
            # Query by repository name, sorted by timestamp (descending)
            response = self.table.query(
                KeyConditionExpression=Key('repository_name').eq(repository_name),
                ScanIndexForward=False,  # Sort descending by range key (timestamp)
                Limit=1
            )
            
            items = response.get('Items', [])
            
            if items:
                item = items[0]
                # Parse the JSON string back to dict if present
                if 'analysis_data' in item and isinstance(item['analysis_data'], str):
                    item['analysis_data'] = json.loads(item['analysis_data'])
                return self._convert_decimal_to_float(item)
            
            return None
            
        except ClientError as e:
            logger.error(f"Error reading from DynamoDB: {e}")
            raise
    
    def get_latest_analysis(self, 
                           repository_name: str,
                           analysis_type: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Get the latest analysis for a repository.
        
        Args:
            repository_name: Name of the repository
            analysis_type: Optional filter by analysis type
        
        Returns:
            The latest analysis item or None if not found
        """
        try:
            # Query by repository name, sorted by timestamp (descending)
            response = self.table.query(
                KeyConditionExpression=Key('repository_name').eq(repository_name),
                ScanIndexForward=False,  # Sort descending by range key (timestamp)
                Limit=1 if not analysis_type else 100  # Get more if filtering by type
            )
            
            items = response.get('Items', [])
            
            if analysis_type and items:
                # Filter by analysis type
                items = [item for item in items if item.get('analysis_type') == analysis_type]
            
            if items:
                item = items[0]
                # Parse the JSON string back to dict
                if 'analysis_data' in item and isinstance(item['analysis_data'], str):
                    item['analysis_data'] = json.loads(item['analysis_data'])
                return self._convert_decimal_to_float(item)
            
            return None
            
        except ClientError as e:
            logger.error(f"Error reading from DynamoDB: {e}")
            raise
    
    def get_all_analyses(self, 
                        repository_name: str,
                        limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get all analyses for a repository (with limit).
        
        Args:
            repository_name: Name of the repository
            limit: Maximum number of items to return
        
        Returns:
            List of analysis items
        """
        try:
            response = self.table.query(
                KeyConditionExpression=Key('repository_name').eq(repository_name),
                ScanIndexForward=False,  # Sort descending by timestamp
                Limit=limit
            )
            
            items = response.get('Items', [])
            
            # Parse JSON strings back to dicts
            for item in items:
                if 'analysis_data' in item and isinstance(item['analysis_data'], str):
                    item['analysis_data'] = json.loads(item['analysis_data'])
            
            return [self._convert_decimal_to_float(item) for item in items]
            
        except ClientError as e:
            logger.error(f"Error reading from DynamoDB: {e}")
            raise
    
    def query_by_analysis_type(self,
                               analysis_type: str,
                               limit: int = 10) -> List[Dict[str, Any]]:
        """
        Query all repositories by analysis type using the GSI.
        
        Args:
            analysis_type: Type of analysis to query
            limit: Maximum number of items to return
        
        Returns:
            List of analysis items
        """
        try:
            response = self.table.query(
                IndexName='AnalysisTypeIndex',
                KeyConditionExpression=Key('analysis_type').eq(analysis_type),
                ScanIndexForward=False,  # Sort descending by timestamp
                Limit=limit
            )
            
            items = response.get('Items', [])
            
            # Parse JSON strings back to dicts
            for item in items:
                if 'analysis_data' in item and isinstance(item['analysis_data'], str):
                    item['analysis_data'] = json.loads(item['analysis_data'])
            
            return [self._convert_decimal_to_float(item) for item in items]
            
        except ClientError as e:
            logger.error(f"Error querying DynamoDB GSI: {e}")
            raise
    
    def delete_analysis(self,
                       repository_name: str,
                       analysis_timestamp: int) -> bool:
        """
        Delete a specific analysis.
        
        Args:
            repository_name: Name of the repository
            analysis_timestamp: Timestamp of the analysis to delete
        
        Returns:
            True if deleted successfully
        """
        try:
            self.table.delete_item(
                Key={
                    'repository_name': repository_name,
                    'analysis_timestamp': analysis_timestamp
                }
            )
            logger.info(f"Deleted analysis for {repository_name} at timestamp {analysis_timestamp}")
            return True
            
        except ClientError as e:
            logger.error(f"Error deleting from DynamoDB: {e}")
            raise
    
    def save_temporary_analysis_data(self,
                                    reference_key: str,
                                    prompt_content: str,
                                    repo_structure: str,
                                    context: Optional[str] = None,
                                    ttl_minutes: int = 60) -> Dict[str, Any]:
        """
        Save temporary analysis data to DynamoDB with a short TTL.
        This is used to pass large text data to activities without going through logs.
        
        Args:
            reference_key: Unique reference key for this analysis data
            prompt_content: The prompt template content
            repo_structure: Repository structure string
            context: Optional context from previous analyses
            ttl_minutes: TTL in minutes (default 60 minutes)
        
        Returns:
            Dictionary with save status
        """
        try:
            # Generate timestamps
            current_timestamp = int(datetime.now(timezone.utc).timestamp())
            ttl_timestamp = current_timestamp + (ttl_minutes * 60)
            
            # Check if data needs compression or chunking
            import gzip
            import base64
            import json
            
            # Prepare the data
            data_to_store = {
                'prompt_content': prompt_content,
                'repo_structure': repo_structure
            }
            if context:
                data_to_store['context'] = context
            
            # Estimate size (rough approximation)
            data_json = json.dumps(data_to_store)
            data_size = len(data_json.encode('utf-8'))
            
            # If data is large (> 300KB to leave room for metadata), compress it
            if data_size > 300 * 1024:  # 300KB threshold
                logger.info(f"Large data detected ({data_size} bytes), compressing before saving...")
                
                # Compress the data
                compressed_data = gzip.compress(data_json.encode('utf-8'))
                compressed_b64 = base64.b64encode(compressed_data).decode('utf-8')
                compressed_size = len(compressed_b64)
                
                logger.info(f"Compressed from {data_size} to {compressed_size} bytes (ratio: {compressed_size/data_size:.2%})")
                
                # Check if even compressed data is too large (> 380KB to leave room for metadata)
                if compressed_size > 380 * 1024:
                    # Need to use chunking strategy
                    return self._save_chunked_analysis_data(
                        reference_key, prompt_content, repo_structure, 
                        context, ttl_minutes, current_timestamp, ttl_timestamp
                    )
                
                # Save compressed data
                item = {
                    'repository_name': f"_temp_{reference_key}",
                    'analysis_timestamp': current_timestamp,
                    'analysis_type': 'temporary_analysis_data',
                    'reference_key': reference_key,
                    'compressed_data': compressed_b64,
                    'is_compressed': True,
                    'original_size': data_size,
                    'compressed_size': compressed_size,
                    'ttl_timestamp': ttl_timestamp,
                    'created_at': datetime.now(timezone.utc).isoformat()
                }
            else:
                # Data is small enough, save as-is
                item = {
                    'repository_name': f"_temp_{reference_key}",
                    'analysis_timestamp': current_timestamp,
                    'analysis_type': 'temporary_analysis_data',
                    'reference_key': reference_key,
                    'prompt_content': prompt_content,
                    'repo_structure': repo_structure,
                    'is_compressed': False,
                    'ttl_timestamp': ttl_timestamp,
                    'created_at': datetime.now(timezone.utc).isoformat()
                }
                
                if context:
                    item['context'] = context
            
            # Convert floats to Decimal for DynamoDB compatibility
            item = self._convert_floats_to_decimal(item)
            
            # Save to DynamoDB
            self.table.put_item(Item=item)
            
            logger.info(f"Saved temporary analysis data with reference key: {reference_key}")
            return {
                "status": "success",
                "reference_key": reference_key,
                "ttl_minutes": ttl_minutes,
                "is_compressed": item.get('is_compressed', False)
            }
            
        except ClientError as e:
            logger.error(f"Error saving temporary analysis data to DynamoDB: {e}")
            raise
    
    def save_generic_data(self,
                         reference_key: str,
                         data: Any,
                         ttl_minutes: int = 60) -> Dict[str, Any]:
        """
        Save arbitrary JSON-serializable data to DynamoDB with TTL.
        Handles compression and chunking for large payloads.

        Unlike save_temporary_analysis_data (which expects prompt_content/repo_structure),
        this method stores any JSON-serializable data (dicts, lists, strings, etc.).

        Args:
            reference_key: Unique reference key for retrieval
            data: Any JSON-serializable data (dict, list, str, etc.)
            ttl_minutes: TTL in minutes (default 60)

        Returns:
            Dictionary with save status
        """
        try:
            import gzip
            import base64
            import json

            current_timestamp = int(datetime.now(timezone.utc).timestamp())
            ttl_timestamp = current_timestamp + (ttl_minutes * 60)

            # Serialize data to JSON
            data_json = json.dumps(data)
            data_size = len(data_json.encode('utf-8'))

            logger.info(f"Saving generic data ({data_size} bytes) with key: {reference_key}")

            if data_size > 300 * 1024:  # 300KB threshold
                logger.info(f"Large generic data detected ({data_size} bytes), compressing...")

                compressed_data = gzip.compress(data_json.encode('utf-8'))
                compressed_b64 = base64.b64encode(compressed_data).decode('utf-8')
                compressed_size = len(compressed_b64)

                logger.info(f"Compressed from {data_size} to {compressed_size} bytes (ratio: {compressed_size/data_size:.2%})")

                if compressed_size > 380 * 1024:
                    # Use chunking for very large data
                    return self._save_chunked_generic_data(
                        reference_key, data_json, ttl_minutes,
                        current_timestamp, ttl_timestamp
                    )

                # Save compressed
                item = {
                    'repository_name': f"_temp_{reference_key}",
                    'analysis_timestamp': current_timestamp,
                    'analysis_type': 'temporary_analysis_data',
                    'reference_key': reference_key,
                    'compressed_data': compressed_b64,
                    'is_compressed': True,
                    'is_generic': True,
                    'original_size': data_size,
                    'compressed_size': compressed_size,
                    'ttl_timestamp': ttl_timestamp,
                    'created_at': datetime.now(timezone.utc).isoformat()
                }
            else:
                # Small enough to save as-is
                item = {
                    'repository_name': f"_temp_{reference_key}",
                    'analysis_timestamp': current_timestamp,
                    'analysis_type': 'temporary_analysis_data',
                    'reference_key': reference_key,
                    'generic_data': data_json,
                    'is_compressed': False,
                    'is_generic': True,
                    'ttl_timestamp': ttl_timestamp,
                    'created_at': datetime.now(timezone.utc).isoformat()
                }

            item = self._convert_floats_to_decimal(item)
            self.table.put_item(Item=item)

            logger.info(f"Saved generic data with reference key: {reference_key}")
            return {
                "status": "success",
                "reference_key": reference_key,
                "ttl_minutes": ttl_minutes,
                "is_compressed": item.get('is_compressed', False)
            }

        except ClientError as e:
            logger.error(f"Error saving generic data to DynamoDB: {e}")
            raise

    def _save_chunked_generic_data(self, reference_key: str, data_json: str,
                                   ttl_minutes: int, current_timestamp: int,
                                   ttl_timestamp: int) -> Dict[str, Any]:
        """
        Save generic data in chunks when it's too large even after compression.
        """
        import gzip
        import base64

        logger.info(f"Generic data too large even after compression, using chunking for: {reference_key}")

        compressed_data = gzip.compress(data_json.encode('utf-8'))
        compressed_b64 = base64.b64encode(compressed_data).decode('utf-8')

        chunk_size = 350 * 1024
        total_size = len(compressed_b64)
        total_chunks = (total_size + chunk_size - 1) // chunk_size

        logger.info(f"Splitting {total_size} bytes into {total_chunks} chunks")

        try:
            # Save metadata item
            metadata_item = {
                'repository_name': f"_temp_{reference_key}",
                'analysis_timestamp': current_timestamp,
                'analysis_type': 'temporary_analysis_data',
                'reference_key': reference_key,
                'is_chunked': True,
                'is_generic': True,
                'total_chunks': total_chunks,
                'total_size': total_size,
                'ttl_timestamp': ttl_timestamp,
                'created_at': datetime.now(timezone.utc).isoformat()
            }
            metadata_item = self._convert_floats_to_decimal(metadata_item)
            self.table.put_item(Item=metadata_item)

            for i in range(total_chunks):
                start_idx = i * chunk_size
                end_idx = min((i + 1) * chunk_size, total_size)
                chunk_data = compressed_b64[start_idx:end_idx]

                chunk_item = {
                    'repository_name': f"_temp_{reference_key}_chunk_{i}",
                    'analysis_timestamp': current_timestamp,
                    'analysis_type': 'temporary_analysis_chunk',
                    'reference_key': reference_key,
                    'chunk_index': i,
                    'chunk_data': chunk_data,
                    'ttl_timestamp': ttl_timestamp,
                    'created_at': datetime.now(timezone.utc).isoformat()
                }
                chunk_item = self._convert_floats_to_decimal(chunk_item)
                self.table.put_item(Item=chunk_item)

                logger.debug(f"Saved generic chunk {i+1}/{total_chunks} for {reference_key}")

            logger.info(f"Successfully saved {total_chunks} generic chunks for reference key: {reference_key}")
            return {
                "status": "success",
                "reference_key": reference_key,
                "ttl_minutes": ttl_minutes,
                "is_chunked": True,
                "total_chunks": total_chunks
            }

        except ClientError as e:
            logger.error(f"Error saving chunked generic data to DynamoDB: {e}")
            raise

    def _save_chunked_analysis_data(self, reference_key: str, prompt_content: str,
                                   repo_structure: str, context: Optional[str],
                                   ttl_minutes: int, current_timestamp: int,
                                   ttl_timestamp: int) -> Dict[str, Any]:
        """
        Save analysis data in chunks when it's too large even after compression.
        
        Args:
            reference_key: Unique reference key
            prompt_content: The prompt template content
            repo_structure: Repository structure string
            context: Optional context from previous analyses
            ttl_minutes: TTL in minutes
            current_timestamp: Current timestamp
            ttl_timestamp: TTL timestamp
            
        Returns:
            Dictionary with save status
        """
        import json
        import gzip
        import base64
        
        logger.info(f"Data too large even after compression, using chunking strategy for: {reference_key}")
        
        # Prepare data
        data_to_store = {
            'prompt_content': prompt_content,
            'repo_structure': repo_structure
        }
        if context:
            data_to_store['context'] = context
        
        # Compress the entire data
        data_json = json.dumps(data_to_store)
        compressed_data = gzip.compress(data_json.encode('utf-8'))
        compressed_b64 = base64.b64encode(compressed_data).decode('utf-8')
        
        # Split into chunks (350KB per chunk to leave room for metadata)
        chunk_size = 350 * 1024  # 350KB chunks
        total_size = len(compressed_b64)
        total_chunks = (total_size + chunk_size - 1) // chunk_size  # Ceiling division
        
        logger.info(f"Splitting {total_size} bytes into {total_chunks} chunks")
        
        try:
            # Save metadata item
            metadata_item = {
                'repository_name': f"_temp_{reference_key}",
                'analysis_timestamp': current_timestamp,
                'analysis_type': 'temporary_analysis_data',
                'reference_key': reference_key,
                'is_chunked': True,
                'total_chunks': total_chunks,
                'total_size': total_size,
                'ttl_timestamp': ttl_timestamp,
                'created_at': datetime.now(timezone.utc).isoformat()
            }
            metadata_item = self._convert_floats_to_decimal(metadata_item)
            self.table.put_item(Item=metadata_item)
            
            # Save each chunk
            for i in range(total_chunks):
                start_idx = i * chunk_size
                end_idx = min((i + 1) * chunk_size, total_size)
                chunk_data = compressed_b64[start_idx:end_idx]
                
                chunk_item = {
                    'repository_name': f"_temp_{reference_key}_chunk_{i}",
                    'analysis_timestamp': current_timestamp,
                    'analysis_type': 'temporary_analysis_chunk',
                    'reference_key': reference_key,
                    'chunk_index': i,
                    'chunk_data': chunk_data,
                    'ttl_timestamp': ttl_timestamp,
                    'created_at': datetime.now(timezone.utc).isoformat()
                }
                chunk_item = self._convert_floats_to_decimal(chunk_item)
                self.table.put_item(Item=chunk_item)
                
                logger.debug(f"Saved chunk {i+1}/{total_chunks} for {reference_key}")
            
            logger.info(f"Successfully saved {total_chunks} chunks for reference key: {reference_key}")
            return {
                "status": "success",
                "reference_key": reference_key,
                "ttl_minutes": ttl_minutes,
                "is_chunked": True,
                "total_chunks": total_chunks
            }
            
        except ClientError as e:
            logger.error(f"Error saving chunked data to DynamoDB: {e}")
            raise
    
    def _get_chunked_analysis_data(self, reference_key: str, total_chunks: int) -> Optional[Dict[str, Any]]:
        """
        Retrieve and reassemble chunked analysis data from DynamoDB.
        
        Args:
            reference_key: Reference key for the chunked data
            total_chunks: Total number of chunks to retrieve
            
        Returns:
            Dictionary with the reassembled analysis data or None if not found
        """
        import gzip
        import base64
        import json
        
        logger.info(f"Retrieving {total_chunks} chunks for reference key: {reference_key}")
        
        try:
            # Retrieve all chunks
            chunks = []
            for i in range(total_chunks):
                response = self.table.query(
                    KeyConditionExpression=Key('repository_name').eq(f"_temp_{reference_key}_chunk_{i}"),
                    ScanIndexForward=False,
                    Limit=1
                )
                
                items = response.get('Items', [])
                if items:
                    chunk_data = items[0].get('chunk_data', '')
                    chunks.append(chunk_data)
                else:
                    logger.error(f"Missing chunk {i} for reference key: {reference_key}")
                    return None
            
            # Reassemble compressed data
            compressed_b64 = ''.join(chunks)
            
            # Decompress
            compressed_data = base64.b64decode(compressed_b64)
            decompressed_json = gzip.decompress(compressed_data).decode('utf-8')
            data = json.loads(decompressed_json)
            
            logger.info(f"Successfully retrieved and reassembled {total_chunks} chunks for {reference_key}")
            if isinstance(data, dict):
                data['reference_key'] = reference_key
            return data

        except Exception as e:
            logger.error(f"Error retrieving chunked data from DynamoDB: {e}")
            return None
    
    def get_temporary_analysis_data(self, reference_key: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve temporary analysis data from DynamoDB using reference key.
        Handles both compressed and chunked data.
        
        Args:
            reference_key: The unique reference key for the analysis data
        
        Returns:
            Dictionary with the analysis data or None if not found
        """
        try:
            # Query using the special temporary prefix
            response = self.table.query(
                KeyConditionExpression=Key('repository_name').eq(f"_temp_{reference_key}"),
                ScanIndexForward=False,
                Limit=1
            )
            
            items = response.get('Items', [])
            
            if items:
                item = items[0]
                # Check if item hasn't expired (though DynamoDB should auto-delete)
                current_timestamp = int(datetime.now(timezone.utc).timestamp())
                ttl_timestamp = item.get('ttl_timestamp', 0)
                
                if ttl_timestamp > 0 and current_timestamp > ttl_timestamp:
                    logger.warning(f"Temporary analysis data has expired for key: {reference_key}")
                    return None
                
                # Check if data is chunked
                if item.get('is_chunked', False):
                    return self._get_chunked_analysis_data(reference_key, item.get('total_chunks', 0))
                
                # Check if data is compressed
                if item.get('is_compressed', False):
                    import gzip
                    import base64
                    import json
                    
                    compressed_b64 = item.get('compressed_data')
                    if compressed_b64:
                        # Decompress the data
                        compressed_data = base64.b64decode(compressed_b64)
                        decompressed_json = gzip.decompress(compressed_data).decode('utf-8')
                        data = json.loads(decompressed_json)
                        
                        logger.info(f"Retrieved and decompressed temporary analysis data for reference key: {reference_key}")
                        if isinstance(data, dict):
                            data['reference_key'] = reference_key
                        return data
                    else:
                        logger.error(f"Compressed data flag set but no compressed_data found for: {reference_key}")
                        return None
                
                # Check if this is generic data (stored via save_generic_data)
                if item.get('is_generic', False):
                    import json
                    generic_data = item.get('generic_data')
                    if generic_data:
                        data = json.loads(generic_data) if isinstance(generic_data, str) else generic_data
                        if isinstance(data, dict):
                            data['reference_key'] = reference_key
                        return data
                    else:
                        logger.error(f"Generic data flag set but no generic_data found for: {reference_key}")
                        return None

                # Regular uncompressed data - convert and return
                return self._convert_decimal_to_float(item)
            
            logger.warning(f"No temporary analysis data found for key: {reference_key}")
            return None
            
        except ClientError as e:
            logger.error(f"Error retrieving temporary analysis data from DynamoDB: {e}")
            raise
    
    def delete_temporary_analysis_data(self, reference_key: str) -> bool:
        """
        Delete temporary analysis data from DynamoDB.
        
        Args:
            reference_key: The unique reference key for the analysis data
        
        Returns:
            True if deleted successfully
        """
        try:
            # First get the item to find the timestamp
            item = self.get_temporary_analysis_data(reference_key)
            if not item:
                logger.info(f"No temporary data to delete for key: {reference_key}")
                return True
            
            # Delete the item
            self.table.delete_item(
                Key={
                    'repository_name': f"_temp_{reference_key}",
                    'analysis_timestamp': item['analysis_timestamp']
                }
            )
            logger.info(f"Deleted temporary analysis data for key: {reference_key}")
            return True
            
        except ClientError as e:
            logger.error(f"Error deleting temporary analysis data from DynamoDB: {e}")
            raise
    
    def save_analysis_result(self,
                           reference_key: str,
                           result_content: str,
                           step_name: str = None,
                           ttl_minutes: int = 60) -> Dict[str, Any]:
        """
        Save analysis result to DynamoDB with a reference key.
        Automatically compresses large results.
        
        Args:
            reference_key: Unique reference key for this result
            result_content: The analysis result content
            step_name: Optional step name for tracking
            ttl_minutes: TTL in minutes (default 60 minutes)
        
        Returns:
            Dictionary with save status and reference key
        """
        try:
            # Generate timestamps
            current_timestamp = int(datetime.now(timezone.utc).timestamp())
            ttl_timestamp = current_timestamp + (ttl_minutes * 60)
            
            # Check if result needs compression
            import gzip
            import base64
            
            result_size = len(result_content.encode('utf-8'))
            
            # If result is large (> 300KB), compress it
            if result_size > 300 * 1024:  # 300KB threshold
                logger.info(f"Large result detected ({result_size} bytes), compressing before saving...")
                
                # Compress the result
                compressed_data = gzip.compress(result_content.encode('utf-8'))
                compressed_b64 = base64.b64encode(compressed_data).decode('utf-8')
                compressed_size = len(compressed_b64)
                
                logger.info(f"Compressed result from {result_size} to {compressed_size} bytes (ratio: {compressed_size/result_size:.2%})")
                
                # Save compressed result
                item = {
                    'repository_name': f"_result_{reference_key}",
                    'analysis_timestamp': current_timestamp,
                    'analysis_type': 'analysis_result',
                    'reference_key': reference_key,
                    'compressed_result': compressed_b64,
                    'is_compressed': True,
                    'original_size': result_size,
                    'compressed_size': compressed_size,
                    'ttl_timestamp': ttl_timestamp,
                    'created_at': datetime.now(timezone.utc).isoformat()
                }
            else:
                # Result is small enough, save as-is
                item = {
                    'repository_name': f"_result_{reference_key}",
                    'analysis_timestamp': current_timestamp,
                    'analysis_type': 'analysis_result',
                    'reference_key': reference_key,
                    'result_content': result_content,
                    'is_compressed': False,
                    'ttl_timestamp': ttl_timestamp,
                    'created_at': datetime.now(timezone.utc).isoformat()
                }
            
            if step_name:
                item['step_name'] = step_name
            
            # Convert floats to Decimal for DynamoDB compatibility
            item = self._convert_floats_to_decimal(item)
            
            # Save to DynamoDB
            self.table.put_item(Item=item)
            
            logger.info(f"Saved analysis result with reference key: {reference_key}")
            return {
                "status": "success",
                "result_key": reference_key,
                "ttl_minutes": ttl_minutes,
                "is_compressed": item.get('is_compressed', False)
            }
            
        except ClientError as e:
            logger.error(f"Error saving analysis result to DynamoDB: {e}")
            raise
    
    def get_analysis_result(self, reference_key: str) -> Optional[str]:
        """
        Retrieve analysis result from DynamoDB using reference key.
        Handles both compressed and uncompressed results.
        
        Args:
            reference_key: The unique reference key for the result
        
        Returns:
            The result content string or None if not found
        """
        try:
            # Query using the result prefix
            response = self.table.query(
                KeyConditionExpression=Key('repository_name').eq(f"_result_{reference_key}"),
                ScanIndexForward=False,
                Limit=1
            )
            
            items = response.get('Items', [])
            
            if items:
                item = items[0]
                # Check if item hasn't expired
                current_timestamp = int(datetime.now(timezone.utc).timestamp())
                ttl_timestamp = item.get('ttl_timestamp', 0)
                
                if ttl_timestamp > 0 and current_timestamp > ttl_timestamp:
                    logger.warning(f"Analysis result has expired for key: {reference_key}")
                    return None
                
                # Check if result is compressed
                if item.get('is_compressed', False):
                    import gzip
                    import base64
                    
                    compressed_b64 = item.get('compressed_result')
                    if compressed_b64:
                        # Decompress the result
                        compressed_data = base64.b64decode(compressed_b64)
                        decompressed_result = gzip.decompress(compressed_data).decode('utf-8')
                        
                        logger.info(f"Retrieved and decompressed analysis result for key: {reference_key}")
                        return decompressed_result
                    else:
                        logger.error(f"Compressed result flag set but no compressed_result found for: {reference_key}")
                        return None
                
                # Return uncompressed result
                return item.get('result_content')
            
            logger.warning(f"No analysis result found for key: {reference_key}")
            return None
            
        except ClientError as e:
            logger.error(f"Error retrieving analysis result from DynamoDB: {e}")
            raise
    
    def get_multiple_analysis_data(self, reference_keys: list) -> Dict[str, Any]:
        """
        Retrieve multiple analysis data items from DynamoDB.
        Used for combining context from multiple previous steps.
        
        Args:
            reference_keys: List of reference keys to retrieve
        
        Returns:
            Dictionary mapping reference keys to their data
        """
        results = {}
        
        for key in reference_keys:
            try:
                # Try to get as temporary analysis data first
                data = self.get_temporary_analysis_data(key)
                if data:
                    results[key] = {
                        'type': 'analysis_data',
                        'data': data
                    }
                    continue
                
                # Try to get as result
                result = self.get_analysis_result(key)
                if result:
                    results[key] = {
                        'type': 'result',
                        'content': result
                    }
                    continue
                    
                logger.warning(f"No data found for reference key: {key}")
                
            except Exception as e:
                logger.error(f"Error retrieving data for key {key}: {e}")
                
        return results
    
    @staticmethod
    def _convert_floats_to_decimal(obj):
        """Convert float values to Decimal for DynamoDB compatibility."""
        if isinstance(obj, float):
            return Decimal(str(obj))
        elif isinstance(obj, dict):
            return {k: DynamoDBClient._convert_floats_to_decimal(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [DynamoDBClient._convert_floats_to_decimal(i) for i in obj]
        return obj
    
    @staticmethod
    def _convert_decimal_to_float(obj):
        """Convert Decimal values back to float for Python compatibility."""
        if isinstance(obj, Decimal):
            return float(obj)
        elif isinstance(obj, dict):
            return {k: DynamoDBClient._convert_decimal_to_float(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [DynamoDBClient._convert_decimal_to_float(i) for i in obj]
        return obj


# Singleton instance for reuse across activities
_dynamodb_client = None

def get_dynamodb_client() -> DynamoDBClient:
    """
    Get a singleton instance of the DynamoDB client.
    
    This follows the same pattern as Harvester's S3 client utilities.
    """
    global _dynamodb_client
    if _dynamodb_client is None:
        _dynamodb_client = DynamoDBClient()
    return _dynamodb_client
