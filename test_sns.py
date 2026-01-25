#!/usr/bin/env python
import boto3

AWS_REGION = "ap-south-1"
SNS_TOPIC_ARN = "arn:aws:sns:ap-south-1:303983719037:snapstream-upload-topic"

sns = boto3.client("sns", region_name=AWS_REGION)

print("=" * 60)
print("🧪 SNS Configuration Test")
print("=" * 60)

# Test 1: Check topic exists
print("\n1️⃣  Checking SNS Topic...")
try:
    response = sns.get_topic_attributes(TopicArn=SNS_TOPIC_ARN)
    print(f"✅ Topic found: {SNS_TOPIC_ARN}")
    print(f"   Topic Arn: {response['Attributes'].get('TopicArn')}")
except Exception as e:
    print(f"❌ Topic not found: {e}")
    exit(1)

# Test 2: List subscriptions
print("\n2️⃣  Checking Topic Subscriptions...")
try:
    response = sns.list_subscriptions_by_topic(TopicArn=SNS_TOPIC_ARN)
    subscriptions = response.get('Subscriptions', [])
    
    if subscriptions:
        print(f"✅ Found {len(subscriptions)} subscription(s):")
        for sub in subscriptions:
            print(f"   - Protocol: {sub['Protocol']}")
            print(f"     Endpoint: {sub['Endpoint']}")
            print(f"     Status: {sub['SubscriptionArn']}")
    else:
        print("❌ NO SUBSCRIPTIONS FOUND!")
        print("   You need to add email subscription to the topic.")
        
except Exception as e:
    print(f"❌ Error listing subscriptions: {e}")

# Test 3: Test publish
print("\n3️⃣  Testing SNS Publish...")
try:
    response = sns.publish(
        TopicArn=SNS_TOPIC_ARN,
        Subject="SnapStream Test - Email Notification",
        Message="This is a test message from SnapStream. If you received this email, SNS is working correctly!"
    )
    print(f"✅ Message published successfully")
    print(f"   Message ID: {response['MessageId']}")
except Exception as e:
    print(f"❌ Publish failed: {e}")

print("\n" + "=" * 60)
print("Test completed!")
print("=" * 60)
