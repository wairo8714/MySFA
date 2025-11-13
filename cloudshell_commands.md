# AWS CloudShell 状態確認コマンド集

## 基本的な確認コマンド

### 1. ECR リポジトリの状態確認

```bash
# リポジトリ情報
aws ecr describe-repositories --repository-names mysfa_ver2 --region ap-northeast-1

# 最新のイメージ一覧（最新5件）
aws ecr describe-images \
    --repository-name mysfa_ver2 \
    --region ap-northeast-1 \
    --query 'sort_by(imageDetails,& imagePushedAt)[-5:].[imageTags[0],imageDigest,imagePushedAt,imageSizeInBytes]' \
    --output table

# latest タグのイメージ詳細
aws ecr describe-images \
    --repository-name mysfa_ver2 \
    --region ap-northeast-1 \
    --image-ids imageTag=latest \
    --query 'imageDetails[0]' \
    --output json | jq '.'

# イメージダイジェストの確認
aws ecr describe-images \
    --repository-name mysfa_ver2 \
    --region ap-northeast-1 \
    --image-ids imageTag=latest \
    --query 'imageDetails[0].imageDigest' \
    --output text

# ライフサイクルポリシーの確認
aws ecr get-lifecycle-policy \
    --repository-name mysfa_ver2 \
    --region ap-northeast-1

# イメージスキャン結果
aws ecr describe-image-scan-findings \
    --repository-name mysfa_ver2 \
    --region ap-northeast-1 \
    --image-id imageTag=latest
```

### 2. ECS クラスター・サービスの状態確認

```bash
# クラスター情報
aws ecs describe-clusters \
    --clusters mysfa-cluster \
    --region ap-northeast-1 \
    --query 'clusters[0]' \
    --output json | jq '.'

# サービス情報
aws ecs describe-services \
    --cluster mysfa-cluster \
    --services mysfa-service \
    --region ap-northeast-1 \
    --query 'services[0]' \
    --output json | jq '{
        serviceName: .serviceName,
        status: .status,
        desiredCount: .desiredCount,
        runningCount: .runningCount,
        pendingCount: .pendingCount,
        taskDefinition: .taskDefinition
    }'

# サービスのイベント（最新10件）
aws ecs describe-services \
    --cluster mysfa-cluster \
    --services mysfa-service \
    --region ap-northeast-1 \
    --query 'services[0].events[0:10]' \
    --output table

# 実行中のタスク一覧
aws ecs list-tasks \
    --cluster mysfa-cluster \
    --service-name mysfa-service \
    --region ap-northeast-1 \
    --desired-status RUNNING

# タスクの詳細情報
TASK_ARN=$(aws ecs list-tasks \
    --cluster mysfa-cluster \
    --service-name mysfa-service \
    --region ap-northeast-1 \
    --desired-status RUNNING \
    --query 'taskArns[0]' \
    --output text)

aws ecs describe-tasks \
    --cluster mysfa-cluster \
    --tasks $TASK_ARN \
    --region ap-northeast-1 \
    --query 'tasks[0]' \
    --output json | jq '{
        lastStatus: .lastStatus,
        desiredStatus: .desiredStatus,
        createdAt: .createdAt,
        startedAt: .startedAt,
        containers: .containers[0] | {
            name: .name,
            lastStatus: .lastStatus,
            reason: .reason,
            healthStatus: .healthStatus
        }
    }'
```

### 3. タスク定義の確認

```bash
# 最新のタスク定義
aws ecs describe-task-definition \
    --task-definition mysfa-task \
    --region ap-northeast-1 \
    --query 'taskDefinition' \
    --output json | jq '{
        family: .family,
        revision: .revision,
        status: .status,
        cpu: .cpu,
        memory: .memory,
        image: .containerDefinitions[0].image,
        healthCheck: .containerDefinitions[0].healthCheck,
        logGroup: .containerDefinitions[0].logConfiguration.options."awslogs-group"
    }'

# タスク定義の履歴
aws ecs list-task-definitions \
    --family-prefix mysfa-task \
    --region ap-northeast-1 \
    --sort DESC \
    --max-items 10
```

### 4. CloudWatch Logs の確認

```bash
# ロググループの確認
aws logs describe-log-groups \
    --log-group-name-prefix "/ecs/" \
    --region ap-northeast-1

# ログストリーム一覧（最新5件）
aws logs describe-log-streams \
    --log-group-name /ecs/mysfa-task \
    --region ap-northeast-1 \
    --order-by LastEventTime \
    --descending \
    --max-items 5

# 最新のログを取得
LOG_STREAM=$(aws logs describe-log-streams \
    --log-group-name /ecs/mysfa-task \
    --region ap-northeast-1 \
    --order-by LastEventTime \
    --descending \
    --max-items 1 \
    --query 'logStreams[0].logStreamName' \
    --output text)

aws logs get-log-events \
    --log-group-name /ecs/mysfa-task \
    --log-stream-name $LOG_STREAM \
    --region ap-northeast-1 \
    --limit 50 \
    --query 'events[*].message' \
    --output text
```

### 5. ターゲットグループのヘルスチェック

```bash
# ターゲットグループ一覧
aws elbv2 describe-target-groups \
    --region ap-northeast-1 \
    --query 'TargetGroups[?contains(TargetGroupName, `mysfa`)]' \
    --output table

# ターゲットグループのヘルス状態
TG_ARN=$(aws elbv2 describe-target-groups \
    --region ap-northeast-1 \
    --query 'TargetGroups[?contains(TargetGroupName, `mysfa`)].TargetGroupArn' \
    --output text | head -1)

aws elbv2 describe-target-health \
    --target-group-arn $TG_ARN \
    --region ap-northeast-1
```

### 6. サービスの安定化状態を確認

```bash
# サービスの安定化を待機（最大5分）
aws ecs wait services-stable \
    --cluster mysfa-cluster \
    --services mysfa-service \
    --region ap-northeast-1 \
    --max-attempts 30 \
    --delay 10

# または、手動で状態を確認
while true; do
    STATUS=$(aws ecs describe-services \
        --cluster mysfa-cluster \
        --services mysfa-service \
        --region ap-northeast-1 \
        --query 'services[0].{running:runningCount,desired:desiredCount,status:status}' \
        --output json)
    
    echo "$(date): $STATUS"
    
    RUNNING=$(echo $STATUS | jq -r '.running')
    DESIRED=$(echo $STATUS | jq -r '.desired')
    
    if [ "$RUNNING" = "$DESIRED" ] && [ "$RUNNING" -gt 0 ]; then
        echo "✅ サービスが安定しました"
        break
    fi
    
    sleep 10
done
```

## トラブルシューティング用コマンド

### タスクが起動しない場合

```bash
# タスクの停止理由を確認
aws ecs describe-tasks \
    --cluster mysfa-cluster \
    --tasks $(aws ecs list-tasks \
        --cluster mysfa-cluster \
        --service-name mysfa-service \
        --region ap-northeast-1 \
        --desired-status STOPPED \
        --query 'taskArns[0]' \
        --output text) \
    --region ap-northeast-1 \
    --query 'tasks[0].stoppedReason' \
    --output text
```

### イメージがプッシュされていない場合

```bash
# ECRへのログイン確認
aws ecr get-login-password --region ap-northeast-1 | \
    docker login --username AWS --password-stdin \
    $(aws sts get-caller-identity --query Account --output text).dkr.ecr.ap-northeast-1.amazonaws.com

# イメージの存在確認
aws ecr batch-get-image \
    --repository-name mysfa_ver2 \
    --region ap-northeast-1 \
    --image-ids imageTag=latest
```

### ログをリアルタイムで確認

```bash
# CloudWatch Logs Insights でクエリ
aws logs tail /ecs/mysfa-task --follow --region ap-northeast-1
```

## 一括確認スクリプトの実行

```bash
# スクリプトをCloudShellにアップロードして実行
bash cloudshell_check.sh
```

