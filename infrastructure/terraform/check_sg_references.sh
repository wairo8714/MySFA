#!/bin/bash
# セキュリティグループの参照を確認するスクリプト
# 使用方法: ./check_sg_references.sh <セキュリティグループID>

set -e

if [ $# -eq 0 ]; then
  echo "使用方法: $0 <セキュリティグループID>"
  echo "例: $0 sg-07be7b31791321202"
  exit 1
fi

SG_ID=$1
REGION=${AWS_REGION:-ap-northeast-1}

echo "========================================="
echo "セキュリティグループ参照確認スクリプト"
echo "========================================="
echo "セキュリティグループID: $SG_ID"
echo "リージョン: $REGION"
echo ""

# セキュリティグループの基本情報を取得
echo "【セキュリティグループ情報】"
aws ec2 describe-security-groups \
  --group-ids $SG_ID \
  --region $REGION \
  --query 'SecurityGroups[0].[GroupName,Description,VpcId]' \
  --output table || {
  echo "❌ セキュリティグループが見つかりません"
  exit 1
}

echo ""
echo "【EC2インスタンスの参照確認】"
INSTANCES=$(aws ec2 describe-instances \
  --filters "Name=instance-state-name,Values=running,stopped,stopping" \
  --region $REGION \
  --query "Reservations[*].Instances[*].[InstanceId,SecurityGroups[?GroupId=='$SG_ID'].GroupId | [0]]" \
  --output text | grep -v "None" | awk '{print $1}' | sort -u)

if [ -z "$INSTANCES" ]; then
  echo "✅ EC2インスタンスからの参照なし"
else
  echo "⚠️  以下のEC2インスタンスがこのセキュリティグループを参照しています:"
  echo "$INSTANCES"
fi

echo ""
echo "【ALBの参照確認】"
ALBS=$(aws elbv2 describe-load-balancers \
  --region $REGION \
  --query "LoadBalancers[?SecurityGroups && contains(SecurityGroups, '$SG_ID')].LoadBalancerArn" \
  --output text)

if [ -z "$ALBS" ]; then
  echo "✅ ALBからの参照なし"
else
  echo "⚠️  以下のALBがこのセキュリティグループを参照しています:"
  echo "$ALBS"
fi

echo ""
echo "【RDSインスタンスの参照確認】"
RDS_INSTANCES=$(aws rds describe-db-instances \
  --region $REGION \
  --query "DBInstances[?VpcSecurityGroups && contains(VpcSecurityGroups[*].VpcSecurityGroupId, '$SG_ID')].DBInstanceIdentifier" \
  --output text)

if [ -z "$RDS_INSTANCES" ]; then
  echo "✅ RDSインスタンスからの参照なし"
else
  echo "⚠️  以下のRDSインスタンスがこのセキュリティグループを参照しています:"
  echo "$RDS_INSTANCES"
fi

echo ""
echo "【ネットワークインターフェース（ENI）の参照確認】"
ENIS=$(aws ec2 describe-network-interfaces \
  --filters "Name=group-id,Values=$SG_ID" \
  --region $REGION \
  --query "NetworkInterfaces[*].[NetworkInterfaceId,Description,Status]" \
  --output table)

if [ -z "$ENIS" ] || [ "$(echo "$ENIS" | wc -l)" -le 2 ]; then
  echo "✅ ネットワークインターフェースからの参照なし"
else
  echo "⚠️  以下のネットワークインターフェースがこのセキュリティグループを参照しています:"
  echo "$ENIS"
fi

echo ""
echo "【他のセキュリティグループからの参照確認】"
# このセキュリティグループをsourceとして参照しているセキュリティグループを確認
REFERENCED_BY=$(aws ec2 describe-security-groups \
  --region $REGION \
  --filters "Name=ip-permission.group-id,Values=$SG_ID" \
  --query "SecurityGroups[*].[GroupId,GroupName]" \
  --output text)

if [ -z "$REFERENCED_BY" ]; then
  echo "✅ 他のセキュリティグループからの参照なし"
else
  echo "⚠️  以下のセキュリティグループがこのセキュリティグループを参照しています:"
  echo "$REFERENCED_BY"
fi

echo ""
echo "========================================="
echo "確認完了"
echo "========================================="
echo ""
echo "削除可能な場合: すべての項目で「参照なし」と表示されている場合"
echo "削除不可な場合: いずれかの項目で参照が表示されている場合"
echo ""
echo "注意: セキュリティグループ自体は無料リソースですが、"
echo "      整理のために未使用のセキュリティグループは削除することを推奨します。"

