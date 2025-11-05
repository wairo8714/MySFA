#!/bin/bash
# EC2インスタンスのセキュリティグループを更新するスクリプト
# 使用方法: ./update_instance_sg.sh <インスタンスID> <新しいセキュリティグループID>

set -e

if [ $# -lt 2 ]; then
  echo "使用方法: $0 <インスタンスID> <新しいセキュリティグループID>"
  echo "例: $0 i-0f94fa7ded31dcc7c sg-080e45ce7d08ff517"
  exit 1
fi

INSTANCE_ID=$1
NEW_SG_ID=$2
REGION=${AWS_REGION:-ap-northeast-1}

echo "========================================="
echo "EC2インスタンスのセキュリティグループ更新"
echo "========================================="
echo "インスタンスID: $INSTANCE_ID"
echo "新しいセキュリティグループID: $NEW_SG_ID"
echo "リージョン: $REGION"
echo ""

# インスタンスの現在のセキュリティグループを確認
echo "【現在のセキュリティグループ】"
CURRENT_SGS=$(aws ec2 describe-instances \
  --instance-ids $INSTANCE_ID \
  --region $REGION \
  --query 'Reservations[0].Instances[0].SecurityGroups[*].GroupId' \
  --output text)

echo "$CURRENT_SGS"
echo ""

# インスタンスの状態を確認
INSTANCE_STATE=$(aws ec2 describe-instances \
  --instance-ids $INSTANCE_ID \
  --region $REGION \
  --query 'Reservations[0].Instances[0].State.Name' \
  --output text)

echo "インスタンスの状態: $INSTANCE_STATE"
echo ""

if [ "$INSTANCE_STATE" != "running" ] && [ "$INSTANCE_STATE" != "stopped" ]; then
  echo "⚠️  インスタンスが $INSTANCE_STATE 状態です。running または stopped 状態でないと更新できません。"
  exit 1
fi

# 新しいセキュリティグループが既に含まれているか確認
if echo "$CURRENT_SGS" | grep -q "$NEW_SG_ID"; then
  echo "✅ インスタンスは既に新しいセキュリティグループを使用しています"
  exit 0
fi

# セキュリティグループを更新
echo "【セキュリティグループを更新中...】"
aws ec2 modify-instance-attribute \
  --instance-id $INSTANCE_ID \
  --groups $NEW_SG_ID \
  --region $REGION

echo "✅ セキュリティグループの更新が完了しました"
echo ""

# 更新後のセキュリティグループを確認
echo "【更新後のセキュリティグループ】"
aws ec2 describe-instances \
  --instance-ids $INSTANCE_ID \
  --region $REGION \
  --query 'Reservations[0].Instances[0].SecurityGroups[*].[GroupId,GroupName]' \
  --output table

echo ""
echo "========================================="
echo "更新完了"
echo "========================================="
echo ""
echo "注意: 古いセキュリティグループが他のリソースから参照されていないことを確認してから削除してください。"

