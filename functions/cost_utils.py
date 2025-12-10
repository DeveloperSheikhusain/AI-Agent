"""
Cost retrieval utilities for AWS and GCP services.

This module provides functions to fetch cost data from:
- AWS Cost Explorer API (Bedrock, Marketplace)
- GCP BigQuery Billing Export (Firestore, Cloud Functions, Translation API)
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional
import boto3
from google.cloud import bigquery
from bedrock_utils import get_config

logger = logging.getLogger('cost_utils')
logger.setLevel(logging.INFO)


def get_aws_cost(service_name: str, start_date: str, end_date: str) -> float:
    """
    Retrieves AWS service cost using Cost Explorer API.
    
    Args:
        service_name: AWS service name (e.g., "Amazon Bedrock", "AWS Marketplace")
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        
    Returns:
        float: Cost amount in USD
    """
    try:
        # Initialize Cost Explorer client
        ce = boto3.client(
            'ce',
            aws_access_key_id=get_config('AWS_ACCESS_KEY'),
            aws_secret_access_key=get_config('AWS_SECRET_KEY'),
            region_name=get_config('AWS_REGION') or 'us-east-1'
        )
        
        response = ce.get_cost_and_usage(
            TimePeriod={'Start': start_date, 'End': end_date},
            Granularity='MONTHLY',
            Metrics=['UnblendedCost'],
            Filter={
                "Dimensions": {
                    "Key": "SERVICE",
                    "Values": [service_name]
                }
            }
        )
        
        # Extract cost from response
        if response.get('ResultsByTime'):
            cost_str = response['ResultsByTime'][0]['Total']['UnblendedCost']['Amount']
            return float(cost_str)
        
        return 0.0
        
    except Exception as e:
        logger.error(f"Error fetching AWS cost for {service_name}: {e}")
        return 0.0


def get_gcp_cost(service_description: str, start_date: str, end_date: str) -> float:
    """
    Retrieves GCP service cost from BigQuery billing export.
    
    Args:
        service_description: GCP service description (e.g., "Cloud Firestore")
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        
    Returns:
        float: Cost amount in USD
    """
    try:
        # Initialize BigQuery client
        project_id = get_config('GOOGLE_CLOUD_PROJECT_ID')
        if not project_id:
            logger.error("GOOGLE_CLOUD_PROJECT_ID not configured")
            return 0.0
            
        client = bigquery.Client(project=project_id)
        
        # Get dataset and table configuration
        dataset = get_config('GCP_BILLING_DATASET') or 'ss_gcp_billing'
        table_prefix = get_config('GCP_BILLING_TABLE_PREFIX') or 'gcp_billing_export_v1'
        table = f"{dataset}.{table_prefix}_*"
        
        # Build query
        query = f"""
        SELECT SUM(cost) AS total_cost
        FROM `{project_id}.{table}`
        WHERE service.description = @service_description
          AND usage_start_time >= @start_date
          AND usage_start_time < @end_date
        """
        
        # Configure query parameters
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("service_description", "STRING", service_description),
                bigquery.ScalarQueryParameter("start_date", "DATE", start_date),
                bigquery.ScalarQueryParameter("end_date", "DATE", end_date),
            ]
        )
        
        # Execute query
        query_job = client.query(query, job_config=job_config)
        results = query_job.result()
        
        # Extract cost from results
        for row in results:
            return float(row.total_cost) if row.total_cost else 0.0
        
        return 0.0
        
    except Exception as e:
        logger.error(f"Error fetching GCP cost for {service_description}: {e}")
        return 0.0


def get_all_costs(start_date: Optional[str] = None, end_date: Optional[str] = None) -> Dict:
    """
    Retrieves costs for all configured AWS and GCP services.
    
    Args:
        start_date: Optional start date in YYYY-MM-DD format (defaults to first day of current month)
        end_date: Optional end date in YYYY-MM-DD format (defaults to today)
        
    Returns:
        dict: Cost breakdown with individual services and total
    """
    # Set default date range to current month if not provided
    if not start_date:
        start_date = datetime.today().replace(day=1).strftime("%Y-%m-%d")
    if not end_date:
        end_date = datetime.today().strftime("%Y-%m-%d")
    
    logger.info(f"Fetching costs from {start_date} to {end_date}")
    
    # Fetch AWS costs
    aws_bedrock_cost = get_aws_cost("Amazon Bedrock", start_date, end_date)
    aws_marketplace_cost = get_aws_cost("AWS Marketplace", start_date, end_date)
    
    # Fetch GCP costs
    gcp_firestore_cost = get_gcp_cost("Cloud Firestore", start_date, end_date)
    gcp_functions_cost = get_gcp_cost("Cloud Functions", start_date, end_date)
    gcp_translation_cost = get_gcp_cost("Cloud Translation API", start_date, end_date)
    
    # Calculate total
    total_cost = (
        aws_bedrock_cost + 
        aws_marketplace_cost + 
        gcp_firestore_cost + 
        gcp_functions_cost + 
        gcp_translation_cost
    )
    
    # Build response
    return {
        "period": {
            "start": start_date,
            "end": end_date
        },
        "services": {
            "aws_bedrock": {
                "cost": round(aws_bedrock_cost, 2),
                "currency": "USD"
            },
            "aws_marketplace": {
                "cost": round(aws_marketplace_cost, 2),
                "currency": "USD"
            },
            "gcp_firestore": {
                "cost": round(gcp_firestore_cost, 2),
                "currency": "USD"
            },
            "gcp_cloud_functions": {
                "cost": round(gcp_functions_cost, 2),
                "currency": "USD"
            },
            "gcp_translation_api": {
                "cost": round(gcp_translation_cost, 2),
                "currency": "USD"
            }
        },
        "total_cost": round(total_cost, 2),
        "currency": "USD"
    }
