set -euo pipefail

REGION="ap-northeast-1"
CLUSTER="mysfa-prod-cluster"
TASK_DEF="arn:aws:ecs:ap-northeast-1:334387323681:task-definition/mysfa-task:209"
LOG_GROUP="/ecs/mysfa-prod"

cat > overrides.json <<'JSON'
{
  "containerOverrides": [
    {
      "name": "web",
      "command": [
        "poetry","run","python","manage.py","shell","-c",
        "from accounts.models import CustomUser; from mysfa.models import Group, GroupMembership; g=Group.objects.get(custom_id='72014332'); print('group:', g.custom_id, 'creator=', g.creator_id); print('yamada candidates:', list(CustomUser.objects.filter(username='山田太郎').values_list('custom_user_id','username','is_active','is_trial'))); print('owners:', list(GroupMembership.objects.filter(group=g, role=GroupMembership.Role.OWNER).values_list('user_id','role','is_active')))"
      ]
    }
  ]
}
JSON

STARTED_BY="owner-check-$(date +%s)"

TASK_ARN="$(aws --no-cli-pager --region "$REGION" ecs run-task \
  --cluster "$CLUSTER" \
  --launch-type FARGATE \
  --started-by "$STARTED_BY" \
  --task-definition "$TASK_DEF" \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-0a297ae308bc3cd2d,subnet-028c0cca48501c864],securityGroups=[sg-0ffeb7a6d45c505ba],assignPublicIp=ENABLED}" \
  --overrides file://overrides.json \
  --query 'tasks[0].taskArn' --output text)"

echo "TASK_ARN=$TASK_ARN"

LOG_STREAM=""
for i in $(seq 1 30); do
  LOG_STREAM="$(aws --no-cli-pager --region "$REGION" ecs describe-tasks \
    --cluster "$CLUSTER" --tasks "$TASK_ARN" \
    --query "tasks[0].containers[?name=='web']|[0].logStreamName" --output text 2>/dev/null || true)"
  if [ -n "$LOG_STREAM" ] && [ "$LOG_STREAM" != "None" ] && [ "$LOG_STREAM" != "null" ]; then
    break
  fi
  sleep 2
done

echo "LOG_STREAM=$LOG_STREAM"

aws --no-cli-pager --region "$REGION" ecs wait tasks-stopped --cluster "$CLUSTER" --tasks "$TASK_ARN"

aws --no-cli-pager --region "$REGION" logs get-log-events \
  --log-group-name "$LOG_GROUP" \
  --log-stream-name "$LOG_STREAM" \
  --limit 200 \
  --query 'events[].message' \
  --output text
