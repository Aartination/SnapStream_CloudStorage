#!/usr/bin/env python
import boto3
from botocore.exceptions import ClientError

AWS_BUCKET_NAME = "snapstream-media-nitin"
AWS_REGION = "ap-south-1"

# Initialize S3 client
s3_client = boto3.client('s3', region_name=AWS_REGION)

print("=" * 60)
print("🧪 S3 Connectivity Test")
print("=" * 60)

# Test 1: List buckets
print("\n1️⃣  Testing bucket access...")
try:
    response = s3_client.list_buckets()
    buckets = [b['Name'] for b in response['Buckets']]
    print(f"✅ Found {len(buckets)} buckets")
    print(f"   Buckets: {buckets}")
    
    if AWS_BUCKET_NAME in buckets:
        print(f"✅ Target bucket '{AWS_BUCKET_NAME}' exists!")
    else:
        print(f"❌ Target bucket '{AWS_BUCKET_NAME}' NOT found!")
        
except ClientError as e:
    print(f"❌ Error listing buckets: {e}")
except Exception as e:
    print(f"❌ Unexpected error: {e}")

# Test 2: Check bucket region
print("\n2️⃣  Testing bucket location...")
try:
    response = s3_client.get_bucket_location(Bucket=AWS_BUCKET_NAME)
    region = response.get('LocationConstraint', 'us-east-1')
    print(f"✅ Bucket '{AWS_BUCKET_NAME}' is in region: {region}")
    if region == AWS_REGION or (region is None and AWS_REGION == 'us-east-1'):
        print(f"✅ Region matches!")
    else:
        print(f"⚠️  Region mismatch! Expected: {AWS_REGION}, Got: {region}")
except ClientError as e:
    print(f"❌ Error checking bucket location: {e}")

# Test 3: Test file upload with ACL
print("\n3️⃣  Testing file upload (without ACL - bucket ACLs disabled)...")
try:
    test_content = b"Test file for SnapStream"
    test_filename = "test_upload.txt"
    
    s3_client.put_object(
        Bucket=AWS_BUCKET_NAME,
        Key=test_filename,
        Body=test_content
    )
    print(f"✅ Successfully uploaded test file: {test_filename}")
    
    # Generate URL
    file_url = f"https://{AWS_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{test_filename}"
    print(f"   Public URL: {file_url}")
    
    # Clean up test file
    s3_client.delete_object(Bucket=AWS_BUCKET_NAME, Key=test_filename)
    print(f"✅ Test file cleaned up")
    
except ClientError as e:
    error_code = e.response['Error']['Code']
    print(f"❌ Error uploading file: {error_code} - {e}")
except Exception as e:
    print(f"❌ Unexpected error: {e}")

# Test 4: Check bucket policy
print("\n4️⃣  Checking bucket CORS and policies...")
try:
    try:
        cors = s3_client.get_bucket_cors(Bucket=AWS_BUCKET_NAME)
        print(f"✅ CORS is configured: {cors}")
    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchCORSConfiguration':
            print("⚠️  No CORS configuration found (may not be needed)")
        else:
            raise
except Exception as e:
    print(f"⚠️  Could not check CORS: {e}")

print("\n" + "=" * 60)
print("✅ S3 connectivity test completed!")
print("=" * 60)
