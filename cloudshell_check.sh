#!/bin/bash
# AWS CloudShell で実行する状態確認スクリプト
# ECR、ECS、CloudWatch Logs の状態を確認します

set -e

# 色付き出力用
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=========================================="
echo "AWS リソース状態確認スクリプト"
echo "=========================================="
echo ""

# リージョン確認
REGION=$(aws configure get region || echo "ap-northeast-1")
echo -e "${GREEN}現在のリージョン: ${REGION}${NC}"
echo ""

# ============================================
# 1. ECR リポジトリの状態確認
# ============================================
echo "=========================================="
echo "1. ECR リポジトリの状態"
echo "=========================================="

REPO_NAME="mysfa_ver2"

echo "リポジトリ情報:"
aws ecr describe-repositories --repository-names $REPO_NAME --region $REGION 2>/dev/null || {
    echo -e "${RED}❌ ECRリポジトリ '$REPO_NAME' が見つかりません${NC}"
    echo "利用可能なリポジトリ:"
    aws ecr describe-repositories --region $REGION --query 'repositories[*].repositoryName' --output table
    exit 1
}

echo ""
echo "最新のイメージ:"
aws ecr describe-images \
    --repository-name $REPO_NAME \
    --region $REGION \
    --query 'sort_by(imageDetails,& imagePushedAt)[-5:].[imageTags[0],imageDigest,imagePushedAt,imageSizeInBytes]' \
    --output table

echo ""
echo "latest タグのイメージ詳細:"
LATEST_IMAGE=$(aws ecr describe-images \
    --repository-name $REPO_NAME \
    --region $REGION \
    --image-ids imageTag=latest \
    --query 'imageDetails[0]' \
    --output json 2>/dev/null)

if [ "$LATEST_IMAGE" != "null" ] && [ -n "$LATEST_IMAGE" ]; then
    echo "$LATEST_IMAGE" | jq -r '{
        "タグ": .imageTags[0],
        "ダイジェスト": .imageDigest,
        "プッシュ日時": .imagePushedAt,
        "サイズ(MB)": (.imageSizeInBytes / 1024 / 1024 | floor),
        "脆弱性スキャン": .imageScanFindingsSummary.status
    }'
else
    echo -e "${YELLOW}⚠️  latest タグのイメージが見つかりません${NC}"
fi

echo ""
echo "ライフサイクルポリシー:"
aws ecr get-lifecycle-policy \
    --repository-name $REPO_NAME \
    --region $REGION \
    --query 'lifecyclePolicyText' \
    --output text 2>/dev/null || echo -e "${YELLOW}ライフサイクルポリシーが設定されていません${NC}"

echo ""
echo "イメージスキャン設定:"
aws ecr describe-image-scan-findings \
    --repository-name $REPO_NAME \
    --region $REGION \
    --image-id imageTag=latest \
    --query 'imageScanFindings.summary' \
    --output json 2>/dev/null || echo -e "${YELLOW}スキャン結果が見つかりません${NC}"

echo ""

# ============================================
# 2. ECS クラスター・サービスの状態確認
# ============================================
echo "=========================================="
echo "2. ECS クラスター・サービスの状態"
echo "=========================================="

CLUSTER_NAME="mysfa-cluster"
SERVICE_NAME="mysfa-service"

echo "クラスター情報:"
aws ecs describe-clusters \
    --clusters $CLUSTER_NAME \
    --region $REGION \
    --query 'clusters[0]' \
    --output json 2>/dev/null | jq -r '{
        "クラスター名": .clusterName,
        "ステータス": .status,
        "アクティブなタスク数": .activeTasksCount,
        "実行中のタスク数": .runningTasksCount,
        "登録済みタスク定義数": .registeredContainerInstancesCount
    }' || {
    echo -e "${RED}❌ ECSクラスター '$CLUSTER_NAME' が見つかりません${NC}"
}

echo ""
echo "サービス情報:"
SERVICE_INFO=$(aws ecs describe-services \
    --cluster $CLUSTER_NAME \
    --services $SERVICE_NAME \
    --region $REGION \
    --query 'services[0]' \
    --output json 2>/dev/null)

if [ "$SERVICE_INFO" != "null" ] && [ -n "$SERVICE_INFO" ]; then
    echo "$SERVICE_INFO" | jq -r '{
        "サービス名": .serviceName,
        "ステータス": .status,
        "希望タスク数": .desiredCount,
        "実行中タスク数": .runningCount,
        "保留中タスク数": .pendingCount,
        "タスク定義": .taskDefinition,
        "ロードバランサー": .loadBalancers[0].targetGroupArn
    }'
    
    echo ""
    echo "サービスのイベント（最新5件）:"
    echo "$SERVICE_INFO" | jq -r '.events[0:5] | .[] | "\(.createdAt) - \(.message)"'
else
    echo -e "${RED}❌ ECSサービス '$SERVICE_NAME' が見つかりません${NC}"
fi

echo ""
echo "実行中のタスク:"
TASK_ARNS=$(aws ecs list-tasks \
    --cluster $CLUSTER_NAME \
    --service-name $SERVICE_NAME \
    --region $REGION \
    --desired-status RUNNING \
    --query 'taskArns' \
    --output json 2>/dev/null)

if [ "$TASK_ARNS" != "[]" ] && [ -n "$TASK_ARNS" ]; then
    echo "$TASK_ARNS" | jq -r '.[]' | while read TASK_ARN; do
        echo ""
        echo "タスク詳細: $TASK_ARN"
        aws ecs describe-tasks \
            --cluster $CLUSTER_NAME \
            --tasks $TASK_ARN \
            --region $REGION \
            --query 'tasks[0]' \
            --output json | jq -r '{
                "最終ステータス": .lastStatus,
                "希望ステータス": .desiredStatus,
                "起動タイプ": .launchType,
                "CPU": .cpu,
                "メモリ": .memory,
                "作成日時": .createdAt,
                "開始日時": .startedAt,
                "コンテナ状態": .containers[0].lastStatus,
                "コンテナ理由": .containers[0].reason,
                "ヘルスステータス": .containers[0].healthStatus
            }'
    done
else
    echo -e "${YELLOW}⚠️  実行中のタスクがありません${NC}"
fi

echo ""

# ============================================
# 3. タスク定義の確認
# ============================================
echo "=========================================="
echo "3. タスク定義の状態"
echo "=========================================="

TASK_FAMILY="mysfa-task"

echo "最新のタスク定義:"
LATEST_TASK_DEF=$(aws ecs describe-task-definition \
    --task-definition $TASK_FAMILY \
    --region $REGION \
    --query 'taskDefinition' \
    --output json 2>/dev/null)

if [ "$LATEST_TASK_DEF" != "null" ] && [ -n "$LATEST_TASK_DEF" ]; then
    echo "$LATEST_TASK_DEF" | jq -r '{
        "ファミリー": .family,
        "リビジョン": .revision,
        "ステータス": .status,
        "CPU": .cpu,
        "メモリ": .memory,
        "イメージ": .containerDefinitions[0].image,
        "ヘルスチェック": .containerDefinitions[0].healthCheck,
        "ロググループ": .containerDefinitions[0].logConfiguration.options."awslogs-group"
    }'
else
    echo -e "${RED}❌ タスク定義 '$TASK_FAMILY' が見つかりません${NC}"
fi

echo ""

# ============================================
# 4. CloudWatch Logs の確認
# ============================================
echo "=========================================="
echo "4. CloudWatch Logs の状態"
echo "=========================================="

LOG_GROUP="/ecs/mysfa-task"

echo "ロググループ情報:"
aws logs describe-log-groups \
    --log-group-name-prefix "/ecs/" \
    --region $REGION \
    --query "logGroups[?logGroupName=='$LOG_GROUP']" \
    --output json | jq -r '.[] | {
        "ロググループ名": .logGroupName,
        "保持期間(日)": .retentionInDays,
        "作成日時": .creationTime,
        "保存サイズ(バイト)": .storedBytes
    }' || echo -e "${YELLOW}⚠️  ロググループ '$LOG_GROUP' が見つかりません${NC}"

echo ""
echo "最新のログストリーム（最新5件）:"
aws logs describe-log-streams \
    --log-group-name $LOG_GROUP \
    --region $REGION \
    --order-by LastEventTime \
    --descending \
    --max-items 5 \
    --query 'logStreams[*].[logStreamName,lastEventTime]' \
    --output table 2>/dev/null || echo -e "${YELLOW}ログストリームが見つかりません${NC}"

echo ""

# ============================================
# 5. ヘルスチェックの確認
# ============================================
echo "=========================================="
echo "5. ターゲットグループのヘルスチェック"
echo "=========================================="

# ターゲットグループを検索
TG_ARNS=$(aws elbv2 describe-target-groups \
    --region $REGION \
    --query 'TargetGroups[?contains(TargetGroupName, `mysfa`)].TargetGroupArn' \
    --output json 2>/dev/null)

if [ "$TG_ARNS" != "[]" ] && [ -n "$TG_ARNS" ]; then
    echo "$TG_ARNS" | jq -r '.[]' | while read TG_ARN; do
        echo ""
        echo "ターゲットグループ: $TG_ARN"
        aws elbv2 describe-target-health \
            --target-group-arn $TG_ARN \
            --region $REGION \
            --query 'TargetHealthDescriptions[*].[Target.Id,TargetHealth.State,TargetHealth.Reason]' \
            --output table
    done
else
    echo -e "${YELLOW}⚠️  ターゲットグループが見つかりません${NC}"
fi

echo ""
echo "=========================================="
echo "状態確認完了"
echo "=========================================="

