import boto3
import os
from botocore.exceptions import ClientError
from typing import Dict, Any, List
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class DynamoDBClient:
    def __init__(self):
        self.aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
        self.aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")
        self.aws_region = os.getenv("AWS_REGION", "us-east-1")
        self.table_name = os.getenv("EVENTS_TABLE_NAME")
        
        # Initialize DynamoDB client
        self.dynamodb = boto3.client(
            'dynamodb',
            aws_access_key_id=self.aws_access_key_id,
            aws_secret_access_key=self.aws_secret_access_key,
            region_name=self.aws_region
        )
        
        # Initialize DynamoDB resource for easier operations
        self.dynamodb_resource = boto3.resource(
            'dynamodb',
            aws_access_key_id=self.aws_access_key_id,
            aws_secret_access_key=self.aws_secret_access_key,
            region_name=self.aws_region
        )
        
        if self.table_name:
            self.table = self.dynamodb_resource.Table(self.table_name)
        else:
            self.table = None
    
    def test_connection(self) -> Dict[str, Any]:
        """Test DynamoDB connection and return table info"""
        if not self.table_name:
            return {
                "status": "error",
                "error": "Table name not configured in environment variables"
            }
        
        try:
            response = self.dynamodb.describe_table(TableName=self.table_name)
            return {
                "status": "connected",
                "table_name": self.table_name,
                "table_status": response['Table']['TableStatus'],
                "item_count": response['Table']['ItemCount']
            }
        except ClientError as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    def put_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Put item into DynamoDB table"""
        try:
            response = self.table.put_item(Item=item)
            return {
                "status": "success",
                "response": response
            }
        except ClientError as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    def get_item(self, pk: str, sk: str) -> Dict[str, Any]:
        """Get item from DynamoDB table"""
        try:
            response = self.table.get_item(
                Key={
                    'pk': pk,
                    'sk': sk
                }
            )
            if 'Item' in response:
                return {
                    "status": "success",
                    "item": response['Item']
                }
            else:
                return {
                    "status": "not_found",
                    "item": None
                }
        except ClientError as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    def query_items(self, pk: str, sk_condition: str = None) -> Dict[str, Any]:
        """Query items by partition key"""
        try:
            if sk_condition:
                response = self.table.query(
                    KeyConditionExpression='pk = :pk AND begins_with(sk, :sk)',
                    ExpressionAttributeValues={
                        ':pk': pk,
                        ':sk': sk_condition
                    }
                )
            else:
                response = self.table.query(
                    KeyConditionExpression='pk = :pk',
                    ExpressionAttributeValues={
                        ':pk': pk
                    }
                )
            
            return {
                "status": "success",
                "items": response['Items'],
                "count": response['Count']
            }
        except ClientError as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    def scan_items(self, filter_expression: str = None, expression_values: Dict[str, Any] = None, expression_names: Dict[str, str] = None) -> Dict[str, Any]:
        """Scan all items in the table with optional filter"""
        try:
            scan_kwargs = {}
            if filter_expression and expression_values:
                scan_kwargs['FilterExpression'] = filter_expression
                scan_kwargs['ExpressionAttributeValues'] = expression_values
                if expression_names:
                    scan_kwargs['ExpressionAttributeNames'] = expression_names
            
            response = self.table.scan(**scan_kwargs)
            
            return {
                "status": "success",
                "items": response['Items'],
                "count": response['Count']
            }
        except ClientError as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    def transact_write(self, transact_items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Execute a transactional write operation"""
        try:
            response = self.dynamodb.transact_write_items(
                TransactItems=transact_items
            )
            return {
                "status": "success",
                "response": response
            }
        except ClientError as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    def query_gsi(self, gsi_name: str, pk: str, sk_condition: str = None) -> Dict[str, Any]:
        """Query items using a Global Secondary Index"""
        try:
            if sk_condition:
                response = self.table.query(
                    IndexName=gsi_name,
                    KeyConditionExpression='user_id = :pk AND begins_with(booking_date, :sk)',
                    ExpressionAttributeValues={
                        ':pk': pk,
                        ':sk': sk_condition
                    }
                )
            else:
                response = self.table.query(
                    IndexName=gsi_name,
                    KeyConditionExpression='user_id = :pk',
                    ExpressionAttributeValues={
                        ':pk': pk
                    }
                )
            
            return {
                "status": "success",
                "items": response['Items'],
                "count": response['Count']
            }
        except ClientError as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    def update_item_conditional(self, pk: str, sk: str, update_expression: str, 
                              condition_expression: str, expression_values: Dict[str, Any]) -> Dict[str, Any]:
        """Update item with conditional expression"""
        try:
            response = self.table.update_item(
                Key={'pk': pk, 'sk': sk},
                UpdateExpression=update_expression,
                ConditionExpression=condition_expression,
                ExpressionAttributeValues=expression_values
            )
            return {
                "status": "success",
                "response": response
            }
        except ClientError as e:
            return {
                "status": "error",
                "error": str(e)
            }

# Global database client instance
db_client = DynamoDBClient()
